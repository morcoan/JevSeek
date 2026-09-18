"""Offline installer/provider regression tests; no model downloads or API charges."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import httpx
from jevseek.bonsai import BonsaiManager, SetupCancelled, isolated_environment
from jevseek.desktop import DesktopAPI


class BonsaiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manager = BonsaiManager(self.root)
        self.manager.root.mkdir()
        self.data = b'actual-model-fixture'
        self.sha = hashlib.sha256(self.data).hexdigest()
        self.path = self.manager.root / 'model.gguf'

    def tearDown(self):
        self.manager.close(); self.tmp.cleanup()

    def client(self, handler):
        return patch('jevseek.bonsai.httpx.Client', return_value=httpx.Client(transport=httpx.MockTransport(handler)))

    def download(self):
        return self.manager._download('https://example.test/model', self.path, len(self.data), self.sha)

    def test_download_integrity_and_reuse(self):
        with self.client(lambda r: httpx.Response(200, content=self.data)):
            self.assertEqual(self.download().read_bytes(), self.data)
        with patch('jevseek.bonsai.httpx.Client', side_effect=AssertionError('no network for verified file')):
            self.download()

    def test_resume_range(self):
        self.path.with_suffix('.gguf.part').write_bytes(self.data[:5])
        def respond(request):
            self.assertEqual(request.headers['range'], 'bytes=5-')
            return httpx.Response(206, headers={'content-range': f'bytes 5-{len(self.data)-1}/{len(self.data)}'}, content=self.data[5:])
        with self.client(respond): self.download()
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_server_ignores_range_restarts_not_appends(self):
        self.path.with_suffix('.gguf.part').write_bytes(self.data[:5])
        with self.client(lambda r: httpx.Response(200, content=self.data)): self.download()
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_wrong_range_rejected(self):
        self.path.with_suffix('.gguf.part').write_bytes(self.data[:5])
        with self.client(lambda r: httpx.Response(206, headers={'content-range': 'bytes 0-18/19'}, content=self.data)), self.assertRaisesRegex(ValueError, 'byte range'):
            self.download()
        self.assertFalse(self.path.exists())

    def test_hash_mismatch_never_promoted(self):
        with self.client(lambda r: httpx.Response(200, content=b'x' * len(self.data))), self.assertRaisesRegex(ValueError, 'Integrity'):
            self.download()
        self.assertFalse(self.path.exists())
        self.assertFalse(self.path.with_suffix('.gguf.part').exists())

    def test_cancel_preserves_partial(self):
        part = self.path.with_suffix('.gguf.part'); part.write_bytes(self.data[:5])
        self.manager.cancel()
        with self.assertRaises(SetupCancelled): self.download()
        self.assertEqual(part.read_bytes(), self.data[:5])

    def test_complete_partial_verified_without_network(self):
        self.path.with_suffix('.gguf.part').write_bytes(self.data)
        with patch('jevseek.bonsai.httpx.Client', side_effect=AssertionError('no network')): self.download()
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_disk_space_preflight(self):
        with patch('jevseek.bonsai.shutil.disk_usage') as usage:
            usage.return_value.free=0
            with self.assertRaisesRegex(ValueError, 'disk space'): self.download()

    def test_zip_traversal_rejected(self):
        archive=self.root/'bad.zip'
        with zipfile.ZipFile(archive,'w') as z: z.writestr('../escape.exe', b'bad')
        with self.assertRaisesRegex(ValueError, 'Unsafe'): self.manager._extract(archive,self.root/'runtime')
        self.assertFalse((self.root/'escape.exe').exists())

    def test_failed_setup_keeps_cloud_selection(self):
        with patch.object(self.manager,'_download',side_effect=ValueError('offline')):
            self.manager._setup('prism')
        self.assertEqual(self.manager.status()['phase'],'error')
        self.assertEqual(self.manager.selection()['provider'],'deepseek')
        self.assertFalse(self.manager.status()['busy'])

    def test_cancelled_setup_keeps_previous_selection(self):
        self.manager._save({'provider':'crack'})
        self.manager.cancel(); self.manager._setup('prism')
        self.assertEqual(self.manager.status()['phase'],'cancelled')
        self.assertEqual(self.manager.selection()['provider'],'crack')

    def test_no_cloud_credentials_in_subprocess(self):
        with patch.dict('os.environ',{'DS_KEY':'test','JEV_KET':'test','TYPESAFE_API_KEY':'test','LLAMA_ARG_MODEL':'bad','HF_TOKEN':'test','NORMAL_SETTING':'ok'}):
            env=isolated_environment()
            for name in ('DS_KEY','JEV_KET','TYPESAFE_API_KEY','LLAMA_ARG_MODEL','HF_TOKEN'): self.assertNotIn(name,env)
            self.assertEqual(env['NORMAL_SETTING'],'ok')

    def test_cpu_uses_validated_common_runtime_not_crashing_optimized_archive(self):
        runtime=self.manager.root/'runtime-cuda';runtime.mkdir()
        (runtime/'.verified').write_text('prism-b10685-7dffb15')
        (runtime/'llama-server.exe').write_bytes(b'fixture')
        self.assertEqual(self.manager._runtime('cpu'),runtime)

    def test_hardware_respects_free_vram_and_driver(self):
        with patch('jevseek.bonsai.subprocess.run') as run:
            run.return_value.stdout='9800, 610.88'
            self.assertEqual(self.manager._hardware(),'cuda')
            run.return_value.stdout='8000, 610.88'
            self.assertEqual(self.manager._hardware(),'cpu')
            run.return_value.stdout='24000, 560.0'
            self.assertEqual(self.manager._hardware(),'cpu')

    def test_invalid_model_rejected(self):
        with self.assertRaises(ValueError): self.manager.setup('../other')

    def test_switch_rejected_during_setup(self):
        self.manager._update(busy=True)
        with self.assertRaises(ValueError): self.manager.use_deepseek()

    def test_desktop_switch_rejected_during_run(self):
        api=DesktopAPI(self.root)
        api._active={'session_id':'test'}
        self.assertFalse(api.setup_local_model('prism')['ok'])
        self.assertFalse(api.use_deepseek()['ok'])

    def test_local_requires_jev_not_deepseek(self):
        api=DesktopAPI(self.root)
        api._bonsai._save({'provider':'crack'})
        with patch.object(api,'_provider_keys',return_value={'jev':'', 'deepseek':''}):
            result=api.start_run(None,'Hello')
            self.assertFalse(result['ok']); self.assertIn('Jev key',result['error'])
        with patch.object(api,'_provider_keys',return_value={'jev':'test', 'deepseek':''}), patch('jevseek.desktop.threading.Thread'):
            self.assertTrue(api.start_run(None,'Hello')['ok'])


if __name__ == '__main__': unittest.main()
