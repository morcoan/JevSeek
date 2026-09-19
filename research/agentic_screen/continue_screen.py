from __future__ import annotations
import concurrent.futures,hashlib,json,threading,time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.agentic_screen.runner import Environment,SYSTEM,tools
from research.agentic_screen.tasks import fixtures,fixture_hash
from research.flash_integration.integration import Flash
from research.decoding_control.providers import credentials,save

SOURCE=ROOT/'.local/research/agentic-screen/1789826483803027400'
LOCK=threading.Lock();NEW_CALLS=0


def apply_batch(env,tcs,remaining):
 from jsonschema import validate
 parsed=[];seen=set();probe_count=0;schemas={x['function']['name']:x['function']['parameters'] for x in tools(env.task)}
 for tc in tcs:
  assert tc['id'] not in seen;seen.add(tc['id']);name=tc['function']['name'];args=json.loads(tc['function']['arguments']);assert name in schemas;validate(args,schemas[name]);parsed.append((tc['id'],name,args))
  if name=='configure_and_check':probe_count+=len(args['checks'])
 assert probe_count<=3
 replies=[];executed=0
 for callid,name,args in parsed:
  if executed>=remaining or env.finished:r={'error':'action_budget_or_already_finished','executed':False}
  else:r=env.act(name,args);executed+=1
  replies.append({'role':'tool','tool_call_id':callid,'content':json.dumps(r,ensure_ascii=False)})
 return replies,executed


def branch(t,arm,target,key,deadline):
 global NEW_CALLS
 old=json.loads((SOURCE/t['id']/arm/'result.json').read_text(encoding='utf-8'));recorded=json.loads((SOURCE/t['id']/arm/'calls.json').read_text(encoding='utf-8'));helper=[c for c in recorded if c['stage']=='helper'];oldagent=[c for c in recorded if c['stage']=='agent'];env=Environment(t,target);flash=Flash(key);flash.client=flash.client.with_options(timeout=90);calls=helper.copy();errors=[];reused=0;fresh=0;executed=0
 messages=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(old['initial_visible'],ensure_ascii=False)}]
 try:
  for turn in range(4):
   if executed>=4:break
   cached=oldagent[turn] if turn<len(oldagent) and oldagent[turn]['messages']==messages else None
   if cached is not None:c={**cached,'replayed_transport_only':True};reused+=1
   else:
    if time.monotonic()>=deadline:errors.append('continuation_deadline');break
    with LOCK:
     if NEW_CALLS>=111:errors.append('new_call_budget');break
     NEW_CALLS+=1
    c=flash.call(messages,tools=tools(t),thinking=True,limit=8192);c.update(stage='agent',turn=turn,replayed_transport_only=False);fresh+=1
   calls.append(c);save(target/'calls.json',calls)
   if 'error' in c:errors.append(c['error']);break
   msg=c['message'];tcs=msg.get('tool_calls') or []
   if not tcs:env.finished=True;break
   try:replies,n=apply_batch(env,tcs,4-executed);executed+=n
   except Exception as exc:errors.append(type(exc).__name__);break
   messages.append(msg);messages.extend(replies)
   if env.finished:break
  row={'task':t['id'],'kind':t['kind'],'arm':arm,'initial_visible':old['initial_visible'],'selection':old['selection'],'events':env.events,'config':env.config,'revision':env.revision,'receipts':env.receipts,'finished':env.finished,
       'evaluation':env.result(),'errors':errors,'replayed_agent_calls':reused,'new_agent_calls':fresh,'executed_actions':executed,
       'serial_call_seconds':sum(c['seconds'] for c in calls),'timing_kind':'sum actual API call durations including reused calls; not a new contemporaneous full-loop wall measurement'}
  save(target/'calls.json',calls);save(target/'result.json',row);return row
 finally:flash.close()


def run():
 oldmanifest=json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'))
 for f,h in oldmanifest['source_sha256'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h
 assert fixture_hash()==oldmanifest['fixture_sha256'];ts={t['id']:t for t in fixtures()};old=json.loads((SOURCE/'results.json').read_text(encoding='utf-8'));assert len(old['results'])==52
 target=ROOT/'.local/research/agentic-screen'/('corrected-'+str(time.time_ns()));target.mkdir(parents=True);keys=credentials();deadline=time.monotonic()+360;rows=[]
 manifest={'kind':'same_checkpoint_transport_corrected_continuation_NOT_new_sample','source_run':SOURCE.name,'source_manifest_sha256':hashlib.sha256((SOURCE/'manifest.json').read_bytes()).hexdigest(),'fixture_sha256':fixture_hash(),
           'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['research/agentic_screen/continue_screen.py','research/agentic_screen/TRANSPORT_FIX.md']},'max_new_flash_calls':111,'new_jev_calls':0,'concurrency':4}
 save(target/'manifest.json',manifest)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures=[pool.submit(branch,ts[r['task']],r['arm'],target/r['task']/r['arm'],keys[0],deadline) for r in old['results']]
  for f in concurrent.futures.as_completed(futures):
   r=f.result();rows.append(r);save(target/'results.json',{'manifest':manifest,'results':rows});print(json.dumps({'task':r['task'],'arm':r['arm'],'result':r['evaluation'],'fresh_calls':r['new_agent_calls'],'errors':r['errors']}),flush=True)
 print('Corrected screen:',target,'new Flash calls:',NEW_CALLS,flush=True)
if __name__=='__main__':run()
