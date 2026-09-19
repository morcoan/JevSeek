from __future__ import annotations
import argparse,hashlib,json,statistics
from pathlib import Path
from math import comb
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import save
from research.flash_integration.tasks import fixtures,evaluate,check
from research.flash_integration.integration import prepare,process,BASE,AGENT,FORMATS,BACKEND
ARMS=['direct','thinking','self_tool','jev_tool']


def usage(cs):
 out={'calls':len(cs),'input_tokens':0,'output_tokens':0,'cache_hit_input_tokens':0,'reasoning_tokens_reported':0,'reasoning_usage_available_calls':0,'seconds':0.,'errors':0}
 for c in cs:
  u=c.get('usage',{});out['input_tokens']+=u.get('prompt_tokens',u.get('input_tokens',0));out['output_tokens']+=u.get('completion_tokens',u.get('output_tokens',0));out['cache_hit_input_tokens']+=u.get('prompt_cache_hit_tokens',0)
  details=u.get('completion_tokens_details') or {};r=details.get('reasoning_tokens',u.get('reasoning_tokens'))
  if r is not None:out['reasoning_usage_available_calls']+=1;out['reasoning_tokens_reported']+=r
  out['seconds']+=c['seconds'];out['errors']+='error' in c
 return out


def label_metrics(ts,rs,arm):
 labels=['Entailment','Contradiction','NotMentioned'];pairs=[]
 for r in rs:
  if r['kind']!='grounding':continue
  gold=ts[r['task']]['hidden']['gold'];a=r['arms'][arm].get('answer') or {};pred=a.get('answers') or {}
  pairs += [(v,pred.get(k)) for k,v in gold.items()]
 n=len(pairs);correct=sum(a==b for a,b in pairs);answered=sum(b in labels for a,b in pairs);by={}
 for label in labels:
  tp=sum(a==b==label for a,b in pairs);fp=sum(a!=label and b==label for a,b in pairs);fn=sum(a==label and b!=label for a,b in pairs)
  by[label]={'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0}
 return {'correct':correct,'total':n,'accuracy':correct/n if n else None,'abstentions':n-answered,'coverage':answered/n if n else None,'conditional_accuracy':correct/answered if answered else None,
         'macro_f1':sum(v['f1'] for v in by.values())/3,'false_entailments':by['Entailment']['fp'],'by_label':by}


def analyze(path):
 d=json.loads((path/'results.json').read_text(encoding='utf-8'));calls=json.loads((path/'calls.json').read_text(encoding='utf-8'));m=d['manifest'];ts={t['id']:t for t in fixtures()};assert check()==m['preflight']
 for f,h in m['source_sha256'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h
 expected={k:t for k,t in ts.items() if t['phase']==m['phase']};rows=d['results'];assert {r['task'] for r in rows}==set(expected)
 outcomes=0;tool_replays=0
 for r in rows:
  t=ts[r['task']];state,qs,mapping=prepare(t['kind'],t['visible'])
  for arm,v in r['arms'].items():
   try:ev=evaluate(t,v['answer'])
   except Exception as exc:ev={'correct':False,'answered':False,'evaluation_error':type(exc).__name__}
   assert ev==v['evaluation'];outcomes+=1
   cs=[calls[i] for i in v['calls']];route=next(c for c in cs if c['stage'] in {'direct','route'})
   assert json.loads(route['messages'][1]['content'])=={'request_id':t['id'],'kind':t['kind'],'request':t['visible']}
   assert route['messages'][0]['content']==BASE+(AGENT if arm in {'self_tool','jev_tool'} else '')+FORMATS[t['kind']]
   assert route['thinking']==(arm=='thinking')
   if v['tool_used']:
    tool_replays+=1;assert process(t['kind'],t['visible'],v['backend_details']['answers'])==v['tool_result']
    back=[c for c in cs if c['stage']=='backend']
    if arm=='self_tool':assert len(back)==1 and json.loads(back[0]['messages'][1]['content'])=={'state':state,'questions':qs} and back[0]['messages'][0]['content']==BACKEND
    else:
     assert all(c['state']==state for c in back);covered={}
     for c in back:
      for k,spec in c['questions'].items():assert spec==qs[k];covered[k]=spec
     assert covered==qs
    reports=[c for c in cs if c['stage']=='report'];assert len(reports)==1 and json.loads(reports[0]['messages'][-1]['content'])==v['tool_result']
 by_kind={}
 for kind in ['allocation','ordering','grounding']:
  rs=[r for r in rows if r['kind']==kind];summary={'tasks':len(rs),'arms':{},'paired':{}}
  for arm in ARMS:
   ars=[r['arms'][arm] for r in rs];cs=[c for c in calls if c['arm']==arm and c['task_id'] in {r['task'] for r in rs}]
   data={'correct_tasks':sum(x['evaluation']['correct'] for x in ars),'tool_used':sum(x['tool_used'] for x in ars),'final_matches_tool':sum(x.get('matches_tool',False) for x in ars),
         'median_wall_seconds':statistics.median(x['wall_seconds'] for x in ars),'usage':{p:usage([c for c in cs if c['provider']==p]) for p in ['deepseek','jev']}}
   if kind=='allocation':data['feasible']=sum(x['evaluation'].get('feasible',False) for x in ars)
   if kind=='grounding':data['labels']=label_metrics(ts,rs,arm)
   if arm in {'self_tool','jev_tool'}:
    evs=[evaluate(ts[r['task']],r['arms'][arm]['tool_result']['proposed_answer']) for r in rs if 'tool_result' in r['arms'][arm]]
    data['tool_stage_correct_tasks']=sum(e['correct'] for e in evs)
    if kind=='grounding':data['tool_stage_correct_labels']=sum(e['correct_labels'] for e in evs)
   summary['arms'][arm]=data
  for b in ['direct','self_tool','thinking']:
   metric='correct_labels' if kind=='grounding' else 'correct';a=[r['arms']['jev_tool']['evaluation'][metric] for r in rs];z=[r['arms'][b]['evaluation'][metric] for r in rs]
   wins=sum(x>y for x,y in zip(a,z));losses=sum(x<y for x,y in zip(a,z));n=wins+losses
   summary['paired']['jev_vs_'+b]={'improved_tasks_or_documents':wins,'worsened_tasks_or_documents':losses,'net_correct_labels_or_tasks':sum(a)-sum(z),
      'descriptive_sign_p':min(1.,2*sum(comb(n,i) for i in range(min(wins,losses)+1))/2**n) if n else 1.}
  by_kind[kind]=summary
 gate=all(r['arms'][a]['tool_used'] and 'integration_error' not in r['arms'][a] for r in rows for a in ['self_tool','jev_tool']) and not any('error' in c for c in calls if c['stage'] in {'route','backend','report'})
 out={'phase':m['phase'],'cases':len(rows),'transport_gate_passed':gate,'by_kind':by_kind,'calls_by_provider':{p:sum(c['provider']==p for c in calls) for p in ['deepseek','jev']},
      'errors':sum('error' in c for c in calls),'reported_models':sorted({c['model'] for c in calls if 'model' in c}),
      'validated':{'outcomes_recomputed':outcomes,'tool_results_recomputed':tool_replays,'all_source_hashes_and_visible_only_inputs_match':True},
      'caveats':['Small paired samples; NLI claims clustered by document.','Public benchmarks may be in training data.','Allocation uses synthetic complete facts and a bounded generator.','All model judgments are fallible; mathematical checks are conditional on them.','Tokens from different providers are not equal FLOP/dollar units.']}
 save(path/'summary.json',out);save(Path(__file__).parent/(m['phase']+'_summary.json'),out);return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args();print(json.dumps(analyze(a.path),indent=2))
