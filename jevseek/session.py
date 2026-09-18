"""Append-only local sessions. Persist intent before effects; never replay effects."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time
import uuid
from filelock import FileLock


class SessionError(RuntimeError):
    pass


class Redactor:
    def __init__(self, secrets=()):
        self.secrets = sorted({v for v in secrets if isinstance(v, str) and len(v) >= 8}, key=len, reverse=True)

    @classmethod
    def environment(cls):
        return cls(v for k, v in os.environ.items() if re.search(r'KEY|TOKEN|SECRET|PASSWORD', k, re.I))

    def text(self, value):
        for secret in self.secrets:
            value = value.replace(secret, '[REDACTED]')
        return re.sub(r'\b(?:sk-[A-Za-z0-9_-]{16,}|apikey_[A-Za-z0-9_-]{16,})\b', '[REDACTED]', value)

    def clean(self, value):
        if isinstance(value, str): return self.text(value)
        if isinstance(value, dict): return {self.text(str(k)): self.clean(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)): return [self.clean(v) for v in value]
        return value


class Session:
    """Caller holds lock throughout a run. Subscribers receive redacted events."""
    VERSION = 1

    def __init__(self, directory: Path, redactor=None, on_event=None):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'events.jsonl'
        self.lock = FileLock(str(self.directory / 'run.lock'), timeout=0)
        self.redactor = redactor or Redactor.environment()
        self.on_event = on_event or (lambda event: None)
        self.events = []

    @classmethod
    def create(cls, home, workspace, **kwargs):
        s = cls(Path(home) / uuid.uuid4().hex, **kwargs)
        with s.lock:
            s.append('session', workspace=str(Path(workspace).resolve()), session_id=s.id)
        return s

    @classmethod
    def open(cls, home, session_id, **kwargs):
        if not re.fullmatch(r'[a-f0-9]{32}', session_id): raise SessionError('Invalid session id')
        path = Path(home) / session_id
        if not (path / 'events.jsonl').is_file(): raise SessionError('Session not found')
        return cls(path, **kwargs)

    @property
    def id(self): return self.directory.name

    def reload(self):
        """Recover only an incomplete final record. Corruption inside log is fatal."""
        self.events = []
        if not self.path.exists(): return
        raw = self.path.read_bytes()
        offset = 0
        lines = raw.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if not line.endswith(b'\n') and i == len(lines)-1:
                (self.directory / f'incomplete-{time.time_ns()}.bin').write_bytes(line)
                with self.path.open('r+b') as f: f.truncate(offset)
                break
            try:
                e = json.loads(line)
                if e['version'] != self.VERSION or e['seq'] != len(self.events)+1: raise ValueError()
            except (ValueError, KeyError, TypeError) as exc:
                raise SessionError('Corrupt session log; do not replay tools') from exc
            self.events.append(e)
            offset += len(line)
        if not self.events or self.events[0]['kind'] != 'session': raise SessionError('Missing session header')

    @property
    def workspace(self): return Path(self.events[0]['data']['workspace'])

    def append(self, kind, **data):
        event = {'version': self.VERSION, 'session_id': self.id, 'seq': len(self.events)+1,
                 'time': time.time(), 'kind': kind, 'data': self.redactor.clean(data)}
        with self.path.open('a', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n'); f.flush(); os.fsync(f.fileno())
        self.events.append(event)
        # UI subscriber failures must not change execution/persistence semantics.
        try: self.on_event(event)
        except Exception: pass
        return event

    def transient(self, kind, **data):
        try: self.on_event({'version': self.VERSION, 'session_id': self.id, 'seq': None,
                            'time': time.time(), 'kind': kind, 'data': self.redactor.clean(data)})
        except Exception: pass

    def artifact(self, call_id, arguments, observation):
        folder = self.directory / 'artifacts'; folder.mkdir(exist_ok=True)
        record = self.redactor.clean({'arguments': arguments, 'observation': observation})
        path = folder / f'{call_id}.json'
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        output = folder / f'{call_id}.txt'
        output.write_text(record['observation'].get('text', ''), encoding='utf-8')
        return str(path), str(output)

    def pending(self):
        started = {e['data']['call_id']: e for e in self.events if e['kind'] == 'tool_started'}
        finished = {e['data']['call_id'] for e in self.events if e['kind'] in ('tool_finished', 'tool_uncertain')}
        pending=[e for key, e in started.items() if key not in finished]
        # Soft-timeout commands may still have effects after their wait returned.
        last_shell=next((e for e in reversed(self.events) if e['kind']=='tool_finished' and e['data']['tool']=='bash'),None)
        acknowledged={e['data']['call_id'] for e in self.events if e['kind']=='tool_uncertain'}
        if last_shell and last_shell['data'].get('status')=='running' and last_shell['data']['call_id'] not in acknowledged:
            pending.append(last_shell)
        return pending

    def saved_result(self):
        if self.pending(): return None
        last=next((e for e in reversed(self.events) if e['kind'] in ('final','error','user','run_started')),None)
        if last and last['kind']=='final':
            return {'session_id':self.id,'status':last['data']['status'],'summary':last['data']['summary'],
                    'session_dir':str(self.directory)}
        return None

    def acknowledge_pending(self):
        for e in self.pending():
            self.append('tool_uncertain', call_id=e['data']['call_id'], tool=e['data']['tool'],
                        note='User acknowledged interrupted execution. Effects unknown: inspect current state before retrying.')
