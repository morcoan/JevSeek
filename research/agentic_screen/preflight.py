from __future__ import annotations
import json,tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.agentic_screen.tasks import fixtures,fixture_hash,outcomes
from research.agentic_screen.runner import Environment
from research.agentic_screen.policies import prepare,ranked


def run():
 checks=0
 with tempfile.TemporaryDirectory(dir=ROOT/'.local') as tmp:
  for t in fixtures():
   env=Environment(t,Path(tmp)/t['id']);assert not env.result()['verified_current'];checks+=1
   proper=[p for p,k in t['hidden']['probe_map'].items() if k in {'delivery','dedupe','unicode'}]
   out=env.act('configure_and_check',{'config':t['hidden']['expected'],'checks':proper});assert env.result()['success'] and all(r['passed'] for r in out['probe_results']);checks+=1
   wrong={**t['hidden']['expected'],'wire_codec':'ascii'};env.act('configure_and_check',{'config':wrong,'checks':[proper[0]]});assert not env.result()['success'];checks+=1
   env.act('finish',{});assert env.result()['false_completion'];checks+=1
   try:env.act('configure_and_check',{'config':wrong,'checks':list(t['probe_catalog'])})
   except Exception:checks+=1
   else:raise AssertionError('probe_budget_not_enforced')
   state,qs,pool=prepare(t);assert qs and all(len(q['criteria'])<=255 for q in qs.values());assert all(r['revision']=='current' and r['scope']==t['project'] for r in pool);checks+=1
   if t['kind']=='loop':
    for h in t['history']:
     expected=[k for k,v in outcomes(h['config'],t['hidden']['expected']).items() if k in {'delivery','dedupe','unicode'} and not v];assert expected==h['failing_probes'];checks+=1
 return {'offline_checks':checks,'fixtures':len(fixtures()),'fixture_sha256':fixture_hash(),'all_pass':True,'provider_calls':0}
if __name__=='__main__':print(json.dumps(run(),indent=2))
