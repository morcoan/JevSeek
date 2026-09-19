"""Retrospective accounting only; never issues inference requests."""
from __future__ import annotations
import json,statistics,hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.flash_integration.analyze import usage
from research.decoding_control.providers import save


def run():
 f=ROOT/'.local/research/flash-integration/confirmation-1789822037006606000';rows=json.loads((f/'results.json').read_text(encoding='utf-8'))['results'];calls=json.loads((f/'calls.json').read_text(encoding='utf-8'));data={}
 for kind in ['allocation','ordering','grounding']:
  rs=[r for r in rows if r['kind']==kind];ids={r['task'] for r in rs};section={}
  for arm in ['direct','thinking','self_tool','jev_tool']:
   cs=[c for c in calls if c['arm']==arm and c['task_id'] in ids];u={p:usage([c for c in cs if c['provider']==p]) for p in ['deepseek','jev']}
   section[arm]={'provider_usage':u,'reported_token_proxy':sum(x['input_tokens']+x['output_tokens'] for x in u.values()),'median_recorded_whole_loop_seconds':statistics.median(r['arms'][arm]['wall_seconds'] for r in rs)}
  bs=[sum(calls[i]['seconds'] for i in r['arms']['jev_tool']['calls'] if calls[i]['stage']=='backend')+r['arms']['jev_tool']['backend_details']['solver_seconds'] for r in rs]
  section['jev_backend_only_median_seconds']=statistics.median(bs);data[kind]=section
 a=ROOT/'.local/research/agentic-screen/corrected-1789826904784495500';ars=json.loads((a/'results.json').read_text(encoding='utf-8'))['results'];helpers={}
 for kind in ['memory','coverage','loop']:
  section={}
  for arm in ['self','jev']:
   cs=[];seconds=[]
   for r in ars:
    if r['kind']!=kind or r['arm']!=arm:continue
    subset=[c for c in json.loads((a/r['task']/arm/'calls.json').read_text(encoding='utf-8')) if c['stage']=='helper'];cs+=subset;seconds.append(sum(c['seconds'] for c in subset))
   u=usage(cs);section[arm]={'usage':u,'median_helper_seconds':statistics.median(seconds),'reported_token_proxy':u['input_tokens']+u['output_tokens']}
  helpers[kind]=section
 result={'kind':'retrospective_existing_trace_audit_NOT_new_quality_trial','new_provider_calls':0,'flash_integration':data,'agentic_helpers':helpers,
   'trace_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [f/'results.json',f/'calls.json',a/'results.json']},
   'warning':'Backend/helper timings exclude surrounding agent work. Removing other model stages is a proposed architecture, not a measured complete-agent speedup. Cross-provider token sums do not measure compute or cost.'}
 save(ROOT/'research/efficiency/existing_trace_audit.json',result);return result
if __name__=='__main__':print(json.dumps(run(),indent=2))
