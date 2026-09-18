"""Provider credentials in the OS vault, never in project files or browser storage.

Windows uses native CredRead/CredWrite with LOCAL_MACHINE persistence: no plugin
discovery, roaming, shadow copies, or plaintext fallback. One vault record makes
the two-key update atomic at the storage layer.
Secrets are never exported to os.environ (and thus not inherited by tool shells).
"""
from __future__ import annotations

import json
import os
import sys
import threading

PROVIDERS = ('deepseek', 'jev')
ENV_NAMES = {'deepseek': ('DS_KEY', 'DEEPSEEK_API_KEY', 'LLM_API_KEY'),
             'jev': ('JEV_KET', 'TYPESAFE_API_KEY')}


class CredentialError(ValueError):
    """Safe, intentionally user-visible message; never interpolate a secret."""


def environment_keys():
    return {provider: next((os.environ[n] for n in names if os.getenv(n)), '')
            for provider, names in ENV_NAMES.items()}


def validate_key(value):
    if not isinstance(value, str): raise CredentialError('Paste an API key as text.')
    value = value.strip()
    if not 8 <= len(value) <= 512 or not all(33 <= ord(c) <= 126 for c in value):
        raise CredentialError('API keys must be 8–512 printable characters with no spaces or line breaks.')
    return value


class WindowsVault:
    """One native record. keyring's multi-user emulation retains shadow copies,
    which is inappropriate for explicit secret rotation/removal in this app.
    """
    def __init__(self):
        import win32cred
        import pywintypes
        self._api = win32cred
        self._os_error = pywintypes.error

    def get_password(self, service, account):
        try:
            record = self._api.CredRead(service, self._api.CRED_TYPE_GENERIC)
        except self._os_error as exc:
            if exc.winerror == 1168: return None
            raise
        if record['UserName'] != account: raise ValueError('Credential target belongs to another account')
        return record['CredentialBlob'].decode('utf-16-le')

    def set_password(self, service, account, value):
        self._api.CredWrite({'Type': self._api.CRED_TYPE_GENERIC, 'TargetName': service,
                             'UserName': account, 'CredentialBlob': value,
                             'Comment': 'JevSeek provider credentials',
                             'Persist': self._api.CRED_PERSIST_LOCAL_MACHINE}, 0)

    def delete_password(self, service, account):
        if self.get_password(service, account) is not None:
            self._api.CredDelete(service, self._api.CRED_TYPE_GENERIC, 0)


class CredentialStore:
    def __init__(self, backend=None, service='JevSeek', account='provider-keys-v1'):
        self._backend = backend
        self._service = service
        self._account = account
        self._lock = threading.RLock()
        if backend is None and sys.platform == 'win32':
            try:
                self._backend = WindowsVault()
            except ImportError:
                pass

    @property
    def supported(self): return self._backend is not None

    def _load(self):
        if self._backend is None:
            raise CredentialError('Secure key storage is unavailable. Windows Credential Manager is required for in-app key setup.')
        try:
            raw = self._backend.get_password(self._service, self._account)
            if raw is None: return {}
            record = json.loads(raw)
            if record.get('version') != 1 or not isinstance(record.get('keys'), dict): raise ValueError()
            keys = record['keys']
            if set(keys) - set(PROVIDERS): raise ValueError()
            return {name: validate_key(value) for name, value in keys.items()}
        except Exception:
            raise CredentialError('Could not read the OS credential vault. Unlock your Windows account and try again. No key was displayed or overwritten.') from None

    def load(self):
        with self._lock: return self._load()

    def update(self, changes):
        if not isinstance(changes, dict) or not changes or set(changes) - set(PROVIDERS):
            raise CredentialError('Choose a supported provider to update.')
        validated = {name: None if value is None else validate_key(value) for name, value in changes.items()}
        with self._lock:
            keys = self._load()
            for name, value in validated.items():
                if value is None: keys.pop(name, None)
                else: keys[name] = value
            try:
                # Keep an empty record on removal: idempotent, atomic, no delete/read race.
                self._backend.set_password(self._service, self._account,
                                           json.dumps({'version': 1, 'keys': keys}, separators=(',', ':')))
            except Exception:
                raise CredentialError('Could not save to Windows Credential Manager. Nothing was written to a project file. Try again after unlocking your account.') from None
            return keys
