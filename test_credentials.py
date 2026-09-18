"""Offline key-management contracts; real vault test uses a disposable namespace."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

from jevseek.credentials import CredentialStore, CredentialError, validate_key
from jevseek.desktop import DesktopAPI


class MemoryVault:
    """Test-only vault, never selected by production code."""
    def __init__(self): self.value = None; self.fail = False
    def get_password(self, service, account): return self.value
    def set_password(self, service, account, value):
        if self.fail: raise RuntimeError('Secret-bearing OS error must not escape')
        self.value = value


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.vault = MemoryVault(); self.store = CredentialStore(self.vault)
        self.api = DesktopAPI(self.temp.name, credentials=self.store)
        self.ds = 'test_deepseek_value_123456789'; self.jev = 'test_jev_value_123456789'

    def test_store_round_trip_and_blank_preserves(self):
        response = self.api.save_keys(self.ds, self.jev)
        self.assertTrue(response['ok'])
        self.assertEqual(response['data']['providers'], {'deepseek': True, 'jev': True})
        self.assertNotIn(self.ds, json.dumps(response))
        self.assertNotIn(self.jev, json.dumps(response))
        self.assertEqual(self.store.load(), {'deepseek': self.ds, 'jev': self.jev})
        new = 'replacement_key_123456789'
        self.assertTrue(self.api.save_keys(new, '')['ok'])
        self.assertEqual(self.store.load(), {'deepseek': new, 'jev': self.jev})
        self.assertFalse(self.api.save_keys('', '')['ok'])

    def test_never_writes_plaintext_or_changes_process_environment(self):
        before = dict(os.environ)
        self.api.save_keys(self.ds, self.jev)
        self.assertEqual(dict(os.environ), before)
        self.assertEqual(list(Path(self.temp.name).rglob('*')), [])
        self.assertNotIn(self.ds, json.dumps(self.api.bootstrap()))

    def test_removal_is_explicit_and_environment_fallback_is_disclosed(self):
        with patch.dict(os.environ, {'DS_KEY': 'environment_key_123456789'}):
            self.api.save_keys(self.ds, self.jev)
            self.assertEqual(self.api._provider_keys()['deepseek'], self.ds)
            response = self.api.remove_key('deepseek')
            self.assertEqual(response['data']['key_setup']['sources']['deepseek'], 'environment')
            self.assertTrue(response['data']['providers']['deepseek'])
            self.assertNotIn('deepseek', self.store.load())
            self.assertEqual(self.store.load()['jev'], self.jev)

    def test_old_and_new_values_redacted_after_rotation_and_removal(self):
        self.api.save_keys(self.ds, self.jev)
        self.api._transient('a' * 32, 'test', {'text': self.ds})
        new = 'replacement_key_123456789'
        self.api.save_keys(new, '')
        self.api.remove_key('deepseek')
        self.assertEqual(self.api._redactor.text(self.ds + ' ' + new), '[REDACTED] [REDACTED]')
        self.assertNotIn(self.ds, json.dumps(self.api.poll(0)))

    def test_no_partial_update_on_invalid_second_key_or_vault_error(self):
        self.api.save_keys(self.ds, self.jev)
        original = self.vault.value
        self.assertFalse(self.api.save_keys('valid_new_key_123456789', 'bad key')['ok'])
        self.assertEqual(self.vault.value, original)
        self.vault.fail = True
        error = self.api.save_keys('valid_new_key_123456789', '')
        self.assertFalse(error['ok'])
        self.assertNotIn('Secret-bearing', json.dumps(error))
        self.assertNotIn('valid_new_key', json.dumps(error))
        self.assertEqual(self.vault.value, original)

    def test_locked_or_corrupt_vault_fails_closed(self):
        self.vault.value = 'corrupt record'
        status = self.api.get_key_status()
        self.assertTrue(status['ok'])
        self.assertIn('vault', status['data']['key_setup']['error'])
        self.assertFalse(self.api.save_keys(self.ds, self.jev)['ok'])
        self.assertEqual(self.vault.value, 'corrupt record')

    def test_changes_rejected_during_run(self):
        self.api._active = {'session_id': 'a' * 32}
        self.assertFalse(self.api.save_keys(self.ds, self.jev)['ok'])
        self.assertFalse(self.api.remove_key('deepseek')['ok'])
        self.assertIsNone(self.vault.value)

    def test_validates_without_echoing_input(self):
        for value in ('short', 'a b' * 10, 'é' * 20, 'abc\nxyz1234', 'A' * 513, None):
            with self.assertRaises(CredentialError): validate_key(value)
        self.assertEqual(validate_key('  normal_key_123456789  '), 'normal_key_123456789')

    def test_packaged_runtime_terms_require_explicit_choice(self):
        api = DesktopAPI(self.temp.name, credentials=self.store, require_runtime_terms=True)
        self.assertFalse(api.bootstrap()['data']['runtime_terms']['accepted'])
        self.assertFalse(api.accept_runtime_terms(False)['ok'])
        self.assertFalse(api.accept_runtime_terms('true')['ok'])
        self.assertFalse(api.start_run(None, 'Never run before agreement')['ok'])
        self.assertTrue(api.accept_runtime_terms(True)['data']['accepted'])
        reopened = DesktopAPI(self.temp.name, credentials=self.store, require_runtime_terms=True)
        self.assertTrue(reopened.bootstrap()['data']['runtime_terms']['accepted'])

    def test_direct_provider_injection_does_not_export_to_shell(self):
        from jevseek.models import Models
        session = object()
        with patch('jevseek.models.OpenAI') as ds, patch('jevseek.models.TypeSafeClient') as jev:
            before = dict(os.environ)
            models = Models(session, credentials={'deepseek': self.ds, 'jev': self.jev})
            self.assertEqual(ds.call_args.kwargs['api_key'], self.ds)
            self.assertEqual(jev.call_args.kwargs['api_key'], self.jev)
            self.assertEqual(dict(os.environ), before)
            models.close()

    @unittest.skipUnless(sys.platform == 'win32', 'Windows vault validation')
    def test_actual_windows_vault_with_disposable_record(self):
        service = 'JevSeek-test-' + uuid.uuid4().hex
        store = CredentialStore(service=service)
        self.assertTrue(store.supported)
        try:
            store.update({'deepseek': self.ds, 'jev': self.jev})
            reopened = CredentialStore(service=service)
            self.assertEqual(reopened.load(), {'deepseek': self.ds, 'jev': self.jev})
            import win32cred
            native = win32cred.CredRead(service, win32cred.CRED_TYPE_GENERIC)
            self.assertEqual(native['Persist'], win32cred.CRED_PERSIST_LOCAL_MACHINE)
            store.update({'deepseek': 'rotated_test_key_123456789'})
            store.update({'deepseek': None, 'jev': None})
            self.assertEqual(reopened.load(), {})
            native = win32cred.CredRead(service, win32cred.CRED_TYPE_GENERIC)
            self.assertNotIn(self.ds.encode('utf-16-le'), native['CredentialBlob'])
            # No keyring-style previous-value backup may survive removal.
            import pywintypes
            with self.assertRaises(pywintypes.error):
                win32cred.CredRead('provider-keys-v1@' + service, win32cred.CRED_TYPE_GENERIC)
        finally:
            store._backend.delete_password(service, 'provider-keys-v1')


if __name__ == '__main__': unittest.main()
