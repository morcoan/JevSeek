"""Publication checks: real Git index/history, not just .gitignore patterns."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts'))
from public_audit import audit, audit_history, public_files, forbidden_path, scan_bytes


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Audit fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'core.autocrlf', 'false')
        (self.root/'.gitignore').write_text((Path(__file__).parent/'.gitignore').read_text())

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True).stdout

    def test_private_paths_and_examples(self):
        for name in ['.pi/avo/memory.md','.jevseek/sessions/x/events.jsonl','.env','sub/.env.local','mcp.json','secret.pfx','work/notes.txt','release/JevSeek.exe']:
            self.assertTrue(forbidden_path(name), name)
        for name in ['.env.example','mcp.example.json','jevseek/credentials.py','frontend/src/KeySetup.tsx']:
            self.assertFalse(forbidden_path(name), name)

    def test_ignore_rules_keep_local_state_out_of_candidates(self):
        for name in ['.env','mcp.json','.pi/avo/memory.md','.jevseek/events.jsonl','.local/archive/private.txt','benchmarks/results/trace.json','release/JevSeek.exe','.build-venv/file.txt']:
            path=self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('private fixture')
        (self.root/'README.md').write_text('Public')
        self.assertEqual(public_files(self.root), ['.gitignore','README.md'])
        self.assertTrue(audit(self.root)['ok'])

    def test_force_added_private_file_is_blocked(self):
        (self.root/'.env').write_text('DS_KEY=non_secret_test_value\n')
        self.git('add','-f','.env')
        result=audit(self.root, staged=True)
        self.assertFalse(result['ok'])
        self.assertNotIn('non_secret_test_value',json.dumps(result))

    def test_scans_index_even_when_worktree_is_cleaned(self):
        token='sk-'+'x'*36
        (self.root/'unsafe.py').write_text('key = '+repr(token))
        self.git('add','unsafe.py')
        (self.root/'unsafe.py').write_text('# now clean')
        self.assertFalse(audit(self.root, staged=True)['ok'])
        self.assertNotIn(token,json.dumps(audit(self.root,staged=True)))

    def test_scans_deleted_historical_secret(self):
        token='sk-'+'z'*36
        (self.root/'old.py').write_text('key = '+repr(token))
        self.git('add','old.py'); self.git('commit','-m','test fixture')
        (self.root/'old.py').unlink(); self.git('add','-u'); self.git('commit','-m','remove fixture')
        result=audit_history(self.root)
        self.assertFalse(result['ok'])
        self.assertNotIn(token,json.dumps(result))

    def test_home_path_detection_not_confused_by_urls(self):
        self.assertEqual(scan_bytes(b'https://example.com/api/v1/',username='fixture'),[])
        self.assertIn('personal_home_path',scan_bytes(b'C:/Users/fixture/private',username='fixture'))
        windows=b'C:'+bytes([92])+b'Users'+bytes([92])+b'fixture'+bytes([92])+b'private'
        self.assertIn('personal_home_path',scan_bytes(windows,username='fixture'))
        self.assertIn('known_local_secret',scan_bytes(b'a personal_dummy_value b',[b'personal_dummy_value']))


if __name__=='__main__': unittest.main()
