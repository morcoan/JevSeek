"""Opt-in, pinned local Bonsai installer and owned localhost Prism server.

No provider keys are sent to downloads or inherited by the model process.
Only a successful compatibility probe changes the selected provider.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import threading
import time
import zipfile

import httpx
from filelock import FileLock

RELEASE = 'https://github.com/PrismML-Eng/llama.cpp/releases/download/prism-b10685-7dffb15/'
MODELS = {
    'prism': dict(label='Prism Bonsai 2 · official', repo='prism-ml/Ternary-Bonsai-2-27B-gguf', revision='6ed5e12bf84b7a63069882c91dd9e9218647d17b', file='Ternary-Bonsai-2-27B-PQ2_0.gguf', size=7206168928, sha256='3907dc1658db1f78a9826bf8d5bcb8dc65db0d466388937af57f2294fae62ec1'),
    'crack': dict(label='Bonsai 2 CRACK · community', repo='dealignai/Bonsai-2-27B-Ternary-CRACK-GGUF', revision='3d36486a5fb2a3868116b8f6e768179e2391d28d', file='Bonsai-2-27B-PQ2_0-CRACK.gguf', size=7206168928, sha256='5b24ea3eebc3e0bccd05fb474eb88b10c57699d71a5db2f29485e3789a70d55d'),
}
RUNTIMES = {
    'cuda': [('llama-prism-b10685-7dffb15-bin-win-cuda-13.3-x64.zip', 144928999, '0b0e44045b0b55bb892c5afa8fd4c988194c47c02967ff1da55cd01c0c8eda69'), ('cudart-llama-bin-win-cuda-13.3-x64.zip', 390970417, '1462a050eb4c684921ba51dcc4cc488a036674c3e73e9945ee705b854808d03e')],
}
SUMMARY_SCHEMA = {'type': 'object', 'properties': {'summary': {'type': 'string'}}, 'required': ['summary'], 'additionalProperties': False}


class SetupCancelled(Exception):
    pass


def isolated_environment():
    return {k: v for k, v in os.environ.items() if k.upper() != 'JEV_KET' and not k.upper().startswith('LLAMA_ARG_') and not any(s in k.upper() for s in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD'))}


class BonsaiManager:
    def __init__(self, state_dir, search_dirs=()):
        self.root = Path(state_dir) / 'bonsai'
        self.config = self.root / 'provider.json'
        self.search_dirs = [Path(p) for p in search_dirs]
        self._guard = threading.RLock()
        self._cancel = threading.Event()
        self._thread = None
        self._process = None
        self._job = None
        self._url = None
        self._token = None
        self._loaded = None
        self._status = dict(phase='idle', message='Choose a local model to get started.', downloaded=0, total=0, speed=0, busy=False)

    def selection(self):
        try:
            data = json.loads(self.config.read_text('utf-8'))
            return data if data.get('provider') in ('deepseek', *MODELS) else {'provider': 'deepseek'}
        except (OSError, ValueError, AttributeError):
            return {'provider': 'deepseek'}

    def status(self):
        with self._guard:
            return {**self._status, 'selected': self.selection()['provider'], 'running': self._process is not None and self._process.poll() is None,
                    'models': [{'id': k, 'label': v['label'], 'bytes': v['size']} for k, v in MODELS.items()]}

    def _update(self, **values):
        with self._guard: self._status.update(values)

    def _check(self):
        if self._cancel.is_set(): raise SetupCancelled()

    def _save(self, data):
        self.root.mkdir(parents=True, exist_ok=True)
        temp = self.config.with_suffix('.tmp')
        temp.write_text(json.dumps(data), 'utf-8')
        os.replace(temp, self.config)

    def setup(self, variant):
        if variant not in MODELS: raise ValueError('Choose a listed Bonsai model.')
        if platform.system() != 'Windows' or platform.machine().lower() not in ('amd64', 'x86_64'):
            raise ValueError('Automatic Bonsai setup currently supports Windows x64.')
        with self._guard:
            if self._status['busy']: raise ValueError('A model setup is already running.')
            self._cancel.clear()
            self._update(busy=True, phase='checking', message='Checking hardware and existing downloads…', downloaded=0, total=0, speed=0)
            self._thread = threading.Thread(target=self._setup, args=(variant,), name='bonsai-setup', daemon=False)
            self._thread.start()
        return self.status()

    def cancel(self):
        self._cancel.set()
        if self._status['busy']: self._update(message='Cancelling setup… waiting for the current network operation to return.')
        return self.status()

    def use_deepseek(self):
        with self._guard:
            if self._status['busy']: raise ValueError('Cancel setup and wait before switching providers.')
            self.root.mkdir(parents=True, exist_ok=True)
            with FileLock(str(self.root / 'setup.lock'), timeout=0):
                self._save({'provider': 'deepseek'})
                self._stop()
                self._update(phase='idle', message='DeepSeek selected. Local GPU memory released.')
            return self.status()

    def _hash(self, path, expected, size):
        self._update(phase='verifying', message='Verifying SHA-256 integrity…', total=size, downloaded=0, speed=0)
        digest = hashlib.sha256(); done = 0
        with path.open('rb') as handle:
            while chunk := handle.read(8 * 1024 * 1024):
                self._check(); digest.update(chunk); done += len(chunk)
                self._update(downloaded=done)
        return done == size and digest.hexdigest() == expected

    def _download(self, url, path, size, sha):
        self._check()
        if path.exists():
            if self._hash(path, sha, size): return path
            path.unlink()
        part = path.with_suffix(path.suffix + '.part')
        offset = part.stat().st_size if part.exists() else 0
        if offset > size: part.unlink(); offset = 0
        if shutil.disk_usage(path.parent).free < size - offset + 256 * 1024**2:
            raise ValueError('Not enough disk space. Free space and retry; partial downloads are retained.')
        if offset < size:
            self._update(phase='downloading', message='Downloading ' + path.name, total=size, downloaded=offset, speed=0)
            with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(30, read=45), trust_env=False) as client:
                with client.stream('GET', url, headers={'Range': f'bytes={offset}-', 'Accept-Encoding': 'identity'} if offset else {'Accept-Encoding': 'identity'}) as response:
                    response.raise_for_status()
                    if response.status_code == 206:
                        if not response.headers.get('content-range', '').startswith(f'bytes {offset}-'):
                            raise ValueError('Download server returned an invalid byte range. Retry setup.')
                    elif response.status_code == 200: offset = 0
                    else: raise ValueError('Unexpected download response.')
                    start = time.monotonic(); initial = offset
                    with part.open('ab' if offset else 'wb') as handle:
                        for chunk in response.iter_bytes(1024 * 1024):
                            self._check(); offset += len(chunk)
                            if offset > size: raise ValueError('Download exceeded its pinned size.')
                            handle.write(chunk)
                            self._update(downloaded=offset, speed=int((offset-initial)/max(.1, time.monotonic()-start)))
                        handle.flush(); os.fsync(handle.fileno())
        if not self._hash(part, sha, size):
            part.unlink(missing_ok=True)
            raise ValueError('Integrity check failed. Retry to download a clean copy.')
        os.replace(part, path)
        return path

    @staticmethod
    def _extract(archive, target):
        with zipfile.ZipFile(archive) as source:
            for item in source.infolist():
                dest = (target / item.filename).resolve()
                if not dest.is_relative_to(target.resolve()) or (item.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Unsafe runtime archive entry.')
            source.extractall(target)

    def _hardware(self):
        # CUDA 13.3 needs a recent driver. Older/other GPUs use portable CPU kernels.
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=memory.free,driver_version', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), env=isolated_environment())
            rows = [r.split(',') for r in result.stdout.strip().splitlines()]
            if any(int(r[0]) >= 9000 and int(r[1].strip().split('.')[0]) >= 610 for r in rows): return 'cuda'
        except (OSError, ValueError, subprocess.SubprocessError): pass
        return 'cpu'

    def _setup(self, variant):
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with FileLock(str(self.root / 'setup.lock'), timeout=0):
                self._stop()
                self._check()
                info = MODELS[variant]
                model_dir = self.root / 'models'; model_dir.mkdir(exist_ok=True)
                model = model_dir / info['file']
                candidates = [model, *(p / info['file'] for p in self.search_dirs)]
                existing = self.selection().get('model_path')
                if existing: candidates.append(Path(existing))
                found = False
                for candidate in candidates:
                    if candidate.is_file() and candidate.stat().st_size == info['size'] and self._hash(candidate, info['sha256'], info['size']):
                        model = candidate; found = True; break
                if not found:
                    self._download(f"https://huggingface.co/{info['repo']}/resolve/{info['revision']}/{info['file']}", model, info['size'], info['sha256'])
                backend = self._hardware()
                runtime = self._runtime(backend)
                self._check()
                try:
                    self._launch(runtime, model, backend)
                except SetupCancelled: raise
                except Exception:
                    if backend != 'cuda': raise
                    self._stop()
                    self._update(message='GPU startup failed. Preparing the slower CPU fallback…')
                    backend = 'cpu'; runtime = self._runtime(backend)
                    self._launch(runtime, model, backend)
                self._check()
                self._save({'provider': variant, 'model_path': str(model.resolve()), 'runtime': str(runtime.resolve()), 'backend': backend})
                self._loaded = variant
                self._update(phase='ready', message=f"{info['label']} is ready ({'NVIDIA GPU' if backend == 'cuda' else 'CPU — slower'}). DeepSeek is no longer required.", downloaded=0, total=0, speed=0)
        except SetupCancelled:
            self._stop(); self._update(phase='cancelled', message='Setup cancelled. Partial downloads are kept for retry.', speed=0)
        except Exception as exc:
            self._stop()
            # Do not surface request headers, signed redirect URLs, or provider keys.
            message = str(exc) if isinstance(exc, ValueError) else f'{type(exc).__name__}: setup failed. Check disk space, network and available memory, then retry.'
            self._update(phase='error', message=message, speed=0)
        finally: self._update(busy=False)

    def _runtime(self, backend):
        # The CPU-only release's auto-selected optimized DLL crashes on PQ2_0
        # on tested hardware. The CUDA distribution includes a verified generic
        # CPU backend too; use that same pinned bundle for both execution modes.
        backend = 'cuda'
        cache = self.root / 'downloads'; cache.mkdir(exist_ok=True)
        dest = self.root / ('runtime-' + backend)
        marker = dest / '.verified'
        if marker.is_file() and (dest / 'llama-server.exe').is_file(): return dest
        temp = self.root / ('runtime-' + backend + '.tmp')
        if temp.exists(): shutil.rmtree(temp)
        temp.mkdir()
        for name, size, sha in RUNTIMES[backend]:
            archive = self._download(RELEASE + name, cache / name, size, sha)
            self._check(); self._update(phase='extracting', message='Installing verified Prism runtime…', downloaded=0, total=0)
            self._extract(archive, temp)
        exe = list(temp.rglob('llama-server.exe'))
        if len(exe) != 1: raise ValueError('Runtime archive did not contain one model server.')
        # Release archives may wrap files in a directory; preserve the complete tree.
        relative = exe[0].parent.relative_to(temp)
        if dest.exists(): shutil.rmtree(dest)
        os.replace(temp, dest)
        runtime = dest / relative
        (runtime / '.verified').write_text('prism-b10685-7dffb15', 'ascii')
        return runtime

    def _launch(self, runtime, model, backend):
        import secrets
        self._check()
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
        self._token = secrets.token_hex(32)
        self._url = f'http://127.0.0.1:{port}/v1'
        args = [str(runtime / 'llama-server.exe'), '-m', str(model), '--alias', 'bonsai', '--host', '127.0.0.1', '--port', str(port), '--api-key', self._token,
                '--spec-type', 'none', '-ngl', 'auto' if backend == 'cuda' else '0', '-fa', 'on', '-c', '32768', '-np', '1', '-b', '1024', '-ub', '256',
                '--jinja', '--reasoning', 'off', '--temp', '0.2', '--no-webui']
        self._update(phase='loading', message='Loading Bonsai on ' + ('NVIDIA GPU…' if backend == 'cuda' else 'CPU (this can take several minutes)…'), downloaded=0, total=0, speed=0)
        with (self.root / 'server.log').open('wb') as log:
            self._process = subprocess.Popen(args, cwd=runtime, env=isolated_environment(), stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if os.name == 'nt':
            import win32api, win32con, win32job
            self._job = win32job.CreateJobObject(None, '')
            limits = win32job.QueryInformationJobObject(self._job, win32job.JobObjectExtendedLimitInformation)
            limits['BasicLimitInformation']['LimitFlags'] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self._job, win32job.JobObjectExtendedLimitInformation, limits)
            handle = win32api.OpenProcess(win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE, False, self._process.pid)
            try: win32job.AssignProcessToJobObject(self._job, handle)
            finally: handle.Close()
        with httpx.Client(timeout=2, trust_env=False, headers={'Authorization': 'Bearer ' + self._token}) as client:
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                self._check()
                if self._process.poll() is not None: raise ValueError('Model server exited. Close other GPU apps or free system memory, then retry.')
                try:
                    if client.get(self._url.removesuffix('/v1') + '/health').status_code == 200: break
                except httpx.HTTPError: pass
                time.sleep(.5)
            else: raise ValueError('Model loading timed out. Free memory and retry.')
        self._update(phase='testing', message='Checking native tool calls and structured answers…')
        self._probe()

    def _probe(self):
        schema = {'type': 'object', 'properties': {'path': {'type': 'string'}}, 'required': ['path'], 'additionalProperties': False}
        common = dict(model='bonsai', max_tokens=128, chat_template_kwargs={'enable_thinking': False})
        with httpx.Client(timeout=120, trust_env=False, headers={'Authorization': 'Bearer ' + self._token}) as client:
            r = client.post(self._url + '/chat/completions', json={**common, 'messages': [{'role': 'user', 'content': 'Call selected_action with path README.md.'}], 'tools': [{'type': 'function', 'function': {'name': 'selected_action', 'parameters': schema}}], 'tool_choice': {'type': 'function', 'function': {'name': 'selected_action'}}, 'parallel_tool_calls': False})
            r.raise_for_status(); choice = r.json()['choices'][0]; calls = choice['message'].get('tool_calls', [])
            if choice['finish_reason'] != 'tool_calls' or len(calls) != 1 or calls[0]['function']['name'] != 'selected_action' or json.loads(calls[0]['function']['arguments']) != {'path': 'README.md'}:
                raise ValueError('Local model failed the native tool-call compatibility check. The previous provider selection has not changed.')
            self._check()
            r = client.post(self._url + '/chat/completions', json={**common, 'messages': [{'role': 'system', 'content': 'Return only JSON, no Markdown.'}, {'role': 'user', 'content': 'Return summary: ready'}], 'response_format': {'type': 'json_schema', 'json_schema': {'name': 'answer', 'strict': True, 'schema': SUMMARY_SCHEMA}}})
            r.raise_for_status(); choice = r.json()['choices'][0]; value = json.loads(choice['message']['content'])
            if choice['finish_reason'] != 'stop' or set(value) != {'summary'} or not isinstance(value['summary'], str): raise ValueError('Local model failed the structured-answer check.')

    def connection(self):
        """Called on the agent worker, not the UI thread. Never silently fall back to cloud."""
        if self._status['busy']: raise ValueError('Wait for local model setup to finish.')
        config = self.selection(); variant = config['provider']
        if variant == 'deepseek': return None
        if self._process is None or self._process.poll() is not None or self._loaded != variant:
            self._cancel.clear(); self._stop()
            try:
                model = Path(config['model_path']); runtime = Path(config['runtime'])
                if not runtime.resolve().is_relative_to(self.root.resolve()): raise ValueError('Local runtime path is outside the managed installation.')
                info = MODELS[variant]
                if not self._hash(model, info['sha256'], info['size']): raise ValueError('Local model integrity changed. Run setup again before using it.')
                self._launch(runtime, model, config['backend'])
            except BaseException:
                self._stop(); raise
            self._loaded = variant
            self._update(phase='ready', message='Local Bonsai ready.')
        return {'base_url': self._url, 'api_key': self._token}

    def _stop(self):
        if self._process is not None:
            if self._process.poll() is None:
                self._process.terminate()
                try: self._process.wait(timeout=10)
                except subprocess.TimeoutExpired: self._process.kill(); self._process.wait(timeout=10)
            self._process = None
        if self._job is not None:
            self._job.Close(); self._job = None
        self._url = self._token = self._loaded = None

    def close(self):
        self._cancel.set()
        if self._thread and self._thread.is_alive(): self._thread.join(timeout=1)
        if not self._thread or not self._thread.is_alive(): self._stop()
