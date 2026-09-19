"""Fresh, matched3arm confirmation of evidence scoping. No local model launch."""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import credentials,jev_client,save
from research.semantic_constraints.tasks import evaluate,visible
from research.semantic_constraints.experiment import CLASSIFIER,CRITERIA as OLD_CRITERIA,solve_labels
from research.semantic_reliability.runtime import Evidence,Query,ScopedEvaluator,RULES,CRITERIA
from research.semantic_reliability.diagnostic import mapped
from research.semantic_reliability.fresh_tasks import tasks,fingerprint


def make_queries(t):
 return [Query(j+'_'+h,'The candidate satisfies the ENTIRE following requirement: '+req,(Evidence('candidate:'+h,r['profile']),)) for j,req in t['jobs'].items() for h,r in t['hosts'].items()]

def run():
 from typesafe_sdk import Choice
 diagnostic=json.loads((Path(__file__).parent/'diagnostic_summary.json').read_text(encoding='utf-8'));assert diagnostic['selected_policy']=='focused'
 fixtures=tasks();directory=ROOT/'.local/research/semantic-reliability'/('fresh-'+str(time.time_ns()));directory.mkdir(parents=True)
 files=['runtime.py','fresh_tasks.py','fresh.py','FRESH_PROTOCOL.md']
 manifest={'kind':'fresh_synthetic_confirmation','fixture_sha256':fingerprint(),'source_sha256':{f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in files},'max_requests':144,'retries':0}
 save(directory/'manifest.json',manifest);save(directory/'fixtures.json',fixtures);_,key=credentials();client=jev_client(key);engine=ScopedEvaluator(client);calls=[];rows=[]
 try:
  for ti,t in enumerate(fixtures):
   row={'task':t['id'],'domain':t['domain'],'visible':visible(t),'arms':{}};qs=make_queries(t);order=['legacy','revised_global','focused'];order=order[ti%3:]+order[:ti%3]
   for arm in order:
    if arm=='focused':
     judgments,call=engine.assess(qs,'focused');labels=mapped(judgments)
    else:
     if arm=='legacy':
      state=visible(t);specs={j+'_'+h:{'instructions':'Consider ONLY service '+j+' and host '+h+'. Does this host satisfy the complete service requirement? '+CLASSIFIER,'criteria':OLD_CRITERIA} for j in t['jobs'] for h in t['hosts']}
     else:
      state={'evidence':{e.id:{'revision':e.revision,'text':e.text} for q in qs for e in q.evidence}}
      specs={q.id:{'instructions':RULES+'\nCLAIM: '+q.claim+'\nUse ONLY evidence IDs: '+json.dumps([e.id for e in q.evidence]),'criteria':CRITERIA} for q in qs}
     start=time.perf_counter();call={'provider':'jev','mode':arm,'state':state,'questions':specs};judgments=None
     try:
      response=client.system_one(state=state,questions={k:Choice(instructions=v['instructions'],criteria=v['criteria']) for k,v in specs.items()})
      raw=response.raw_http_response.json();answers={k:v.choice for k,v in response.answers.items()};assert set(answers)==set(specs)
      call.update(answers=answers,usage=raw.get('usage',{}),model=raw.get('model'))
      labels=answers if arm=='legacy' else mapped({k:{'truth':v} for k,v in answers.items()})
     except Exception as exc:call['error']=type(exc).__name__;labels={q.id:'unknown' for q in qs}
     call['seconds']=time.perf_counter()-start
    if call is not None:
     call.update(task_id=t['id'],arm=arm);idx=len(calls);assert idx<144;calls.append(call);save(directory/'calls.json',calls)
    else:idx=None
    found,cost,seconds=solve_labels(t,labels)
    row['arms'][arm]={'answers':labels,'judgments':judgments,'assignment':found,'cost':cost,'solver_seconds':seconds,'call':idx}
   for ar in row['arms'].values():ar['evaluation']=evaluate(t,ar['assignment'])
   rows.append(row);save(directory/'results.json',{'manifest':manifest,'results':rows})
   print(json.dumps({'task':t['id'],'optimal':{a:r['evaluation']['optimal'] for a,r in row['arms'].items()},'calls':len(calls)}),flush=True)
 finally:client.close()
 print('Private fresh results:',directory,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
 if a.run:run()
 else:print(json.dumps({'tasks':len(tasks()),'sha256':fingerprint(),'no_calls':True},indent=2))
