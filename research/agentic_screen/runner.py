from __future__ import annotations
import argparse,concurrent.futures,copy,hashlib,json,threading,time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import credentials,jev_client,save
from research.flash_integration.integration import Flash
from research.agentic_screen.tasks import fixtures,fixture_hash,outcomes,evaluate
from research.agentic_screen.policies import ranked,select_context

SYSTEM='''You are resuming a configuration-maintenance task. Use original current evidence, not stale receipts or claims of success. All three requested behaviors must work and be verified on the resulting current revision. Probe descriptions explain what they actually test; a smoke/health/ASCII check is not full behavioral verification. You can inspect the archive, configure the client and run up to3 probes, or finish. Use inspect if required protocol values are missing. You have at most4tool turns. Helper associations are fallible suggestions, not proof; inspect the original evidence. No shell, arbitrary code or real deployment exists here. Call finish when done.'''


def tools(t):
 config={'type':'object','properties':{'receiver_key':{'type':'string','minLength':1,'maxLength':100},'token_header':{'type':'string','minLength':1,'maxLength':100},'wire_codec':{'type':'string','enum':['utf-8','ascii','latin-1']}},'required':['receiver_key','token_header','wire_codec'],'additionalProperties':False}
 defs=[('inspect','Search the entire current project archive with a query; returns original records with provenance.',{'type':'object','properties':{'query':{'type':'string','maxLength':400}},'required':['query'],'additionalProperties':False}),
       ('configure_and_check','Write the full JSON client configuration, then actually run up to3 selected owned probes. No arbitrary code.',{'type':'object','properties':{'config':config,'checks':{'type':'array','items':{'type':'string','enum':list(t['probe_catalog'])},'minItems':1,'maxItems':3,'uniqueItems':True}},'required':['config','checks'],'additionalProperties':False}),
       ('finish','End this branch. A declaration does not establish correctness or verification.',{'type':'object','properties':{},'additionalProperties':False})]
 return [{'type':'function','function':{'name':name,'description':desc,'parameters':schema}} for name,desc,schema in defs]


class Environment:
 def __init__(self,t,path):
  self.task=t;self.path=path;path.mkdir(parents=True,exist_ok=True);self.config=copy.deepcopy(t['config']);self.revision=t['revision'];self.receipts=copy.deepcopy(t['receipts']);self.finished=False;self.events=[];save(path/'config.json',self.config)
 def act(self,name,args):
  from jsonschema import validate
  schema=next((x['function']['parameters'] for x in tools(self.task) if x['function']['name']==name),None)
  if schema is None:raise ValueError('unknown_tool')
  validate(args,schema)
  if name=='inspect':result={'records':ranked(self.task,args['query'],True)[:6],'note':'Original current-scope observations only. No missing hit proves absence.'}
  elif name=='finish':self.finished=True;result={'ended':True}
  else:
   if args['config']!=self.config:self.revision+=1
   self.config=copy.deepcopy(args['config']);save(self.path/'config.json',self.config)
   # Probes read actual saved data, not the model's asserted outcome.
   self.config=json.loads((self.path/'config.json').read_text(encoding='utf-8'));actual=outcomes(self.config,self.task['hidden']['expected']);receipts=[]
   for p in args['checks']:
    row={'probe':p,'revision':self.revision,'passed':actual[self.task['hidden']['probe_map'][p]]};receipts.append(row);self.receipts.append(row)
   result={'revision':self.revision,'config':self.config,'probe_results':receipts,'note':'Only these observed checks ran; no declaration of full requirement coverage is implied.'}
  self.events.append({'tool':name,'arguments':copy.deepcopy(args),'result':copy.deepcopy(result)});return result
 def result(self):return evaluate(self.task,self.config,self.revision,self.receipts,self.finished)


def run_branch(task,arm,directory,keys,deadline):
 start=time.perf_counter();flash=Flash(keys[0]);flash.client=flash.client.with_options(timeout=90);jev=jev_client(keys[1]);calls=[];env=Environment(task,directory);errors=[]
 try:
  records,hint,helper,selection=select_context(task,arm,flash,jev,lambda:time.monotonic()<deadline);calls+=helper
  visible={k:task[k] for k in ['id','kind','goal','requirements','project','config','revision','receipts','history','probe_catalog']};visible.update(working_evidence=records,helper=hint,archive_size=len(task['records']))
  messages=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(visible,ensure_ascii=False)}];catalog=tools(task)
  for turn in range(4):
   if time.monotonic()>=deadline:errors.append('run_deadline');break
   c=flash.call(messages,tools=catalog,thinking=True,limit=8192);c.update(stage='agent',turn=turn);calls.append(c);save(directory/'calls.json',calls)
   if 'error' in c:errors.append(c['error']);break
   msg=c['message'];tcs=msg.get('tool_calls') or []
   if not tcs:env.finished=True;break
   if len(tcs)!=1:errors.append('multiple_tool_calls');break
   tc=tcs[0]
   try:result=env.act(tc['function']['name'],json.loads(tc['function']['arguments']))
   except Exception as exc:result={'error':type(exc).__name__};errors.append(type(exc).__name__)
   messages.extend([msg,{'role':'tool','tool_call_id':tc['id'],'content':json.dumps(result,ensure_ascii=False)}])
   if env.finished:break
  row={'task':task['id'],'kind':task['kind'],'arm':arm,'initial_visible':visible,'selection':selection,'events':env.events,'config':env.config,'revision':env.revision,'receipts':env.receipts,'finished':env.finished,
       'evaluation':env.result(),'errors':errors,'wall_seconds':time.perf_counter()-start,'calls':len(calls)}
  save(directory/'calls.json',calls);save(directory/'result.json',row);return row
 finally:flash.close();jev.close()


def run():
 ts=fixtures();directory=ROOT/'.local/research/agentic-screen'/str(time.time_ns());directory.mkdir(parents=True)
 source=['research/agentic_screen/'+x for x in ['PROTOCOL.md','tasks.py','policies.py','runner.py']]+['research/flash_integration/integration.py','research/semantic_reliability/bounded.py']
 manifest={'kind':'authored_checkpoint_to_completion_screen','source_sha256':{x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in source},'fixture_sha256':fixture_hash(),'cases':12,'max_provider_calls':244,'deadline_seconds':720,'concurrency':4,'no_generated_code_execution':True}
 save(directory/'manifest.json',manifest);save(directory/'fixtures.json',ts);keys=credentials();assert all(keys);deadline=time.monotonic()+720;rows=[]
 jobs=[]
 # Interleave avenues, rotate arms to reduce order/cache confounding.
 ordered=[ts[a*4+i] for i in range(4) for a in range(3)]
 for i,t in enumerate(ordered):
  arms=['base','code','self','jev'];arms=arms[i%4:]+arms[:i%4]
  if t['kind']=='memory':arms.append('full')
  jobs += [(t,a) for a in arms]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures={pool.submit(run_branch,t,a,directory/t['id']/a,keys,deadline):(t['id'],a) for t,a in jobs}
  for f in concurrent.futures.as_completed(futures):
   tid,arm=futures[f]
   try:r=f.result()
   except Exception as exc:r={'task':tid,'arm':arm,'fatal_error':type(exc).__name__}
   rows.append(r);save(directory/'results.json',{'manifest':manifest,'results':rows});print(json.dumps({'task':tid,'arm':arm,'result':r.get('evaluation'),'seconds':round(r.get('wall_seconds',0),2),'errors':r.get('errors',r.get('fatal_error'))}),flush=True)
 print('Private screen:',directory,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
 if a.run:run()
 else:print(json.dumps({'cases':len(fixtures()),'fixture_sha256':fixture_hash(),'no_calls':True}))
