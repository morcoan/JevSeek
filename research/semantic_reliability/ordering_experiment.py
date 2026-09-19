"""Paid opt-in third-party ordering transfer. See ORDERING_PROTOCOL.md."""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import credentials,jev_client,DeepSeekPrefix,save
from research.verified_search.local_model import LocalServer,LocalGenerator
from research.semantic_reliability.ordering import DATA,parse,specs,solve,selection

DIRECT='Select the single answer option logically entailed by the statements. Return only JSON {"choice":"letter"}. No explanation, code or new assumptions.'
COMPILE='Translate each source sentence independently into exactly one equivalent constraint from its allowed catalog. Respect the explicit axis and one-indexed positions. Do not solve the entire puzzle in place of translating the sentence. Return only JSON {"answers":{"question_id":"criterion_id"}} with every question exactly once. Use unsupported for unrepresentable/unclear meaning. No prose or code.'


def run(phase,development=None):
 from typesafe_sdk import Choice
 sel=selection();frozen=json.loads((DATA/'ordering-selection.json').read_text(encoding='utf-8'));assert sel==frozen
 files=['ordering.py','ordering_experiment.py','ORDERING_PROTOCOL.md'];hashes={f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in files}
 if phase=='confirmation':
  assert development
  prior=json.loads((development/'summary.json').read_text(encoding='utf-8'));assert prior['development_gate_passed']
  old=json.loads((development/'manifest.json').read_text(encoding='utf-8'));assert old['source_sha256']==hashes
 cases=sel[phase];directory=ROOT/'.local/research/semantic-reliability'/('ordering-'+phase+'-'+str(time.time_ns()));directory.mkdir(parents=True)
 manifest={'kind':'BBH_ordering','phase':phase,'source_sha256':hashes,'selection_sha256':hashlib.sha256((DATA/'ordering-selection.json').read_bytes()).hexdigest(),'max_calls':len(cases)*4,'retries':0}
 save(directory/'manifest.json',manifest);dk,jk=credentials();calls=[];rows=[]
 def record(c):
  i=len(calls);assert i<manifest['max_calls'];calls.append(c);save(directory/'calls.json',calls);return i
 with LocalServer() as server:
  local=LocalGenerator(server);ds=DeepSeekPrefix(dk);jev=jev_client(jk);manifest['local_model']=server.identity;save(directory/'manifest.json',manifest)
  try:
   for ti,t in enumerate(cases):
    context,rules,options=parse(t['input']);qs,choices=specs(context,rules,options);row={'task':t['id'],'size':t['size'],'arms':{}}
    order=['qwen_direct','jev_direct','jev_compiler','ds_compiler'];order=order[ti%4:]+order[:ti%4]
    for arm in order:
     ar={'choice':None};start=time.perf_counter()
     if arm=='qwen_direct':
      shape={'type':'object','properties':{'choice':{'type':'string','enum':list(options)}},'required':['choice'],'additionalProperties':False}
      c=local.generate(DIRECT,{'problem':t['input']},schema=shape,limit=200,temperature=0,seed=7311+ti);c.update(task_id=t['id'],arm=arm);ar['call']=record(c)
      try:
       assert 'error' not in c and c['finish']=='stop';answer=json.loads(c['text'])['choice'];assert answer in options;ar['choice']=answer
      except Exception as exc:ar['error']=type(exc).__name__
     elif arm=='jev_direct':
      c={'provider':'jev','task_id':t['id'],'arm':arm,'state':{'problem':t['input']}}
      try:
       response=jev.system_one(state=c['state'],questions={'choice':Choice(instructions='Which single answer option is logically entailed by the stated ordering constraints? Use only the supplied facts.',criteria=options)})
       raw=response.raw_http_response.json();ar['choice']=response.answers['choice'].choice;c.update(answer=ar['choice'],usage=raw.get('usage',{}),model=raw.get('model'))
      except Exception as exc:c['error']=type(exc).__name__;ar['error']=type(exc).__name__
      c['seconds']=time.perf_counter()-start;ar['call']=record(c)
     else:
      if arm=='ds_compiler':
       payload={'questions':qs};c=ds.generate(COMPILE,json.dumps(payload,ensure_ascii=False),limit=1000,temperature=0,json_output=True);c.update(task_id=t['id'],arm=arm);ar['call']=record(c)
       try:
        assert 'error' not in c and c['finish']=='stop';answers=json.loads(c['text'])['answers'];ar['answers']=answers
       except Exception as exc:ar['error']=type(exc).__name__
      else:
       c={'provider':'jev','task_id':t['id'],'arm':arm,'state':{'purpose':'Independent scoped sentence-to-constraint translation.'},'questions':qs}
       try:
        response=jev.system_one(state=c['state'],questions={k:Choice(instructions=q['instructions'],criteria=q['criteria']) for k,q in qs.items()})
        raw=response.raw_http_response.json();answers={k:v.choice for k,v in response.answers.items()};ar['answers']=answers;c.update(answers=answers,usage=raw.get('usage',{}),model=raw.get('model'))
       except Exception as exc:c['error']=type(exc).__name__;ar['error']=type(exc).__name__
       c['seconds']=time.perf_counter()-start;ar['call']=record(c)
      if 'answers' in ar:
       ss=time.perf_counter();ar['solver']=solve(context,rules,options,ar['answers']);ar['solver_seconds']=time.perf_counter()-ss;ar['choice']=ar['solver']['choice']
     row['arms'][arm]=ar
    # Labels exposed to evaluator only after every arm decided.
    for ar in row['arms'].values():ar['correct']=ar['choice']==t['target']
    rows.append(row);save(directory/'results.json',{'manifest':manifest,'results':rows})
    print(json.dumps({'task':t['id'],'correct':{a:r['correct'] for a,r in row['arms'].items()},'calls':len(calls)}),flush=True)
  finally:local.close();ds.close();jev.close()
 save(directory/'cleanup.json',{'owned_server_exited':server.process.poll() is not None})
 print('Private ordering results:',directory,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','confirmation'],default='development');p.add_argument('--development',type=Path);p.add_argument('--run',action='store_true');a=p.parse_args()
 if a.run:run(a.phase,a.development)
 else:print('No inference. Read ORDERING_PROTOCOL.md; opt in with --run.')
