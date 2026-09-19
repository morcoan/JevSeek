from __future__ import annotations
import argparse,concurrent.futures,hashlib,json,math,re,statistics,time
from collections import Counter
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.efficiency.tasks import fixtures,fingerprint,evaluate
from research.efficiency.fastpath import RULE,select,render,checked_answers
from research.flash_integration.integration import Flash
from research.decoding_control.providers import credentials,jev_client,save


def lexical(catalog,queries):
 stop={'the','a','an','and','or','to','of','in','that','it','is','be','must','only','verify','check','asserts','for','with','its','one','this'}
 def words(s):return [w for w in re.findall('[a-z0-9]+',s.lower()) if w not in stop]
 docs={k:Counter(words(v['description'])) for k,v in catalog.items() if k!='NONE'};df=Counter(w for d in docs.values() for w in d);n=len(docs)
 def vector(s):return {w:c*(1+math.log((n+1)/(df[w]+1))) for w,c in s.items()}
 dv={k:vector(v) for k,v in docs.items()}
 def score(a,b):return sum(v*b.get(w,0) for w,v in a.items())/(math.sqrt(sum(v*v for v in a.values())*sum(v*v for v in b.values())) or 1)
 result={}
 for q,s in queries.items():
  v=vector(Counter(words(s)));scores={k:score(v,d) for k,d in dv.items()};top=max(scores,key=scores.get);result[q]=top if scores[top]>=.12 else 'NONE'
 return result


def branch(t,path,keys,deadline):
 flash=Flash(keys[0]);flash.client=flash.client.with_options(timeout=90);jev=jev_client(keys[1]);calls=[];arms={};order=['thinking','plain','jev_verbose','jev_compact'];offset=int(t['id'].rsplit('-',1)[1])%4;order=order[offset:]+order[:offset]
 try:
  for arm in order:
   if time.monotonic()>=deadline:arms[arm]={'answers':None,'error':'run_deadline','wall_seconds':0};continue
   start=time.perf_counter()
   if arm.startswith('jev_'):
    row,c=select(jev,t['catalog'],t['queries'],compact=arm=='jev_compact')
   else:
    payload={'catalogue':{k:v['description'] for k,v in t['catalog'].items()},'queries':t['queries']}
    messages=[{'role':'system','content':RULE+' Return only JSON {"answers":{"question_id":"catalogue_id"}} with every question exactly once.'},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]
    c=flash.call(messages,thinking=arm=='thinking',limit=8192 if arm=='thinking' else 2048);row={'answers':None,'result':None}
    try:
     assert 'error' not in c;answers=json.loads(c['message']['content'])['answers'];row['answers']=checked_answers(t['catalog'],t['queries'],answers);row['result']=render(t['catalog'],t['queries'],answers)
    except Exception as exc:row['error']=type(exc).__name__
    row['wall_seconds']=time.perf_counter()-start
   c.update(arm=arm,task_id=t['id']);row['call']=len(calls);calls.append(c);arms[arm]=row;save(path/'calls.json',calls)
  start=time.perf_counter();answers=lexical(t['catalog'],t['queries']);arms['code']={'answers':answers,'result':render(t['catalog'],t['queries'],answers),'wall_seconds':time.perf_counter()-start}
  # Evaluate only after every provider arm decided.
  for v in arms.values():v['evaluation']=evaluate(t,v['answers'])
  row={'task':t['id'],'domain':t['domain'],'phase':t['phase'],'arms':arms};save(path/'result.json',row);return row
 finally:flash.close();jev.close()


def run(phase,development=None):
 ts=[t for t in fixtures() if t['phase']==phase];files=['research/efficiency/'+x for x in ['PROTOCOL.md','tasks.py','fastpath.py','experiment.py']]+['research/flash_integration/integration.py']
 hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
 if phase=='confirmation':
  assert development;old=json.loads((development/'manifest.json').read_text(encoding='utf-8'));summary=json.loads((development/'summary.json').read_text(encoding='utf-8'));assert hashes==old['source_sha256'] and summary['development_gate_passed']
 path=ROOT/'.local/research/efficiency'/ (phase+'-'+str(time.time_ns()));path.mkdir(parents=True)
 manifest={'phase':phase,'fixture_sha256':fingerprint(),'source_sha256':hashes,'max_flash_calls':len(ts)*2,'max_jev_calls':len(ts)*2,'cached_quality_labels':False,'scope':'bounded semantic dispatch endpoint, not a whole-agent benchmark'}
 save(path/'manifest.json',manifest);save(path/'fixtures.json',ts);keys=credentials();assert all(keys);deadline=time.monotonic()+(180 if phase=='development' else 420);rows=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  futures=[]
  for t in ts:
   p=path/t['id'];p.mkdir();futures.append(pool.submit(branch,t,p,keys,deadline))
  for f in concurrent.futures.as_completed(futures):
   row=f.result();rows.append(row);save(path/'results.json',{'manifest':manifest,'results':rows});print(json.dumps({'task':row['task'],'correct_of8':{a:v['evaluation']['correct'] for a,v in row['arms'].items()},'seconds':{a:round(v['wall_seconds'],3) for a,v in row['arms'].items()}}),flush=True)
 print('Private efficiency run:',path,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','confirmation'],default='development');p.add_argument('--development',type=Path);p.add_argument('--run',action='store_true');a=p.parse_args()
 if a.run:run(a.phase,a.development)
 else:print(json.dumps({'batches':len(fixtures()),'hash':fingerprint(),'no_calls':True}))
