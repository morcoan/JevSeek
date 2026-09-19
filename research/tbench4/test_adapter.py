"""Offline adapter guards; no provider calls, downloads or real shell execution."""
import asyncio
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from research.tbench4.agent import ContainerTools, ContainerWorkspace, JevSeekBonsaiAgent, Transport, configure_credentials, local_endpoint


class LocalOnlyTests(unittest.TestCase):
    def test_cloud_and_ambiguous_endpoints_rejected(self):
        for url in ['https://api.deepseek.com/v1','http://example.com:80/v1','http://127.0.0.1:80/v1?url=cloud','http://user:pass@127.0.0.1:80/v1','http://127.0.0.1/v1','http://127.0.0.1:80/elsewhere']:
            with self.subTest(url=url),self.assertRaises(ValueError):local_endpoint(url)
        self.assertEqual(local_endpoint('http://127.0.0.1:18080/v1/'),'http://127.0.0.1:18080/v1')

    def test_model_constructor_forces_local_even_with_ambient_deepseek(self):
        from jevseek.models import Models,Settings
        with patch.dict(os.environ,{'DS_KEY':'test-forbidden-cloud','LLM_BASE_URL':'https://api.deepseek.com/v1'}),patch('jevseek.models.OpenAI') as openai,patch('jevseek.models.TypeSafeClient') as jev:
            model=Models(SimpleNamespace(),Settings(model='bonsai'),credentials={'jev':'test-jev','deepseek':''},local={'base_url':'http://127.0.0.1:18080/v1','api_key':'local'})
            self.assertEqual(openai.call_args.kwargs['base_url'],'http://127.0.0.1:18080/v1')
            self.assertEqual(openai.call_args.kwargs['api_key'],'local')
            self.assertFalse(openai.call_args.kwargs['http_client'].follow_redirects)
            openai.call_args.kwargs['http_client'].close()
            self.assertEqual(jev.call_args.kwargs['api_key'],'test-jev')
            model.close()

    def test_no_alternate_model_option(self):
        configure_credentials('test-jev')
        with tempfile.TemporaryDirectory() as tmp,self.assertRaises(ValueError):JevSeekBonsaiAgent(logs_dir=Path(tmp),model_name='deepseek-flash')

    def test_schema_rejects_unknown_fields_before_effects(self):
        transport=SimpleNamespace(call=lambda *a: self.fail('must not execute'),environment=None)
        tools=ContainerTools(transport,'/app')
        for args in [{'command':'true','provider':'deepseek'},{'command':''},{'command':'true','timeout':99999}]:
            with self.assertRaises(Exception):tools.execute('bash',args)

    def test_workspace_is_container_not_controller(self):
        workspace=ContainerWorkspace('/app',['file.txt'])
        self.assertEqual(str(workspace),'/app')
        self.assertEqual([p.name for p in workspace.iterdir()],['file.txt'])


class LoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_unchanged_agent_calls_only_container_and_uploads_observations(self):
        from harbor.models.agent.context import AgentContext
        from jevseek.models import Settings
        calls=[];uploads=[]
        class Environment:
            async def exec(self,command,**kwargs):
                calls.append((command,kwargs))
                if command.startswith('printf'):return SimpleNamespace(stdout='/app\0fixture.txt\0',stderr='',return_code=0)
                return SimpleNamespace(stdout='observed',stderr='',return_code=0)
            async def upload_file(self,source_path,target_path):
                uploads.append((Path(source_path).read_bytes(),target_path))
        class FakeModels:
            def __init__(self,session,settings,credentials,local):
                self.settings=settings;self.routes=iter(['bash','done']);self.session=session
                assert credentials['deepseek']=='' and local['base_url'].startswith('http://127.0.0.1:')
            def route_overhead(self,*a):return 1024
            def argument_overhead(self,*a):return 1024
            def route(self,*a):return next(self.routes),1
            def arguments(self,*a):return {'command':'printf observed','timeout':5}
            def summary(self,*a):return 'Observed from the container.'
            def close(self):pass
        configure_credentials('fake-jev-test')
        with tempfile.TemporaryDirectory() as tmp,patch('research.tbench4.agent.Models',FakeModels):
            agent=JevSeekBonsaiAgent(logs_dir=Path(tmp),model_name='bonsai');env=Environment();ctx=AgentContext()
            await agent.setup(env);await agent.run('Read the fixture.',env,ctx)
            self.assertEqual(ctx.metadata['agent_status'],'completed')
            self.assertTrue(ctx.metadata['deepseek_forbidden'])
            self.assertTrue(uploads)
            self.assertTrue(all(dest.startswith('/tmp/jevseek-observations-') for _,dest in uploads))
            self.assertEqual(calls[-1],('printf observed',{'cwd':'/app','timeout_sec':5}))
            result=json.loads((Path(tmp)/'jevseek-result.json').read_text())
            self.assertEqual(result['status'],'completed')
            events=[json.loads(l) for p in Path(tmp).rglob('events.jsonl') for l in p.read_text().splitlines()]
            start=next(e for e in events if e['kind']=='run_started')
            self.assertEqual(start['data']['workspace_entries']['entries'],['fixture.txt'])
            end=next(e for e in events if e['kind']=='tool_finished')
            self.assertTrue(end['data']['full_output'].startswith('/tmp/jevseek-observations-'))


if __name__=='__main__':unittest.main()
