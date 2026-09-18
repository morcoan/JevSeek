import json
import unittest
from unittest.mock import Mock
from compare_deliberation import (Run, request_options, route_state, DraftProgress,
                                 DeliberationStalled, DeliberationNeedsEvidence)

class DeliberationTests(unittest.TestCase):
    def test_native_max(self):
        p=request_options('native','arguments')
        self.assertEqual(p['model'],'deepseek-flash')
        self.assertEqual(p['reasoning_effort'],'max')
        self.assertEqual(p['extra_body']['thinking']['type'],'enabled')
    def test_non_native_disabled(self):
        for mode in ('plain','synthetic','synthetic_v2'):
            for stage in ('draft','arguments','summary'):
                p=request_options(mode,stage)
                self.assertEqual(p['reasoning_effort'],'none')
                self.assertEqual(p['extra_body']['thinking']['type'],'disabled')
    def test_same_model_and_ceiling(self):
        params=[request_options(m,'arguments') for m in ('native','synthetic','plain')]
        self.assertEqual(len({p['model'] for p in params}),1)
        self.assertEqual(len({p['max_tokens'] for p in params}),1)
    def test_router_factual_state_only(self):
        h=[{'tool':'read','arguments':{'path':'engine.py'},'observation':'source'}]
        state=route_state('task',h)
        self.assertEqual(set(state),{'user_intent','completed_turns'})
        self.assertEqual(state['completed_turns'],h)
    def test_gate_controls_repetition_and_drafts_not_persisted(self):
        r=Run.__new__(Run)
        r.mode='synthetic';r.task='task';r.history=[]
        r.messages=[{'role':'system','content':'arguments'},{'role':'user','content':'task'}]
        r.choose=Mock(side_effect=['continue','continue','enough'])
        r.event=Mock()
        r.completion=Mock(side_effect=['draft one','draft two','draft three','{"path":"engine.py"}'])
        text=r.arguments('read')
        self.assertEqual(json.loads(text),{'path':'engine.py'})
        self.assertEqual(r.choose.call_count,3)
        self.assertEqual([a.args[0] for a in r.completion.call_args_list],['draft','draft','draft','arguments'])
        final_input=r.completion.call_args_list[-1].args[1]
        self.assertIn('draft three',json.dumps(final_input))
        self.assertNotIn('draft three',json.dumps(r.messages))
        self.assertEqual(r.history,[])
    def test_plain_no_gate(self):
        r=Run.__new__(Run);r.mode='plain';r.messages=[]
        r.choose=Mock();r.completion=Mock(return_value='{"path":"engine.py"}')
        r.arguments('read')
        r.choose.assert_not_called()
        self.assertEqual(r.completion.call_count,1)

class V2Tests(unittest.TestCase):
    def fake_run(self, drafts, gates):
        r=Run.__new__(Run); r.mode='synthetic_v2'; r.task='task'; r.history=[]; r.messages=[]
        r.event=Mock(); r.completion=Mock(side_effect=drafts); r.choose=Mock(side_effect=gates)
        return r
    def test_cycle(self):
        p=DraftProgress(); p.observe('A draft'); p.observe('Another draft')
        with self.assertRaises(DeliberationStalled): p.observe(' A\n draft ')
    def test_duplicate_aborts_not_enough(self):
        r=self.fake_run(['unchanged','unchanged'],['design_gap'])
        with self.assertRaises(DeliberationStalled): r.arguments('edit')
        self.assertEqual(r.choose.call_count,1)
        self.assertEqual([a.args[0] for a in r.completion.call_args_list],['draft','draft'])
        self.assertEqual(r.history,[])
    def test_missing_evidence_aborts(self):
        r=self.fake_run(['need source'],['needs_evidence'])
        with self.assertRaises(DeliberationNeedsEvidence): r.arguments('edit')
        self.assertEqual(r.completion.call_count,1)
    def test_latest_only_and_actionable_feedback(self):
        r=self.fake_run(['old draft','revised draft','{"path":"engine.py"}'],['schema_gap','enough'])
        r.arguments('read')
        state=r.choose.call_args_list[-1].args[1]
        self.assertEqual(state['latest_draft'],'revised draft')
        self.assertNotIn('working_drafts',state)
        final=r.completion.call_args_list[-1].args[1]
        self.assertNotIn('old draft',json.dumps(final))
        self.assertIn('revised draft',json.dumps(final))
        self.assertNotIn('revised draft',json.dumps(r.messages))

if __name__=='__main__':unittest.main()
