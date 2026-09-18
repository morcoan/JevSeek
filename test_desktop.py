"""Offline desktop bridge contracts. No providers, MCP, or native tools required."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from jevseek.desktop import DesktopAPI
from jevseek.session import Session, Redactor


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / '.jevseek' / 'sessions'
        self.api = DesktopAPI(self.root)

    def data(self, result):
        self.assertTrue(result['ok'], result)
        return result['data']

    def session(self, pending=False):
        s = Session.create(self.home, self.root)
        s.append('user', text='Review the build engine')
        s.append('tool_started', call_id='one', tool='read', target='engine.py')
        if not pending:
            artifact, output = s.artifact('one', {'path': 'engine.py'}, {'text': 'hello world'})
            s.append('tool_finished', call_id='one', tool='read', status='ok', text='hello world', artifact=artifact, full_output=output)
            s.append('final', status='completed', summary='Reviewed without changes.')
        return s

    def test_bootstrap_offline_and_new_profile(self):
        with patch.dict('sys.modules', {'jevseek.models': None, 'jevseek.tools': None}):
            boot = self.data(self.api.bootstrap())
        self.assertEqual(boot['sessions'], [])
        self.assertIsNone(boot['active'])
        self.assertTrue(boot['desktop'])
        self.assertEqual(boot['preferences']['theme'], 'system')

    def test_saved_history_does_not_replay_or_import_sdks(self):
        s = self.session()
        before = s.path.read_bytes()
        with patch.dict('sys.modules', {'jevseek.models': None, 'jevseek.tools': None}):
            snapshot = self.data(self.api.get_session(s.id))
            listing = self.data(self.api.list_sessions())
        self.assertEqual(snapshot['meta']['status'], 'completed')
        self.assertEqual(listing['sessions'][0]['title'], 'Review the build engine')
        self.assertEqual(s.path.read_bytes(), before)
        self.assertFalse(self.api.start_run(s.id, None)['ok'])

    def test_invalid_id_and_missing_session_are_safe(self):
        for id in ('../.env', '/etc/passwd', 'A' * 32, 'a' * 32, None):
            self.assertFalse(self.api.get_session(id)['ok'])
        self.assertFalse(self.api.read_artifact('x', '../../.env')['ok'])

    def test_torn_tail_read_is_non_mutating(self):
        s = self.session()
        with s.path.open('ab') as file: file.write(b'{"partial":')
        before = s.path.read_bytes()
        snapshot = self.data(self.api.get_session(s.id))
        self.assertTrue(snapshot['meta']['trailing'])
        self.assertEqual(s.path.read_bytes(), before)
        self.assertFalse(list(s.directory.glob('incomplete-*')))

    def test_corrupt_log_is_rejected_and_other_sessions_survive(self):
        good = self.session()
        bad = self.session()
        with bad.path.open('ab') as file: file.write(b'{"bad":1}\n')
        self.assertFalse(self.api.get_session(bad.id)['ok'])
        listing = self.data(self.api.list_sessions())
        self.assertEqual(listing['unreadable'], 1)
        self.assertEqual(listing['sessions'][0]['session_id'], good.id)

    def test_artifacts_only_from_selected_session_and_limit(self):
        s = self.session()
        files = self.data(self.api.list_artifacts(s.id))
        self.assertEqual({r['kind'] for r in files}, {'Tool record', 'Tool output'})
        self.assertTrue(all('_path' not in r for r in files))
        output = next(row for row in files if row['kind'] == 'Tool output')
        result = self.data(self.api.read_artifact(s.id, output['id']))
        self.assertEqual(result['text'], 'hello world')
        self.assertFalse(result['truncated'])
        (s.directory / 'artifacts' / 'one.txt').write_text('A' * 70000)
        result = self.data(self.api.read_artifact(s.id, output['id']))
        self.assertTrue(result['truncated'])
        self.assertEqual(len(result['text']), 65536)
        # Even a referenced external path is not exposed.
        outside = self.root / 'private.txt'; outside.write_text('private')
        s.append('tool_finished', call_id='two', tool='read', status='ok', full_output=str(outside))
        self.assertEqual(len(self.data(self.api.list_artifacts(s.id))), 2)
        self.assertFalse(self.api.read_artifact(s.id, str(outside))['ok'])

    def test_secret_redaction_at_bridge_and_artifact_boundary(self):
        secret = 'test_desktop_secret_123456789'
        s = self.session()
        (s.directory / 'artifacts' / 'one.txt').write_text(secret)
        self.api._redactor = Redactor([secret])
        self.api._transient(s.id, 'model_progress', {'message': secret})
        data = self.data(self.api.poll(0))
        self.assertNotIn(secret, json.dumps(data))
        self.assertEqual(self.data(self.api.read_artifact(s.id, '4:full_output'))['text'], '[REDACTED]')

    def test_secret_straddling_artifact_preview_boundary_is_redacted(self):
        secret = 'long_secret_for_preview_boundary_123456789'
        s = self.session()
        (s.directory / 'artifacts' / 'one.txt').write_text('a' * 65530 + secret + 'tail')
        self.api._redactor = Redactor([secret])
        result = self.data(self.api.read_artifact(s.id, '4:full_output'))
        self.assertNotIn('long_', result['text'])
        self.assertTrue(result['truncated'])
        self.assertLessEqual(len(result['text'].encode('utf-8')), 65536)

    def test_malformed_metadata_does_not_hide_healthy_sessions(self):
        self.session()
        bad = self.session()
        events = [json.loads(line) for line in bad.path.read_text().splitlines()]
        events[-1].pop('time')
        bad.path.write_text(''.join(json.dumps(e) + '\n' for e in events))
        listing = self.data(self.api.list_sessions())
        self.assertEqual(len(listing['sessions']), 1)
        self.assertEqual(listing['unreadable'], 1)

    def test_preferences_validate_and_round_trip(self):
        prefs = {'theme': 'dark', 'workspace': str(self.root), 'use_mcp': False}
        self.assertEqual(self.data(self.api.save_preferences(prefs)), prefs)
        self.assertEqual(self.data(DesktopAPI(self.root).bootstrap())['preferences'], prefs)
        for invalid in ({**prefs, 'theme': 'fake'}, {**prefs, 'use_mcp': 'false'}, {**prefs, 'workspace': str(self.root / 'missing')}, {**prefs, 'key': 'secret'}):
            self.assertFalse(self.api.save_preferences(invalid)['ok'])
        self.assertEqual(self.data(self.api.bootstrap())['preferences'], prefs)

    def test_progress_dedup_cursor_and_reset(self):
        for i in range(2055): self.api._transient('a' * 32, 'model_progress', {'characters': i})
        data = self.data(self.api.poll(0))
        self.assertTrue(data['reset'])
        self.assertEqual(len(data['events']), 2048)
        self.assertEqual(self.data(self.api.poll(data['cursor']))['events'], [])
        self.assertFalse(self.api.poll(-1)['ok'])

    def test_run_is_nonblocking_single_worker_and_cooperative_stop(self):
        ready = threading.Event()
        def runner(session, prompt, acknowledge, mcp, cancel):
            with session.lock:
                session.reload(); session.append('user', text=prompt)
                ready.set(); cancel.wait(3)
                session.append('error', stage='cancelled', error='Cancelled')
                return {'session_id': session.id, 'status': 'cancelled', 'summary': 'Stopped.'}
        api = DesktopAPI(self.root, runner=runner)
        result = self.data(api.start_run(None, 'Read only'))
        self.assertTrue(ready.wait(2))
        self.assertFalse(api.start_run(None, 'Another')['ok'])
        self.assertFalse(api.compact_session(result['session_id'])['ok'])
        # Read while the writer holds its lock must work and not repair anything.
        self.assertEqual(self.data(api.get_session(result['session_id']))['meta']['status'], 'running')
        self.assertFalse(api._request_close())
        api._thread.join(3)
        self.assertFalse(api._thread.is_alive())
        self.assertTrue(api._request_close())
        events = self.data(api.poll(0))['events']
        self.assertTrue(any(e['kind'] == 'result' and e['data']['status'] == 'cancelled' for e in events))
        self.assertIsNone(self.data(api.poll(0))['active'])

    def test_pending_needs_explicit_ack_and_a_followup(self):
        s = self.session(pending=True)
        observed = []
        def runner(session, prompt, acknowledge, mcp, cancel):
            observed.append((prompt, acknowledge))
            return {'session_id': session.id, 'status': 'needs_input', 'summary': 'Test only.'}
        api = DesktopAPI(self.root, runner=runner)
        self.assertTrue(self.data(api.get_session(s.id))['meta']['pending'])
        self.assertFalse(api.start_run(s.id, 'Continue')['ok'])
        self.assertFalse(api.start_run(s.id, None, True)['ok'])
        self.data(api.start_run(s.id, 'I reviewed the files. Continue.', True))
        api._thread.join(3)
        self.assertEqual(observed, [('I reviewed the files. Continue.', True)])

    def test_startup_failure_preserves_prompt_without_secret_error_payload(self):
        def runner(*args): raise RuntimeError('do not expose provider headers or secrets')
        api = DesktopAPI(self.root, runner=runner)
        result = self.data(api.start_run(None, 'My initial request'))
        api._thread.join(3)
        snapshot = self.data(api.get_session(result['session_id']))
        self.assertEqual(snapshot['meta']['status'], 'blocked')
        self.assertIn('My initial request', json.dumps(snapshot))
        self.assertNotIn('do not expose provider', json.dumps(snapshot))

    def test_compaction_local_only(self):
        s = self.session()
        with patch.dict('sys.modules', {'jevseek.models': None, 'jevseek.tools': None}):
            self.data(self.api.compact_session(s.id))
        snapshot = self.data(self.api.get_session(s.id))
        self.assertEqual(snapshot['meta']['status'], 'completed')
        self.assertEqual(sum(e['kind'] == 'compaction' for e in snapshot['events']), 2)

    def test_unsafe_links_rejected(self):
        with patch('jevseek.desktop.webbrowser.open') as browser:
            for url in ('file:///etc/passwd', 'javascript:alert(1)', 'https://user:secret@example.com', '//example.com', 'https://example.com/\nunsafe'):
                self.assertFalse(self.api.open_external(url)['ok'])
            self.data(self.api.open_external('https://example.com/docs'))
            browser.assert_called_once_with('https://example.com/docs', new=2)


if __name__ == '__main__': unittest.main()
