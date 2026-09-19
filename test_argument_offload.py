"""Production schema-determined argument bypass: offline, no inference."""
import itertools
import json
import os
import threading
import unittest
from unittest.mock import Mock, patch
from jsonschema import Draft202012Validator
from jevseek.argument_offload import unique_arguments
from jevseek.models import Models, Settings


def obj(props, required=None):
    return {'type':'object', 'properties':props,
            'required':list(props) if required is None else required,
            'additionalProperties':False}


def model(mode='deterministic'):
    m=Models.__new__(Models)
    m.settings=Settings(argument_offload=mode)
    m.session=Mock(); m.cancel=None; m.local=None; m.provider='deepseek'
    m.jev=Mock(); m.generate=Mock(return_value={'original_generator':True})
    return m


class SchemaTests(unittest.TestCase):
    def test_empty_closed(self):self.assertEqual(unique_arguments(obj({})),{})
    def test_open_object(self):self.assertIsNone(unique_arguments({'type':'object','properties':{}}))
    def test_unknown_schema(self):self.assertIsNone(unique_arguments({}))
    def test_single_const(self):self.assertEqual(unique_arguments(obj({'v':{'const':'one'}})),{'v':'one'})
    def test_single_enum(self):self.assertEqual(unique_arguments(obj({'v':{'enum':['same','same']}})),{'v':'same'})
    def test_multiple_enum(self):self.assertIsNone(unique_arguments(obj({'v':{'enum':['a','b']}})))
    def test_false_not_zero(self):self.assertIsNone(unique_arguments(obj({'v':{'enum':[False,0]}})))
    def test_null(self):self.assertEqual(unique_arguments(obj({'v':{'type':'null'}})),{'v':None})
    def test_nested(self):self.assertEqual(unique_arguments(obj({'v':obj({'n':{'const':3}})})),{'v':{'n':3}})
    def test_optional_not_dropped(self):self.assertIsNone(unique_arguments(obj({'v':{'const':'one'}},[])))
    def test_default_not_inferred(self):self.assertIsNone(unique_arguments(obj({'limit':{'type':'integer','default':3}})))
    def test_invalid_const(self):self.assertIsNone(unique_arguments(obj({'v':{'type':'string','const':5}})))
    def test_no_reference_fetch(self):self.assertIsNone(unique_arguments({'$ref':'https://example.invalid/schema'}))
    def test_unknown_composition(self):self.assertIsNone(unique_arguments({'type':'object','oneOf':[obj({})]}))
    def test_input_copy_isolation(self):
        s=obj({'v':{'const':{'list':['original']}}});r=unique_arguments(s)
        r['v']['list'].append('changed');self.assertEqual(s['properties']['v']['const']['list'],['original'])
    def test_oversized_schema(self):self.assertIsNone(unique_arguments(obj({'v':{'const':'x'*17000}})))
    def test_invalid_schema(self):self.assertIsNone(unique_arguments({'type':'not_a_json_type'}))
    def test_cyclic_schema(self):
        s={};s['properties']=s;self.assertIsNone(unique_arguments(s))
    def test_exhaustive_small_schema_subset(self):
        subs=[{'const':'a'},{'enum':['a','b']},{'type':'boolean'},{'type':'null'},{'type':'integer','default':0}]
        missing=object();values=[missing,'a','b',True,False,None,0,1]
        objects=[]
        for x,y in itertools.product(values,repeat=2):
            objects.append({k:v for k,v in [('x',x),('y',y)] if v is not missing})
        accepted=0
        for x,y in itertools.product(subs,repeat=2):
            for required in [[],['x'],['y'],['x','y']]:
                s=obj({'x':x,'y':y},required);answer=unique_arguments(s)
                if answer is None:continue
                valid=[v for v in objects if Draft202012Validator(s).is_valid(v)]
                canonical={json.dumps(v,sort_keys=True) for v in valid}
                self.assertEqual(canonical,{json.dumps(answer,sort_keys=True)})
                accepted+=1
        self.assertEqual(accepted,4)


class IntegrationTests(unittest.TestCase):
    def test_baseline_one_call_bypass_zero_same_arguments(self):
        baseline=model('off');baseline.generate.return_value={}
        new=model();args=({},'mcp.no_arguments',obj({}),'')
        self.assertEqual(baseline.arguments(*args),new.arguments(*args))
        baseline.generate.assert_called_once();new.generate.assert_not_called();new.jev.system_one.assert_not_called()
    def test_fixed_values_skip_model(self):
        m=model();self.assertEqual(m.arguments({},'mcp.bound',obj({'v':{'const':'known'}}),''),{'v':'known'})
        m.generate.assert_not_called();m.jev.system_one.assert_not_called()
        event=m.session.append.call_args;self.assertEqual(event.args,('argument_offload',));self.assertTrue(event.kwargs['flash_call_skipped'])
    def test_free_fields_original_input_unchanged(self):
        m=model();s=obj({'path':{'type':'string'}});state={'user_intent':'Read requested.txt'}
        self.assertEqual(m.arguments(state,'read',s,'keep instructions'),{'original_generator':True})
        m.generate.assert_called_once();m.jev.system_one.assert_not_called()
        args=m.generate.call_args.args;self.assertEqual(args[0],'arguments')
        self.assertEqual(json.loads(args[1][1]['content']),state)
        self.assertIn('keep instructions',args[1][0]['content'])
        self.assertEqual(m.generate.call_args.kwargs['schema'],s)
    def test_unsupported_optional_field_original_path(self):
        m=model();s=obj({'format':{'const':'json'},'limit':{'type':'integer','default':3}},['format'])
        m.arguments({'user_intent':'give me 17'},'mcp.list',s,'');m.generate.assert_called_once();m.jev.system_one.assert_not_called()
    def test_local_generation_also_skips_unique_without_paid_jev(self):
        m=model();m.local={'local':True};m.provider='bonsai'
        self.assertEqual(m.arguments({},'mcp.zero',obj({}),''),{});m.generate.assert_not_called();m.jev.system_one.assert_not_called()
    def test_cancel_before_bypass(self):
        m=model();m.cancel=threading.Event();m.cancel.set()
        with self.assertRaises(KeyboardInterrupt):m.arguments({},'mcp.zero',obj({}),'')
        m.generate.assert_not_called()
    def test_unvalidated_semantic_mode_not_enabled(self):
        with self.assertRaises(ValueError):Settings(argument_offload='bounded')
    def test_environment_switch(self):
        with patch.dict(os.environ,{'LLM_MODEL':'deepseek-flash','JEV_ARGUMENT_OFFLOAD':'off'}):self.assertEqual(Settings.environment().argument_offload,'off')
    def test_real_agent_preserves_persist_before_effect_and_no_replay(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from jevseek.session import Session
        from jevseek.agent import Agent
        with TemporaryDirectory() as directory:
            root=Path(directory);workspace=root/'work';workspace.mkdir()
            session=Session.create(root/'sessions',workspace)
            m=model();m.session=session;m.route_overhead=Mock(return_value=100)
            m.route=Mock(side_effect=[('mcp.ping',1),('done',1)])
            m.summary=Mock(return_value='Completed recorded ping.')
            tools=Mock();tools.schemas={'mcp.ping':obj({})};tools.catalog.return_value={'mcp.ping':'Read-only ping.'}
            def execute(name,args):
                self.assertEqual(name,'mcp.ping');self.assertEqual(args,{})
                self.assertEqual(len(session.pending()),1)
                return {'text':'pong','is_error':False,'exit_code':0}
            tools.execute.side_effect=execute
            agent=Agent(session,m,tools)
            self.assertEqual(agent.run('Ping once')['status'],'completed')
            self.assertEqual(session.pending(),[])
            self.assertEqual(agent.run()['status'],'completed')
            tools.execute.assert_called_once();m.generate.assert_not_called();m.jev.system_one.assert_not_called()

if __name__=='__main__':unittest.main()
