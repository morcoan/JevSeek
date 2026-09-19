from __future__ import annotations
import argparse,hashlib,json,statistics
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.efficiency.tasks import fixtures,fingerprint,evaluate
from research.efficiency.fastpath import request,render,RULE
from research.flash_integration.analyze import usage
from research.decoding_control.providers import save


def analyze(path):
 d=json.loads((path/'results.json').read_text(encoding='utf-8'));m=d['manifest'];ts={t['id']:t for t in fixtures()};assert fingerprint()==m['fixture_sha256']
 for f,h in m['source_sha256'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h
 expected={t['id'] for t in ts.values() if t['phase']==m['phase']};rows=d['results'];assert {r['task'] for r in rows}==expected
 arms=['thinking','plain','jev_verbose','jev_compact','code'];stats={a:{'correct':0,'total':0,'batch_correct':0,'none_correct':0,'none_total':0,'invalid':0,'seconds':[],'calls':[]} for a in arms};verified=0
 for r in rows:
  t=ts[r['task']];cs=json.loads((path/t['id']/'calls.json').read_text(encoding='utf-8'))
  for arm,v in r['arms'].items():
   ev=evaluate(t,v['answers']);assert ev==v['evaluation'];s=stats[arm]
   for k in ['correct','total','batch_correct','none_correct','none_total','invalid']:s[k]+=ev[k]
   s['seconds'].append(v['wall_seconds'])
   if v['result'] is not None:assert render(t['catalog'],t['queries'],v['answers'])==v['result'];verified+=1
   if arm=='code':continue
   c=cs[v['call']];assert c['arm']==arm;s['calls'].append(c)
   if arm.startswith('jev_'):
    state,qs=request(t['catalog'],t['queries'],arm=='jev_compact');assert c['state']==state and c['questions']==qs
   else:
    payload={'catalogue':{k:x['description'] for k,x in t['catalog'].items()},'queries':t['queries']};assert json.loads(c['messages'][1]['content'])==payload
    assert c['messages'][0]['content']==RULE+' Return only JSON {"answers":{"question_id":"catalogue_id"}} with every question exactly once.';assert c['thinking']==(arm=='thinking')
 for a,s in stats.items():
  cs=s.pop('calls');times=s.pop('seconds');s['median_endpoint_seconds']=statistics.median(times);s['usage']=usage(cs);s['reported_token_proxy']=s['usage']['input_tokens']+s['usage']['output_tokens']
 compact=stats['jev_compact'];comparisons={}
 for a in ['jev_verbose','thinking','plain']:
  other=stats[a];comparisons[a]={'compact_minus_correct':compact['correct']-other['correct'],'compact_minus_full_batches':compact['batch_correct']-other['batch_correct'],
    'median_speedup':other['median_endpoint_seconds']/compact['median_endpoint_seconds'],'reported_token_proxy_reduction':1-compact['reported_token_proxy']/other['reported_token_proxy'],
    'input_token_reduction':1-compact['usage']['input_tokens']/other['usage']['input_tokens']}
 out={'phase':m['phase'],'batches':len(rows),'queries':len(rows)*8,'arms':stats,'compact_comparisons':comparisons,
      'development_gate_passed':compact['usage']['errors']==0 and compact['invalid']==0 and compact['batch_correct']>=stats['jev_verbose']['batch_correct'],
      'validation':{'source_input_hashes_match':True,'rendered_results_recomputed':verified},'caveats':['Authored bounded dispatch endpoint, not a complete agent or novel-code task.','Caller supplies existing concrete catalogue and questions; authoring/permission costs are not measured here.','Provider token counts are accounting proxies, not equal compute or dollar units.','Small correlated batches; equal observed accuracy is not statistical noninferiority.']}
 save(path/'summary.json',out);save(ROOT/'research/efficiency'/(m['phase']+'_summary.json'),out);return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args();print(json.dumps(analyze(a.path),indent=2))
