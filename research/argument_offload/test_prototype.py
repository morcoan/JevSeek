"""Scoped, offline offload contracts; no model/tool/network calls."""
import json,threading,unittest
from copy import deepcopy
from types import SimpleNamespace as NS
from unittest.mock import Mock
from research.argument_offload.compiler import prepare,assemble,unique_arguments,read_candidates,safe_schema,FALLBACK
from research.argument_offload.models_snapshot import Models,Settings


def obj(props,required=None):return {'type':'object','properties':props,'required':list(props) if required is None else required,'additionalProperties':False}
READ=obj({'path':{'type':'string'},'view_range':{'anyOf':[{'type':'array','items':{'type':'integer'}},{'type':'null'}],'default':None}},['path'])
SCHEMA=obj({'region':{'enum':['eu','us']},'preview':{'type':'boolean','default':False}},['region'])
STATE={'user_intent':'Read `src/a.py` lines 12 through 18, not `old.py`.','workspace_entries_at_run_start':{'entries':['src','old.py']},'working_files':[]}


def choices_for(plan,arguments):
    answers={}
    for q,b in plan.bindings.items():
        if b['field'] not in arguments:answers[q]='OMIT';continue
        wanted=json.dumps(arguments[b['field']],sort_keys=True)
        answers[q]=next(k for k,v in b['values'].items() if json.dumps(v,sort_keys=True)==wanted)
    return answers


def model(mode='bounded'):
    m=Models.__new__(Models);m.settings=Settings(argument_offload=mode);m.session=Mock();m.cancel=None;m.local=None;m.provider='deepseek';m.jev=Mock();m.generate=Mock(return_value={'fallback':True})
    return m


def respond(m,arguments,confidence=1):
    def call(state,questions,**kw):
        p=prepare(state['context'],state['selected_tool'],state['schema'],state['caller_instructions'])
        answers=choices_for(p,arguments)
        return NS(answers={q:NS(choice=v,confidence=confidence) for q,v in answers.items()},raw_http_response=NS(json=lambda:{'model':'fake','usage':{'input_tokens':20,'output_tokens':30}}))
    m.jev.system_one.side_effect=call


class SchemaTests(unittest.TestCase):
    def test_closed_empty(self):self.assertEqual(unique_arguments(obj({})),{})
    def test_unconstrained_not_unique(self):self.assertIsNone(unique_arguments({'type':'object'}))
    def test_open_empty_not_unique(self):self.assertIsNone(unique_arguments({'type':'object','properties':{}}))
    def test_nested_const(self):self.assertEqual(unique_arguments(obj({'x':obj({'y':{'const':7}})})),{'x':{'y':7}})
    def test_false_is_not_zero(self):self.assertIsNone(unique_arguments(obj({'v':{'enum':[False,0]}})))
    def test_single_enum(self):self.assertEqual(unique_arguments(obj({'v':{'enum':['same','same']}})),{'v':'same'})
    def test_optional_not_implicitly_absent(self):self.assertIsNone(unique_arguments(obj({'x':{'const':1}},[])))
    def test_default_not_value(self):self.assertIsNone(unique_arguments(obj({'x':{'type':'integer','default':7}})))
    def test_invalid_const(self):self.assertIsNone(unique_arguments(obj({'x':{'type':'string','const':5}})))
    def test_no_refs(self):self.assertFalse(safe_schema({'$ref':'https://example.invalid/schema'}))
    def test_no_extra_dialects(self):self.assertFalse(safe_schema({'type':'object','oneOf':[{}]}))
    def test_free_optional_field_falls_back(self):
        s=deepcopy(SCHEMA);s['properties']['limit']={'type':'integer','default':3}
        self.assertIsNone(prepare({'user_intent':'top17 in eu'},'mcp.query',s))
    def test_free_generation_not_offloaded(self):
        for n in ['write','edit','bash','recall']:self.assertIsNone(prepare({},n,SCHEMA))
    def test_open_mcp_not_compiled(self):
        s=deepcopy(SCHEMA);s.pop('additionalProperties');self.assertIsNone(prepare({},'mcp.query',s))
    def test_empty_required_path_candidates_falls_back(self):self.assertIsNone(prepare({},'read',READ))
    def test_oversize_never_truncated(self):self.assertIsNone(prepare({'user_intent':'a'*30000},'mcp.query',SCHEMA))
    def test_bounded_read(self):
        p=prepare(STATE,'read',READ);a={'path':'src/a.py','view_range':[12,18]};self.assertEqual(assemble(p,choices_for(p,a),STATE,'read',READ),a)
    def test_pure_inputs(self):
        state=deepcopy(STATE);s=deepcopy(READ);p=prepare(state,'read',s);self.assertEqual(state,STATE);self.assertEqual(s,READ)
        p.state['context']['user_intent']='changed';self.assertEqual(state,STATE)
    def test_changed_context_rejected(self):
        p=prepare(STATE,'read',READ);changed={**STATE,'user_intent':'Other file'}
        with self.assertRaises(ValueError):assemble(p,{},changed,'read',READ)
    def test_mutated_plan_rejected(self):
        p=prepare(STATE,'read',READ);p.bindings['p0']['values']['v0']='wrong'
        with self.assertRaises(ValueError):assemble(p,{},STATE,'read',READ)
    def test_partial_answers_rejected(self):
        p=prepare(STATE,'read',READ)
        with self.assertRaises(ValueError):assemble(p,{},STATE,'read',READ)
    def test_unknown_value_never_guessed(self):
        p=prepare(STATE,'read',READ)
        with self.assertRaises(ValueError):assemble(p,{q:FALLBACK for q in p.questions},STATE,'read',READ)
    def test_required_never_omitted(self):
        p=prepare(STATE,'read',READ)
        with self.assertRaises(ValueError):assemble(p,{q:'OMIT' for q in p.questions},STATE,'read',READ)
    def test_extra_answers_rejected(self):
        p=prepare(STATE,'read',READ);a=choices_for(p,{'path':'src/a.py'});a['junk']='v0'
        with self.assertRaises(ValueError):assemble(p,a,STATE,'read',READ)
    def test_verbatim_paths_and_ranges(self):
        c=read_candidates({'user_intent':'Read "folder/naïve file.txt" [4, -1] and not `.env`.'})
        self.assertIn('folder/naïve file.txt',c['path']);self.assertNotIn('.env',c['path']);self.assertIn([4,-1],c['view_range'])
    def test_settings(self):
        for s in ['oops','']:
            with self.assertRaises(ValueError):Settings(argument_offload=s)
        with self.assertRaises(ValueError):Settings(argument_min_confidence=float('nan'))


class IntegrationTests(unittest.TestCase):
    def test_unique_no_model(self):
        m=model();self.assertEqual(m.arguments({},'mcp.ping',obj({}),''),{});m.jev.system_one.assert_not_called();m.generate.assert_not_called()
    def test_off_uses_original(self):
        m=model('off');m.arguments({},'mcp.ping',obj({}),'');m.generate.assert_called_once();m.jev.system_one.assert_not_called()
    def test_deterministic_no_semantic_extra_call(self):
        m=model('deterministic');m.arguments({},'mcp.query',SCHEMA,'');m.jev.system_one.assert_not_called();m.generate.assert_called_once()
    def test_bounded_replaces_flash(self):
        m=model();respond(m,{'region':'eu','preview':False});self.assertEqual(m.arguments({},'mcp.query',SCHEMA,''),{'region':'eu','preview':False});m.generate.assert_not_called()
        self.assertEqual(m.jev.system_one.call_args.kwargs['retry'].max_retries,0)
    def test_optional_omitted(self):
        m=model();respond(m,{'region':'eu'});self.assertEqual(m.arguments({},'mcp.query',SCHEMA,''),{'region':'eu'})
    def test_read_replace(self):
        m=model();respond(m,{'path':'src/a.py','view_range':[12,18]});a=m.arguments(STATE,'read',READ,'');self.assertEqual(a['view_range'],[12,18]);m.generate.assert_not_called()
    def test_low_confidence_falls_back(self):
        m=model();respond(m,{'region':'eu'},.5);self.assertEqual(m.arguments({},'mcp.query',SCHEMA,''),{'fallback':True});m.generate.assert_called_once()
        usage=[c for c in m.session.append.call_args_list if c.args==('usage',)];self.assertEqual(len(usage),1)
    def test_provider_error_falls_back_once(self):
        m=model();m.jev.system_one.side_effect=RuntimeError('private');m.arguments({},'mcp.query',SCHEMA,'');m.generate.assert_called_once();self.assertNotIn('private',str(m.session.append.call_args_list))
    def test_no_jev_tax_unsupported(self):
        m=model();m.arguments({},'edit',READ,'');m.jev.system_one.assert_not_called();m.generate.assert_called_once()
    def test_cancel_no_fallback(self):
        m=model();m.cancel=threading.Event();m.cancel.set()
        with self.assertRaises(KeyboardInterrupt):m.arguments({},'mcp.query',SCHEMA,'')
        m.generate.assert_not_called();m.jev.system_one.assert_not_called()
    def test_cancel_after_jev_no_fallback(self):
        m=model();m.cancel=threading.Event();respond(m,{'region':'eu'});original=m.jev.system_one.side_effect
        def call(**kw):r=original(**kw);m.cancel.set();return r
        m.jev.system_one.side_effect=call
        with self.assertRaises(KeyboardInterrupt):m.arguments({},'mcp.query',SCHEMA,'')
        m.generate.assert_not_called()
    def test_local_model_does_not_add_jev_bill(self):
        m=model();m.local={'local':True};m.arguments({},'mcp.query',SCHEMA,'');m.jev.system_one.assert_not_called();m.generate.assert_called_once()
    def test_fallback_messages_not_polluted(self):
        m=model();respond(m,{'region':'eu'},.1);m.arguments({'user_intent':'original'},'mcp.query',SCHEMA,'retain this')
        messages=m.generate.call_args.args[1];self.assertEqual(json.loads(messages[1]['content']),{'user_intent':'original'});self.assertNotIn('argument_options',str(messages))

if __name__=='__main__':unittest.main()
