from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import credentials,jev_client,save
from research.flash_integration.tasks import fixtures,check,evaluate
from research.flash_integration.integration import Flash,run_arm


def run(phase,development=None):
 files=['research/flash_integration/'+f for f in ['PROTOCOL.md','tasks.py','integration.py','experiment.py']]+['research/semantic_reliability/'+f for f in ['runtime.py','bounded.py','engine.py','nli.py','ordering.py','fresh_tasks.py']]+['research/semantic_constraints/tasks.py']
 hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files};preflight=check();cases=[t for t in fixtures() if t['phase']==phase]
 if phase=='confirmation':
  assert development;old=json.loads((development/'summary.json').read_text(encoding='utf-8'));assert old['transport_gate_passed']
  prior=json.loads((development/'manifest.json').read_text(encoding='utf-8'));assert prior['source_sha256']==hashes
 directory=ROOT/'.local/research/flash-integration'/ (phase+'-'+str(time.time_ns()));directory.mkdir(parents=True)
 manifest={'phase':phase,'kind':'live_Flash_native_tool_comparison','source_sha256':hashes,'preflight':preflight,'model_identity_source':'https://api-docs.deepseek.com/news/news260910',
           'max_flash_calls':len(cases)*7,'max_jev_calls':len(cases)*2,'cached_model_labels':False}
 save(directory/'manifest.json',manifest);save(directory/'fixtures.json',cases);dk,jk=credentials();flash=Flash(dk);jev=jev_client(jk);calls=[];rows=[]
 try:
  for ti,t in enumerate(cases):
   row={'task':t['id'],'kind':t['kind'],'arms':{}};order=['direct','thinking','self_tool','jev_tool'];shift=ti%4;order=order[shift:]+order[:shift]
   for arm in order:
    ar,new_calls=run_arm(t,arm,flash,jev);ar['calls']=[]
    for c in new_calls:
     c.update(task_id=t['id'],arm=arm);ar['calls'].append(len(calls));calls.append(c)
    assert sum(c['provider']=='deepseek' for c in calls)<=manifest['max_flash_calls'];assert sum(c['provider']=='jev' for c in calls)<=manifest['max_jev_calls']
    row['arms'][arm]=ar;save(directory/'calls.json',calls)
    print(json.dumps({'task':t['id'],'arm':arm,'completed':True,'seconds':round(ar['wall_seconds'],3),'tool_used':ar['tool_used']}),flush=True)
   # No scoring or labels accessed until ALL branches finished this task.
   for ar in row['arms'].values():
    try:ar['evaluation']=evaluate(t,ar['answer'])
    except Exception as exc:ar['evaluation']={'correct':False,'answered':False,'evaluation_error':type(exc).__name__}
   rows.append(row);save(directory/'results.json',{'manifest':manifest,'results':rows})
   print(json.dumps({'task_complete':t['id'],'scores':{a:r['evaluation'].get('correct_labels',r['evaluation']['correct']) for a,r in row['arms'].items()}}),flush=True)
 finally:flash.close();jev.close()
 print('Private results:',directory,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','confirmation'],default='development');p.add_argument('--development',type=Path);p.add_argument('--run',action='store_true');a=p.parse_args()
 if a.run:run(a.phase,a.development)
 else:print(json.dumps(check(),indent=2))
