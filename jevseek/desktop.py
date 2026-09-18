"""Local-only desktop adapter. No SDK/model imports until an explicit run.

pywebview is the only transport. This is not an HTTP API. Public methods return
safe envelopes; artifacts must be referenced by the selected session's log.
"""
from __future__ import annotations

from collections import deque
from functools import wraps
import json
import os
from pathlib import Path
import re
import threading
import time
import webbrowser
from urllib.parse import urlsplit

from filelock import FileLock
from .session import Session, SessionError, Redactor
from .credentials import CredentialError, environment_keys


class DesktopError(ValueError):
    """An intentionally user-visible validation error."""


def endpoint(fn):
    @wraps(fn)
    def guarded(self, *args, **kwargs):
        try:
            return {'ok': True, 'data': fn(self, *args, **kwargs)}
        except (DesktopError, CredentialError) as exc:
            return {'ok': False, 'error': str(exc)}
        except Exception as exc:
            return {'ok': False, 'error': f'{type(exc).__name__}: unable to complete this local operation. Check the session files or try again.'}
    return guarded


class DesktopAPI:
    def __init__(self, project, sessions_dir=None, workspace=None, runner=None, *, state_dir=None, credentials=None, require_runtime_terms=False):
        self._project = Path(project).resolve()
        self._state_dir = Path(state_dir or self._project / '.jevseek').resolve()
        self._home = Path(sessions_dir or self._state_dir / 'sessions').resolve()
        self._prefs_path = self._state_dir / 'desktop.json'
        self._credentials = credentials
        self._require_runtime_terms = require_runtime_terms
        self._close_window = None
        self._default_workspace = Path(workspace or project).resolve()
        self._guard = threading.RLock()
        self._events = deque(maxlen=2048)
        self._cursor = 0
        self._active = None
        self._cancel = threading.Event()
        self._thread = None
        self._runner = runner  # Dependency injection for offline adapter tests only.
        self._choose_folder = None
        self._redactor = Redactor.environment()

    def _runtime_terms(self):
        version = 'microsoft-webview2-fixed-v1'
        accepted = not self._require_runtime_terms
        if not accepted:
            try:
                value = json.loads((self._state_dir / 'runtime-terms.json').read_text())
                accepted = value == {'version': version, 'accepted': True}
            except (OSError, ValueError): pass
        return {'required': self._require_runtime_terms, 'accepted': accepted, 'version': version}

    @endpoint
    def accept_runtime_terms(self, accepted):
        if accepted is not True: raise DesktopError('Agreement must be an explicit choice.')
        with self._guard:
            terms = self._runtime_terms()
            self._state_dir.mkdir(parents=True, exist_ok=True)
            path = self._state_dir / 'runtime-terms.json'
            with FileLock(str(path) + '.lock', timeout=2):
                temporary = path.with_suffix('.tmp')
                temporary.write_text(json.dumps({'version': terms['version'], 'accepted': True}), encoding='utf-8')
                os.replace(temporary, path)
            return self._runtime_terms()

    @endpoint
    def close_app(self):
        if self._close_window is None: raise DesktopError('Close the desktop window to exit.')
        if self._request_close(): self._close_window()
        return True

    def _provider_keys(self):
        keys = environment_keys()
        if self._credentials is not None and self._credentials.supported:
            keys.update(self._credentials.load())
        # Keep retired keys redacted for the rest of this process too.
        self._redactor = Redactor([*self._redactor.secrets, *keys.values()])
        return keys

    def _key_status(self):
        error = None
        vault = {}
        supported = bool(self._credentials and self._credentials.supported)
        try:
            if supported: vault = self._credentials.load()
        except CredentialError as exc: error = str(exc)
        keys = {**environment_keys(), **vault}
        self._redactor = Redactor([*self._redactor.secrets, *keys.values()])
        return {'providers': {name: bool(value) for name, value in keys.items()},
                'key_setup': {'supported': supported, 'storage': 'Windows Credential Manager' if supported else 'Unavailable',
                              'sources': {name: 'vault' if name in vault else 'environment' if value else 'missing' for name, value in keys.items()},
                              'error': error}}

    @endpoint
    def get_key_status(self):
        with self._guard: return self._key_status()

    @endpoint
    def save_keys(self, deepseek, jev):
        with self._guard:
            if self._active: raise DesktopError('Stop the active run before changing API keys.')
            if self._credentials is None: raise DesktopError('Key setup is unavailable in this preview or test profile.')
            # Blank means keep, not delete. Delete is a separate explicit action.
            if not isinstance(deepseek, str) or not isinstance(jev, str): raise DesktopError('Paste API keys as text.')
            changes = {name: value for name, value in (('deepseek', deepseek), ('jev', jev)) if value.strip()}
            if not changes: raise DesktopError('Paste at least one new key. Blank fields keep existing keys.')
            self._provider_keys()  # Retain previous secrets for redaction after rotation.
            self._credentials.update(changes)
            return self._key_status()

    @endpoint
    def remove_key(self, provider):
        with self._guard:
            if self._active: raise DesktopError('Stop the active run before removing API keys.')
            if provider not in ('deepseek', 'jev'): raise DesktopError('Unknown provider.')
            if self._credentials is None: raise DesktopError('Key setup is unavailable in this preview or test profile.')
            self._provider_keys()
            self._credentials.update({provider: None})
            return self._key_status()

    def _preferences(self):
        prefs = {'theme': 'system', 'workspace': str(self._default_workspace), 'use_mcp': True}
        try:
            data = json.loads(self._prefs_path.read_text(encoding='utf-8'))
            if data.get('theme') in ('light', 'dark', 'system'): prefs['theme'] = data['theme']
            if isinstance(data.get('workspace'), str): prefs['workspace'] = data['workspace']
            if isinstance(data.get('use_mcp'), bool): prefs['use_mcp'] = data['use_mcp']
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        return prefs

    def _publish(self, event):
        with self._guard:
            self._cursor += 1
            self._events.append({'cursor': self._cursor, 'event': self._redactor.clean(event)})

    def _transient(self, session_id, kind, data):
        self._publish({'version': 1, 'session_id': session_id, 'seq': None,
                       'time': time.time(), 'kind': kind, 'data': data})

    def _session(self, session_id):
        if not isinstance(session_id, str) or not re.fullmatch(r'[a-f0-9]{32}', session_id):
            raise DesktopError('Invalid session identifier.')
        directory = (self._home / session_id).resolve()
        if directory.parent != self._home or not (directory / 'events.jsonl').is_file():
            raise DesktopError('This saved conversation is unavailable.')
        return Session.open(self._home, session_id, redactor=self._redactor, on_event=self._publish)

    def _snapshot(self, session_id):
        """Read-only snapshot: never repair logs or acquire the writer's lock.

        A currently-appending/torn final line is ignored and reported, not edited.
        Only Session.reload under the backend writer lock can recover it.
        """
        session = self._session(session_id)
        raw = session.path.read_bytes()
        trailing = bool(raw and not raw.endswith(b'\n'))
        lines = raw.splitlines(keepends=True)
        for line in lines:
            if not line.endswith(b'\n'): break
            try:
                event = json.loads(line)
                if (event['version'] != 1 or event['seq'] != len(session.events) + 1
                        or event['session_id'] != session_id or not isinstance(event['data'], dict)
                        or not isinstance(event['kind'], str) or not isinstance(event['time'], (int, float))):
                    raise ValueError()
            except (ValueError, TypeError, KeyError) as exc:
                raise DesktopError('This session log is incompatible or damaged. Its tools have not been replayed.') from exc
            session.events.append(event)
        if (not session.events or session.events[0]['kind'] != 'session'
                or not isinstance(session.events[0]['data'].get('workspace'), str)):
            raise DesktopError('This conversation has no readable session header.')
        return session, trailing

    def _meta(self, session, trailing=False):
        events = session.events
        user = next((e for e in events if e['kind'] == 'user'), None)
        title = user['data']['text'] if user else 'New conversation'
        last = next((e for e in reversed(events) if e['kind'] in ('final', 'error', 'user', 'run_started')), None)
        status = 'ready'
        if last:
            status = (last['data'].get('status', 'completed') if last['kind'] == 'final' else
                      'cancelled' if last['kind'] == 'error' and last['data'].get('stage') == 'cancelled' else 'blocked')
        pending = session.pending()
        if pending: status = 'needs_input'
        with self._guard:
            if self._active and self._active['session_id'] == session.id:
                status = 'stopping' if self._active['stopping'] else 'running'
        return self._redactor.clean({'session_id': session.id, 'title': ' '.join(title.split())[:100],
                                    'workspace': str(session.workspace), 'status': status,
                                    'updated': events[-1]['time'], 'pending': bool(pending),
                                    'trailing': trailing})

    def _list(self):
        rows, unreadable = [], 0
        for path in self._home.glob('*/events.jsonl'):
            try:
                session, trailing = self._snapshot(path.parent.name)
                rows.append(self._meta(session, trailing))
            except (OSError, ValueError, SessionError, KeyError, TypeError):
                unreadable += 1
        return {'sessions': sorted(rows, key=lambda x: x['updated'], reverse=True), 'unreadable': unreadable}

    @endpoint
    def bootstrap(self):
        status = self._key_status()
        return {**self._list(), 'preferences': self._preferences(), 'active': self._active,
                'cursor': self._cursor, 'desktop': True, 'runtime_terms': self._runtime_terms(), **status}

    @endpoint
    def list_sessions(self):
        return self._list()

    @endpoint
    def get_session(self, session_id):
        session, trailing = self._snapshot(session_id)
        return {'meta': self._meta(session, trailing), 'events': self._redactor.clean(session.events),
                'pending': self._redactor.clean(session.pending())}

    @endpoint
    def poll(self, cursor):
        if not isinstance(cursor, int) or cursor < 0: raise DesktopError('Invalid event cursor.')
        with self._guard:
            return {'cursor': self._cursor, 'active': dict(self._active) if self._active else None,
                    'reset': bool(self._events and cursor < self._events[0]['cursor'] - 1),
                    'events': [self._redactor.clean(item['event']) for item in self._events if item['cursor'] > cursor]}

    @endpoint
    def save_preferences(self, preferences):
        if not isinstance(preferences, dict) or set(preferences) != {'theme', 'workspace', 'use_mcp'}:
            raise DesktopError('Invalid settings. Nothing was saved.')
        if preferences['theme'] not in ('light', 'dark', 'system') or not isinstance(preferences['use_mcp'], bool):
            raise DesktopError('Choose a valid appearance and MCP setting.')
        workspace = Path(preferences['workspace']).expanduser().resolve()
        if not workspace.is_dir(): raise DesktopError('Choose an existing workspace folder.')
        prefs = {**preferences, 'workspace': str(workspace)}
        self._prefs_path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self._prefs_path) + '.lock', timeout=2):
            temp = self._prefs_path.with_suffix('.tmp')
            temp.write_text(json.dumps(prefs, indent=2), encoding='utf-8')
            os.replace(temp, self._prefs_path)
        return prefs

    @endpoint
    def choose_workspace(self):
        if self._choose_folder is None: raise DesktopError('Folder selection is available in the desktop app.')
        paths = self._choose_folder()
        return str(Path(paths[0]).resolve()) if paths else None

    @endpoint
    def start_run(self, session_id, prompt, acknowledge=False):
        if prompt is not None and (not isinstance(prompt, str) or len(prompt) > 1_000_000):
            raise DesktopError('The message is too large. Keep it under one million characters.')
        if not isinstance(acknowledge, bool): raise DesktopError('Invalid acknowledgement.')
        if prompt is not None and not prompt.strip(): raise DesktopError('Write a message first.')
        with self._guard:
            if self._active: raise DesktopError('A run is already in progress. Stop it or wait before starting another.')
            prefs = self._preferences()
            if not self._runtime_terms()['accepted']:
                raise DesktopError('Review and agree to the included Microsoft runtime terms before starting a run.')
            keys = self._provider_keys()
            if self._runner is None and not all(keys.values()):
                raise DesktopError('Add both API keys in Settings before starting a run. Saved conversations can still be viewed offline.')
            if session_id:
                session, _ = self._snapshot(session_id)
                if session.pending() and not acknowledge:
                    raise DesktopError('Inspect the interrupted tool and acknowledge uncertain effects before continuing.')
                if acknowledge and not prompt:
                    raise DesktopError('Include a follow-up message after inspecting the interrupted tool.')
                if not prompt and session.saved_result():
                    raise DesktopError('This conversation is paused or finished. Send a follow-up message to continue.')
            else:
                if not prompt: raise DesktopError('Write a message to start a conversation.')
                workspace = Path(prefs['workspace'])
                if not workspace.is_dir(): raise DesktopError('Your workspace is unavailable. Choose an existing folder in Settings.')
                session = Session.create(self._home, workspace, redactor=self._redactor, on_event=self._publish)
            self._cancel = threading.Event()
            self._active = {'session_id': session.id, 'stopping': False, 'started': time.time()}
            self._thread = threading.Thread(target=self._run, args=(session, prompt, acknowledge, prefs['use_mcp'], keys),
                                            name='jevseek-agent', daemon=False)
            self._thread.start()
            return {'session_id': session.id}

    def _run(self, session, prompt, acknowledge, use_mcp, keys):
        agent = models = None
        try:
            if self._runner is not None:
                result = self._runner(session, prompt, acknowledge, use_mcp, self._cancel)
            else:
                from .agent import Agent
                from .models import Models, Settings
                from .tools import Tools
                from .context import ContextPolicy
                from mcp_setup import load_servers
                from main import instructions
                policy = ContextPolicy(router_bytes=int(os.getenv('JEV_CONTEXT_BYTES', '24000')),
                                       model_bytes=int(os.getenv('DS_CONTEXT_BYTES', '96000')))
                models = Models(session, Settings.environment(), credentials=keys)
                tools = Tools(session.workspace, session.directory / 'terminal', load_servers() if use_mcp else {})
                agent = Agent(session, models, tools, policy, instructions(), cancel=self._cancel)
                result = agent.run(prompt, acknowledge_pending=acknowledge)
            self._transient(session.id, 'result', result)
        except BaseException as exc:
            # Do not leak SDK headers, literal config credentials, or exception payloads.
            message = f'{type(exc).__name__}: could not start the run. Check API keys, workspace and MCP availability in Settings. Another process may hold this session.'
            try:
                with session.lock:
                    session.reload()
                    # Preserve the user's request even when initial provider/tool setup fails.
                    if prompt: session.append('user', text=prompt)
                    session.append('error', stage='startup', error=type(exc).__name__, message=message)
            except Exception:
                pass
            self._transient(session.id, 'result', {'session_id': session.id, 'status': 'blocked', 'summary': message})
        finally:
            try:
                if agent is not None: agent.close()
                elif models is not None: models.close()
            except Exception:
                pass
            with self._guard:
                self._active = None
            self._transient(session.id, 'desktop_idle', {})

    @endpoint
    def cancel_run(self):
        with self._guard:
            if self._active:
                self._cancel.set()
                self._active['stopping'] = True
            return {'active': dict(self._active) if self._active else None}

    def _request_close(self):
        """Refuse to kill uncertain native effects; user closes again after stop."""
        with self._guard:
            if self._active:
                self.cancel_run()
                self._transient(self._active['session_id'], 'desktop_notice', {
                    'message': 'Stopping safely before closing. Native tools may need time to return. Close the window again once the run has stopped.'})
                return False
        return True

    @endpoint
    def compact_session(self, session_id):
        with self._guard:
            if self._active: raise DesktopError('Wait for the active run to finish before compacting history.')
            from .context import Context, ContextPolicy
            session = self._session(session_id)
            with session.lock:
                session.reload()
                policy = ContextPolicy(router_bytes=int(os.getenv('JEV_CONTEXT_BYTES', '24000')),
                                       model_bytes=int(os.getenv('DS_CONTEXT_BYTES', '96000')))
                for audience in ('router', 'model'): Context(session, policy).build(audience, force=True)
        return {'message': 'Factual history compacted locally. No model or tool ran.'}

    def _artifacts(self, session):
        rows = []
        for event in session.events:
            for key, label in (('request', 'Tool input'), ('artifact', 'Tool record'),
                               ('full_output', 'Tool output'), ('checkpoint', 'Context checkpoint')):
                reference = event['data'].get(key)
                if not isinstance(reference, str): continue
                path = Path(reference)
                if not path.is_absolute(): path = session.directory / path
                path = path.resolve()
                if not path.is_relative_to(session.directory) or not path.is_file(): continue
                rows.append({'id': f"{event['seq']}:{key}", 'name': path.name, 'kind': label,
                             'tool': event['data'].get('tool', event['data'].get('audience', 'context')),
                             'time': event['time'], 'bytes': path.stat().st_size, '_path': path})
        return rows

    @endpoint
    def list_artifacts(self, session_id):
        session, _ = self._snapshot(session_id)
        return [{k: v for k, v in row.items() if k != '_path'} for row in self._artifacts(session)]

    @endpoint
    def read_artifact(self, session_id, artifact_id):
        session, _ = self._snapshot(session_id)
        row = next((r for r in self._artifacts(session) if r['id'] == artifact_id), None)
        if row is None: raise DesktopError('This file is not an available artifact of the selected conversation.')
        # Redact before excerpting; a known secret may straddle the preview boundary.
        overlap = max((len(s.encode('utf-8')) for s in self._redactor.secrets), default=0) + 64
        with row['_path'].open('rb') as source: raw = source.read(65537 + overlap)
        clean = self._redactor.text(raw.decode('utf-8', errors='replace'))
        preview = clean.encode('utf-8')[:65536].decode('utf-8', errors='replace')
        return {'name': row['name'], 'text': preview,
                'truncated': len(raw) > 65536, 'bytes': row['bytes']}

    @endpoint
    def open_external(self, url):
        if not isinstance(url, str) or len(url) > 4096 or any(ord(c) < 32 for c in url):
            raise DesktopError('Invalid link.')
        parsed = urlsplit(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise DesktopError('Only HTTP and HTTPS links can open in your browser.')
        webbrowser.open(url, new=2)
        return True
