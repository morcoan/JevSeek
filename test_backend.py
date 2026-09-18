"""Offline backend contracts; no network/model credentials required."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
from filelock import Timeout

os.environ['OPENHANDS_SUPPRESS_BANNER']='1'
from jevseek.agent import Agent
from jevseek.context import Context,ContextPolicy,ContextOverflow,encoded,size
from jevseek.models import Settings,deepseek_options,Models
from jevseek.session import Session,SessionError,Redactor
from jevseek.tools import Tools

# Synthetic redaction fixture, assembled to avoid looking like a committed API key.
FAKE_SECRET = 'sk-' + 'example-secret-123456'

class Base(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.workspace=self.root/'work'; self.workspace.mkdir()
        self.s=Session.create(self.root/'sessions',self.workspace,redactor=Redactor([FAKE_SECRET]))
    def effect(self,n,text='result',status='ok',target='a.txt'):
        artifact,output=self.s.artifact(str(n),{'path':target},{'text':text})
        return self.s.append('tool_finished',call_id=str(n),tool='read',status=status,target=target,
                             exit_code=None,text=text,arguments={'path':target},artifact=artifact,full_output=output)

class SessionTests(Base):
    def test_resume(self):
        self.s.append('user',text='keep me')
        other=Session.open(self.root/'sessions',self.s.id)
        with other.lock: other.reload()
        self.assertEqual(other.events[-1]['data']['text'],'keep me')
        self.assertEqual(other.workspace,self.workspace.resolve())
    def test_torn_tail(self):
        with self.s.path.open('ab') as f: f.write(b'{"incomplete":')
        with self.s.lock: self.s.reload(); self.s.append('user',text='safe')
        self.s.reload();self.assertEqual(self.s.events[-1]['data']['text'],'safe')
        self.assertEqual(len(list(self.s.directory.glob('incomplete-*'))),1)
    def test_internal_corruption_is_not_silent(self):
        with self.s.path.open('ab') as f: f.write(b'{bad}\n')
        with self.assertRaises(SessionError):self.s.reload()
    def test_unknown_version(self):
        raw=self.s.path.read_text().replace('"version": 1','"version": 2')
        self.s.path.write_text(raw)
        with self.assertRaises(SessionError):self.s.reload()
    def test_pending_no_replay(self):
        self.s.append('tool_started',call_id='x',tool='bash')
        self.assertEqual(len(self.s.pending()),1)
        self.s.acknowledge_pending();self.assertEqual(self.s.pending(),[])
        self.assertEqual(self.s.events[-1]['kind'],'tool_uncertain')
    def test_unfinished_shell_wait_requires_ack_on_resume(self):
        self.s.append('tool_started',call_id='shell',tool='bash')
        self.s.append('tool_finished',call_id='shell',tool='bash',status='running',exit_code=-1)
        self.assertEqual(len(self.s.pending()),1)
        self.s.acknowledge_pending();self.assertEqual(self.s.pending(),[])
    def test_completed_poll_resolves_unfinished_shell(self):
        self.s.append('tool_started',call_id='shell',tool='bash')
        self.s.append('tool_finished',call_id='shell',tool='bash',status='running',exit_code=-1)
        self.s.append('tool_started',call_id='poll',tool='bash')
        self.s.append('tool_finished',call_id='poll',tool='bash',status='ok',exit_code=0)
        self.assertEqual(self.s.pending(),[])
    def test_secrets_redacted_in_disk_and_callback(self):
        seen=[];self.s.on_event=seen.append
        self.s.append('user',text=FAKE_SECRET)
        artifact,output=self.s.artifact('a',{}, {'text':FAKE_SECRET})
        self.assertNotIn('sk-example-secret',self.s.path.read_text())
        self.assertEqual(Path(output).read_text(),'[REDACTED]')
        self.assertEqual(seen[-1]['data']['text'],'[REDACTED]')
    def test_bad_subscriber_does_not_interrupt_persistence(self):
        self.s.on_event=Mock(side_effect=RuntimeError())
        self.s.append('user',text='saved');self.s.reload()
        self.assertEqual(self.s.events[-1]['data']['text'],'saved')
    def test_one_writer(self):
        other=Session.open(self.root/'sessions',self.s.id)
        with self.s.lock:
            with self.assertRaises(Timeout):
                with other.lock: pass
    def test_session_path_traversal(self):
        with self.assertRaises(SessionError):Session.open(self.root/'sessions','../../etc')

class ContextTests(Base):
    def test_bounded_and_pinned_with_retrievable_output(self):
        prompt='Preserve this exact constraint: do not change tests.'
        self.s.append('user',text=prompt)
        for i in range(20):self.effect(i,'BEGIN\n'+'x'*20000+'\nEND')
        policy=ContextPolicy(router_bytes=10000,model_bytes=16000,keep_recent=3)
        for audience,budget in [('router',10000),('model',16000)]:
            state=Context(self.s,policy).build(audience)
            self.assertLessEqual(size(state),budget)
            self.assertEqual(state['user_intent'],prompt)
            self.assertEqual(len(state['recent_execution']),3)
            self.assertIn('OMITTED',state['recent_execution'][-1]['text'])
            full=Path(state['recent_execution'][-1]['full_output']).read_text()
            self.assertTrue(full.endswith('END'));self.assertGreater(len(full),20000)
        self.assertTrue(list(self.s.directory.glob('context-*.json')))
    def test_no_generative_summaries_or_plans_in_router(self):
        self.s.append('user',text='read a.txt')
        self.s.append('final',status='completed',summary='POISON_MODEL_SUMMARY')
        self.s.append('route',choice='edit',confidence=1,plan='POISON_PLAN')
        self.s.append('draft',text='POISON_DRAFT')
        self.effect(1,'actual source')
        state=encoded(Context(self.s).build('router'))
        self.assertNotIn('POISON',state);self.assertIn('actual source',state)
    def test_historical_failure_status_retained(self):
        self.s.append('user',text='task')
        e=self.effect(1,'failure','error')
        for i in range(2,20):self.effect(i,'x'*5000)
        state=Context(self.s,ContextPolicy(router_bytes=8000)).build('router')
        self.assertEqual(state['verification']['latest_historical_failure']['seq'],e['seq'])
    def test_large_intent_not_silently_dropped(self):
        self.s.append('user',text='中'*20000)
        with self.assertRaises(ContextOverflow): Context(self.s).build('router')
    def test_checkpoint_resume_same_facts(self):
        self.s.append('user',text='intent')
        for i in range(20):self.effect(i,'x'*5000)
        policy=ContextPolicy(router_bytes=9000)
        before=Context(self.s,policy).build('router')
        self.s.reload();after=Context(self.s,policy).build('router')
        self.assertEqual(before,after)
    def test_followup_scopes_old_failure_out_of_current_verification(self):
        self.s.append('user',text='first task');self.effect(1,'old failure','error')
        self.s.append('user',text='new task');self.effect(2,'current source')
        state=Context(self.s).build('router')
        self.assertIsNone(state['verification']['latest_historical_failure'])
        self.assertEqual(state['user_intent'],'new task')
        self.assertIn('error',encoded(state['historical_activity']))
        self.assertNotIn('old failure',encoded(state['recent_execution']))
    def test_manual_compaction(self):
        self.s.append('user',text='intent'); self.effect(1)
        Context(self.s).build('model',force=True)
        self.assertEqual(self.s.events[-1]['kind'],'compaction')
    def test_working_source_survives_rolling_archive(self):
        self.s.append('user',text='task')
        first=self.effect(1,'PINNED_SOURCE')
        for i in range(2,15):
            self.effect(i,'x'*5000,target='other.txt')
        context=Context(self.s,ContextPolicy(router_bytes=10000,model_bytes=18000))
        state=context.build('model')
        self.assertNotIn(first['seq'],[e['seq'] for e in state['recent_execution']])
        self.assertIn('PINNED_SOURCE',encoded(state['working_files']))
        self.assertLessEqual(size(state),18000)
    def test_working_source_invalidation(self):
        self.s.append('user',text='task');self.effect(1,'source')
        self.assertTrue(Context(self.s).build('model')['working_files'])
        self.s.append('tool_finished',tool='edit',target='a.txt',status='ok')
        self.assertFalse(Context(self.s).build('model')['working_files'])
        self.effect(2,'new source')
        self.s.append('tool_finished',tool='bash',target='command',status='ok',exit_code=0)
        self.assertFalse(Context(self.s).build('model')['working_files'])
    def test_archive_can_be_read_by_native_tool(self):
        e=self.effect(1,'line one\nline two\nline three')
        t=Tools(self.workspace,self.root/'output');self.addCleanup(t.close)
        result=t.execute('read',{'path':e['data']['full_output'],'view_range':[2,2]})
        self.assertIn('line two',result['text']);self.assertNotIn('line three',result['text'])
    def test_policy_bounds(self):
        with self.assertRaises(ValueError):ContextPolicy(router_bytes=10)
        with self.assertRaises(ValueError):ContextPolicy(keep_recent=0)

class FakeModels:
    settings=Settings()
    def __init__(self,choices): self.choices=iter(choices);self.states=[];self.calls=0
    def route_overhead(self,catalog):return 100
    def route(self,state,catalog):self.states.append(state);return next(self.choices)
    def argument_overhead(self,schema,instructions):return 100
    def arguments(self,state,name,schema,instructions):self.calls+=1;return {'path':'file.txt'}
    def summary(self,state,status,instructions):return 'Factual summary: '+status
    def close(self):pass

class FakeTools:
    schemas={'read':{'type':'object'}}
    def __init__(self):self.calls=0
    def catalog(self):return {'read':'read a file'}
    def execute(self,name,args):self.calls+=1;return {'text':'file content','is_error':False,'exit_code':None}
    def close(self):pass

class AgentTests(Base):
    def test_jit_loop_and_resume_does_not_rerun(self):
        m=FakeModels([('read',1),('done',1)]);t=FakeTools()
        a=Agent(self.s,m,t)
        self.assertEqual(a.run('read file')['status'],'completed')
        self.assertEqual(t.calls,1);self.assertEqual(m.calls,1)
        self.assertIn('file content',encoded(m.states[-1]))
        self.assertEqual(a.run()['status'],'completed');self.assertEqual(t.calls,1)
    def test_low_confidence_asks_without_effect(self):
        m=FakeModels([('read',0.1)]);t=FakeTools()
        self.assertEqual(Agent(self.s,m,t).run('ambiguous')['status'],'needs_input')
        self.assertEqual(t.calls,0)
    def test_crashed_inflight_never_replayed(self):
        self.s.append('user',text='task');self.s.append('tool_started',tool='read',call_id='pending')
        t=FakeTools();m=FakeModels([])
        self.assertEqual(Agent(self.s,m,t).run()['status'],'needs_input');self.assertEqual(t.calls,0)
    def test_cancel_before_tool(self):
        cancel=threading.Event();cancel.set()
        t=FakeTools();m=FakeModels([])
        self.assertEqual(Agent(self.s,m,t,cancel=cancel).run('task')['status'],'cancelled');self.assertEqual(t.calls,0)
    def test_interrupted_tool_preserves_uncertainty(self):
        t=FakeTools();t.execute=Mock(side_effect=KeyboardInterrupt())
        m=FakeModels([('read',1)])
        self.assertEqual(Agent(self.s,m,t).run('task')['status'],'cancelled')
        self.assertEqual(len(self.s.pending()),1)
    def test_provider_failure_saved_no_tool(self):
        m=FakeModels([]);m.route=Mock(side_effect=RuntimeError(FAKE_SECRET))
        t=FakeTools();r=Agent(self.s,m,t).run('task')
        self.assertEqual(r['status'],'blocked');self.assertEqual(t.calls,0)
        self.assertNotIn('sk-example-secret',self.s.path.read_text())
    def test_failure_not_completed_on_done(self):
        t=FakeTools();t.execute=Mock(return_value={'text':'failed','is_error':True,'exit_code':1})
        m=FakeModels([('read',1),('done',1)])
        self.assertEqual(Agent(self.s,m,t).run('task')['status'],'needs_input')
    def test_followup_keeps_verbatim_original_intent(self):
        t=FakeTools();m=FakeModels([('done',1),('done',1)])
        a=Agent(self.s,m,t);a.run('Original instruction');a.run('Followup correction')
        texts=[r['text'] for r in m.states[-1]['earlier_user_requests_verbatim']]+[m.states[-1]['user_intent']]
        self.assertEqual(texts,['Original instruction','Followup correction'])

class AdapterTests(Base):
    def test_prebuilt_file_tools_and_validation(self):
        t=Tools(self.workspace,self.root/'outputs')
        self.addCleanup(t.close)
        self.assertFalse(t.execute('write',{'path':'a.txt','file_text':'before'})['is_error'])
        self.assertIn('before',t.execute('read',{'path':'a.txt'})['text'])
        self.assertFalse(t.execute('edit',{'path':'a.txt','old_str':'before','new_str':'after'})['is_error'])
        self.assertEqual((self.workspace/'a.txt').read_text(),'after')
        with self.assertRaises(Exception):t.execute('edit',{'path':'a.txt','file_text':'wrong schema'})
        with self.assertRaises(ValueError):t.execute('write',{'path':'a.txt','file_text':'overwrite'})
    def test_mcp_uses_raw_schema_not_agent_metadata(self):
        tool=Mock();tool.name='custom';tool.description='custom tool'
        tool.mcp_tool.input_schema={'type':'object','properties':{'value':{'type':'string'}}}
        client=Mock();client.tools=[tool]
        with patch('jevseek.tools.create_mcp_tools',return_value=client):
            t=Tools(self.workspace,self.root/'out',{'server':object()})
        self.assertNotIn('summary',t.schemas['mcp.custom']['properties'])
        tool.to_openai_tool.assert_not_called();t.close()
        client.sync_close.assert_called_once()
    def test_defaults_are_nonthinking_for_arguments_and_summary(self):
        for summary in (False,True):
            opts=deepseek_options(Settings(),summary)
            self.assertEqual(opts['model'],'deepseek-flash')
            self.assertEqual(opts['reasoning_effort'],'none')
            self.assertEqual(opts['extra_body']['thinking']['type'],'disabled')
    def test_catalog_limit_is_explicit(self):
        with self.assertRaises(ValueError):Models.choices({str(i):'x' for i in range(251)})

class Stream(list):
    closed=False
    def __enter__(self):return self
    def __exit__(self,*args):self.closed=True

class ProviderTests(Base):
    def model(self,chunks):
        m=Models.__new__(Models);m.session=self.s;m.settings=Settings();m.cancel=None
        stream=Stream(chunks);m.ds=Mock();m.ds.chat.completions.create.return_value=stream
        return m,stream
    def chunk(self,text,finish=None,tool=False,reasoning=None):
        function=SimpleNamespace(name='selected_action',arguments=text)
        delta=SimpleNamespace(content=None if tool else text,
                              tool_calls=[SimpleNamespace(index=0,function=function)] if tool else None,
                              reasoning_content=reasoning)
        return SimpleNamespace(model='deepseek-flash',usage=None,
                               choices=[SimpleNamespace(delta=delta,finish_reason=finish)])
    def test_forced_one_native_function(self):
        m,stream=self.model([self.chunk('{"path":',tool=True),self.chunk('"a.txt"}',finish='tool_calls',tool=True)])
        schema={'type':'object','properties':{'path':{'type':'string'}},'required':['path']}
        self.assertEqual(m.arguments({},'read',schema,''),{'path':'a.txt'})
        kwargs=m.ds.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs['tool_choice']['function']['name'],'selected_action')
        self.assertEqual(len(kwargs['tools']),1);self.assertNotIn('response_format',kwargs)
        self.assertFalse(kwargs['parallel_tool_calls'])
        self.assertEqual(kwargs['reasoning_effort'],'none');self.assertTrue(stream.closed)
    def test_truncated_payload_never_used(self):
        m,stream=self.model([self.chunk('{',finish='length',tool=True)])
        with self.assertRaises(ValueError):m.generate('arguments',[],schema={})
        self.assertTrue(stream.closed)
    def test_unexpected_reasoning_rejected(self):
        m,stream=self.model([self.chunk('{}',finish='stop',reasoning='thinking')])
        with self.assertRaises(ValueError):m.generate('summary',[])
        self.assertTrue(stream.closed)
    def test_progress_never_leaks_split_secret(self):
        seen=[];self.s.on_event=seen.append
        m,_=self.model([self.chunk('{"summary":"sk-example-'),self.chunk('secret-123456"}',finish='stop')])
        m.generate('summary',[])
        self.assertNotIn('sk-example',json.dumps(seen))
    def test_stream_cancellation_closes_response(self):
        m,stream=self.model([self.chunk('{}',finish='stop')])
        m.cancel=threading.Event();m.cancel.set()
        with self.assertRaises(KeyboardInterrupt):m.generate('summary',[])
        self.assertTrue(stream.closed)
    def test_returned_final_redacted(self):
        m=FakeModels([('done',1)]);m.summary=lambda *args:FAKE_SECRET
        result=Agent(self.s,m,FakeTools()).run('task')
        self.assertEqual(result['summary'],'[REDACTED]')

if __name__=='__main__':unittest.main()
