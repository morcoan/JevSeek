from __future__ import annotations
import argparse,hashlib,json,statistics,tempfile
from pathlib import Path
from collections import Counter
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.agentic_screen.tasks import fixtures,fixture_hash
from research.agentic_screen.runner import Environment,SYSTEM
from research.agentic_screen.policies import prepare,ranked,query_for,code_hint
from research.flash_integration.analyze import usage
from research.decoding_control.providers import save


def analyze(path):
 d=json.loads((path/'results.json').read_text(encoding='utf-8'));m=d['manifest'];source=path.parent/m['source_run'];sm=json.loads((source/'manifest.json').read_text(encoding='utf-8'));ts={t['id']:t for t in fixtures()};assert fixture_hash()==m['fixture_sha256']==sm['fixture_sha256']
 assert hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest()==m['source_manifest_sha256']
 for f,h in {**m['source_sha256'],**sm['source_sha256']}.items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h
 assert len(d['results'])==52;assert len({(r['task'],r['arm']) for r in d['results']})==52
 replayed=0;calls_by={};coverage=[];helper_accuracy=[];all_corrected_calls=[];new=0
 with tempfile.TemporaryDirectory(dir=ROOT/'.local') as tmp:
  for r in d['results']:
   t=ts[r['task']];arm=r['arm'];env=Environment(t,Path(tmp)/t['id']/arm)
   for event in r['events']:assert env.act(event['tool'],event['arguments'])==event['result']
   env.finished=r['finished'];assert env.result()==r['evaluation'];assert env.config==r['config'] and env.receipts==r['receipts'];assert json.loads((path/t['id']/arm/'config.json').read_text(encoding='utf-8'))==env.config;replayed+=1
   cs=json.loads((path/t['id']/arm/'calls.json').read_text(encoding='utf-8'));calls_by[t['id'],arm]=cs;all_corrected_calls+=cs;new+=sum(c['stage']=='agent' and not c.get('replayed_transport_only') for c in cs)
   initial=r['initial_visible'];assert 'hidden' not in initial
   for key in ['id','kind','goal','requirements','project','config','revision','receipts','history','probe_catalog']:assert initial[key]==t[key]
   assert all(x in t['records'] and x['scope']==t['project'] and x['revision']=='current' for x in initial['working_evidence'])
   state,qs,pool=prepare(t);assert r['selection']['candidate_ids']==[x['id'] for x in pool]
   for c in cs:
    if c['stage']=='agent':
     assert c['thinking'] and c['messages'][0]['content']==SYSTEM and json.loads(c['messages'][1]['content'])==initial
    elif arm=='self':assert json.loads(c['messages'][1]['content'])=={'state':state,'questions':qs}
    elif arm=='jev':assert c['state']==state and all(qs[k]==v for k,v in c['questions'].items())
   assert r['executed_actions']==len(r['events'])<=4
   if t['kind']=='memory':
    needed=set(t['hidden']['relevant_records']);have={x['id'] for x in initial['working_evidence']};candidate=set(r['selection']['candidate_ids'])
    coverage.append({'task':t['id'],'arm':arm,'initial_reference_records':len(needed&have),'reference_records':len(needed),'candidate_reference_records':len(candidate&needed)})
   if arm in {'self','jev'} and t['kind']=='coverage':
    wanted=['delivery','dedupe','unicode'];a=r['selection'].get('answers',{});correct=sum(t['hidden']['probe_map'].get(a.get('q'+str(i)))==kind for i,kind in enumerate(wanted));helper_accuracy.append({'task':t['id'],'arm':arm,'correct_associations':correct,'total':3})
 by_kind={}
 for kind in ['memory','coverage','loop']:
  rows=[r for r in d['results'] if r['kind']==kind];summary={'cases':4,'arms':{},'jev_comparisons':{}}
  for arm in ['base','code','self','jev']+(['full'] if kind=='memory' else []):
   rs=[r for r in rows if r['arm']==arm];cs=[c for r in rs for c in calls_by[r['task'],arm]]
   summary['arms'][arm]={'success':sum(r['evaluation']['success'] for r in rs),'false_completion':sum(r['evaluation']['false_completion'] for r in rs),
    'median_serial_call_seconds':statistics.median(r['serial_call_seconds'] for r in rs),'tool_actions':sum(r['executed_actions'] for r in rs),
    'errors':sum(len(r['errors']) for r in rs),'usage':{p:usage([c for c in cs if c['provider']==p]) for p in ['deepseek','jev']}}
  j={r['task']:r for r in rows if r['arm']=='jev'}
  for b in ['base','code','self']:
   br={r['task']:r for r in rows if r['arm']==b};wins=sum(j[k]['evaluation']['success'] and not br[k]['evaluation']['success'] for k in j);losses=sum(not j[k]['evaluation']['success'] and br[k]['evaluation']['success'] for k in j)
   summary['jev_comparisons'][b]={'rescues':wins,'regressions':losses}
  comparisons=summary['jev_comparisons'];gate=all(comparisons[b]['rescues']>=2 and comparisons[b]['regressions']==0 for b in ['code','self'])
  gate=gate and summary['arms']['jev']['median_serial_call_seconds']<=2*summary['arms']['code']['median_serial_call_seconds'];summary['followup_gate']=gate;summary['decision']='candidate_only_needs_fresh_validation' if gate else 'STOP_no_unique_task_gain_in_screen';by_kind[kind]=summary
 # Actual requests count originals once, plus new continuations; no double-counting replay.
 original=[]
 for t in ts.values():
  for arm in ['base','code','self','jev']+(['full'] if t['kind']=='memory' else []):original+=json.loads((source/t['id']/arm/'calls.json').read_text(encoding='utf-8'))
 fresh=[c for c in all_corrected_calls if c['stage']=='agent' and not c.get('replayed_transport_only')]
 out={'kind':m['kind'],'by_kind':by_kind,'actual_provider_requests':dict(Counter(c['provider'] for c in original+fresh)),'new_continuation_calls':new,
      'actual_usage_including_original_errors':{p:usage([c for c in original+fresh if c['provider']==p]) for p in ['deepseek','jev']},
      'memory_reference_coverage':coverage,'coverage_helper_associations':helper_accuracy,'artifact_trajectories_replayed':replayed,'all_input_source_hash_checks_pass':True,
      'caveats':['Authored checkpoint workflows, not a full coding benchmark.','Fourcases per avenue; ceiling results are no evidence of benefit, not proof of impossibility.','Original single-call harness failures preserved; corrected continuation reuses real paid outputs, not a fresh sample.','Latencies are reconstructed sum of actual call durations across replay/continuation, not a new wall-time benchmark.','Classical word/character retrieval, no dense embedding model benchmark.']}
 save(path/'summary.json',out);save(ROOT/'research/agentic_screen/summary.json',out);return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args();print(json.dumps(analyze(a.path),indent=2))
