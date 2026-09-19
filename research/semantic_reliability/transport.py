"""Context-budget repair: known-case transport replay, then fresh7object validation."""
from __future__ import annotations
import argparse,hashlib,json,random,time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import credentials,jev_client,DeepSeekPrefix,save
from research.verified_search.local_model import LocalServer,LocalGenerator
from research.semantic_reliability.ordering import DATA,selection,parse,specs,solve
from research.semantic_reliability.ordering_experiment import DIRECT,COMPILE
from research.semantic_reliability.bounded import ask_bounded


def select_new():
 prior=selection();excluded={t['id'] for phase in ['development','confirmation'] for t in prior[phase]}
 raw=json.loads((DATA/'logical_deduction_seven_objects.json').read_text(encoding='utf-8'))['examples'];pool=[{'id':'seven-'+str(i),'size':7,'input':r['input'],'target':r['target'][1]} for i,r in enumerate(raw) if 'seven-'+str(i) not in excluded]
 random.Random(481709).shuffle(pool)
 return pool[:20]


def run(phase,development=None):
 from typesafe_sdk import Choice
 prior=selection();cases=([t for t in prior['confirmation'] if t['size']==7][:8] if phase=='replay' else select_new())
 files=['bounded.py','transport.py','TRANSPORT_PROTOCOL.md','ordering.py'];hashes={f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in files}
 if phase=='fresh':
  assert development;old=json.loads((development/'results.json').read_text(encoding='utf-8'));assert old['manifest']['source_sha256']==hashes
  assert len(old['results'])==8 and all(r['arms']['jev_compiler']['complete'] for r in old['results'])
 directory=ROOT/'.local/research/semantic-reliability'/('transport-'+phase+'-'+str(time.time_ns()));directory.mkdir(parents=True)
 manifest={'kind':'budget_repair_'+phase,'source_sha256':hashes,'case_sha256':hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest(),
           'phase':phase,'max_calls':128 if phase=='replay' else 380,'questions_unchanged':True,'semantic_retries':0}
 save(directory/'manifest.json',manifest);save(directory/'selection.json',cases);dk,jk=credentials();client=jev_client(jk);ds=DeepSeekPrefix(dk);calls=[];rows=[]
 server=None;local=None
 try:
  if phase=='fresh':server=LocalServer().__enter__();local=LocalGenerator(server);manifest['local_model']=server.identity;save(directory/'manifest.json',manifest)
  for ti,t in enumerate(cases):
   context,rules,options=parse(t['input']);qs,_=specs(context,rules,options);row={'task':t['id'],'arms':{}}
   order=['jev_compiler'] if phase=='replay' else ['qwen_direct','jev_direct','jev_compiler','ds_compiler'];shift=ti%len(order);order=order[shift:]+order[:shift]
   for arm in order:
    ar={'choice':None};start=time.perf_counter()
    if arm=='jev_compiler':
     bounded=ask_bounded(client,{'purpose':'Independent scoped sentence-to-constraint translation.'},qs)
     indexes=[]
     for c in bounded['calls']:
      c.update(task_id=t['id'],arm=arm);indexes.append(len(calls));calls.append(c)
     ar.update(complete=bounded['complete'],answers=bounded['answers'],transport_errors=bounded['errors'],calls=indexes)
     if bounded['complete']:
      ss=time.perf_counter();ar['solver']=solve(context,rules,options,bounded['answers']);ar['solver_seconds']=time.perf_counter()-ss;ar['choice']=ar['solver']['choice']
    else:
     c={'task_id':t['id'],'arm':arm};ar['calls']=[len(calls)]
     if arm=='qwen_direct':
      shape={'type':'object','properties':{'choice':{'type':'string','enum':list(options)}},'required':['choice'],'additionalProperties':False}
      c=local.generate(DIRECT,{'problem':t['input']},schema=shape,limit=200,temperature=0,seed=7311+ti);c.update(task_id=t['id'],arm=arm)
      try:
       assert 'error' not in c and c['finish']=='stop';ar['choice']=json.loads(c['text'])['choice'];assert ar['choice'] in options
      except Exception as exc:ar['error']=type(exc).__name__
     elif arm=='jev_direct':
      c.update(provider='jev',state={'problem':t['input']})
      try:
       response=client.system_one(state=c['state'],questions={'choice':Choice(instructions='Which single answer option is logically entailed by the stated ordering constraints? Use only the supplied facts.',criteria=options)})
       raw=response.raw_http_response.json();ar['choice']=response.answers['choice'].choice;c.update(answer=ar['choice'],usage=raw.get('usage',{}),model=raw.get('model'))
      except Exception as exc:c['error']=type(exc).__name__;ar['error']=type(exc).__name__
      c['seconds']=time.perf_counter()-start
     else:
      c=ds.generate(COMPILE,json.dumps({'questions':qs},ensure_ascii=False),limit=1000,temperature=0,json_output=True);c.update(task_id=t['id'],arm=arm)
      try:
       assert 'error' not in c and c['finish']=='stop';ar['answers']=json.loads(c['text'])['answers'];ss=time.perf_counter();ar['solver']=solve(context,rules,options,ar['answers']);ar['solver_seconds']=time.perf_counter()-ss;ar['choice']=ar['solver']['choice']
      except Exception as exc:ar['error']=type(exc).__name__
     calls.append(c)
    assert len(calls)<=manifest['max_calls'];save(directory/'calls.json',calls);row['arms'][arm]=ar
   for a in row['arms'].values():a['correct']=a['choice']==t['target']
   rows.append(row);save(directory/'results.json',{'manifest':manifest,'results':rows})
   print(json.dumps({'task':t['id'],'correct':{a:r['correct'] for a,r in row['arms'].items()},'complete':row['arms']['jev_compiler']['complete'],'calls':len(calls)}),flush=True)
 finally:
  client.close();ds.close()
  if local:local.close()
  if server:server.__exit__(None,None,None)
 if server:save(directory/'cleanup.json',{'owned_server_exited':server.process.poll() is not None})
 print('Private transport results:',directory,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['replay','fresh'],default='replay');p.add_argument('--development',type=Path);p.add_argument('--run',action='store_true');a=p.parse_args()
 if a.run:run(a.phase,a.development)
 else:print('No calls. Read TRANSPORT_PROTOCOL.md; --run opts in.')
