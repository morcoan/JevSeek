from __future__ import annotations
import json,hashlib
from pathlib import Path
from types import SimpleNamespace
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.efficiency.tasks import fixtures,fingerprint,evaluate
from research.efficiency.fastpath import request,render,select,checked_answers


def run():
 count=0;payloads=[]
 for t in fixtures():
  vstate,vq=request(t['catalog'],t['queries'],False);cstate,cq=request(t['catalog'],t['queries'],True)
  assert len(vq)==len(cq)==8 and len(t['catalog'])==13;count+=1
  assert cstate['catalogue']=={k:v['description'] for k,v in t['catalog'].items()};assert all(set(q['criteria'])==set(t['catalog']) and all(v is None for v in q['criteria'].values()) for q in cq.values());count+=1
  assert evaluate(t,t['hidden']['gold'])['batch_correct'];out=render(t['catalog'],t['queries'],t['hidden']['gold']);assert out['proposed_calls']['q6'] is None and out['proposed_calls']['q7'] is None and not out['execution_authorized'] and not out['executed'];count+=1
  a=next(v for v in out['proposed_calls'].values() if v);a['arguments']['artifact_id']='mutated';assert all(x['call'] is None or x['call']['arguments']['artifact_id']!='mutated' for x in t['catalog'].values());count+=1
  class Fake:
   def system_one(self,state,questions):return SimpleNamespace(answers={k:SimpleNamespace(choice=t['hidden']['gold'][k]) for k in questions},raw_http_response=SimpleNamespace(json=lambda:{'model':'fake','usage':{}}))
  row,call=select(Fake(),t['catalog'],t['queries']);assert row['answers']==t['hidden']['gold'] and row['result']['executed'] is False;count+=1
  try:checked_answers(t['catalog'],t['queries'],{'q0':'made_up'})
  except ValueError:count+=1
  else:raise AssertionError('bad_labels_accepted')
  payloads.append({'id':t['id'],'verbose_bytes':len(json.dumps({'state':vstate,'questions':vq}).encode()),'compact_bytes':len(json.dumps({'state':cstate,'questions':cq}).encode())})
 return {'offline_checks':count,'all_pass':True,'fixture_sha256':fingerprint(),'provider_calls':0,'payload_sizes':payloads}
if __name__=='__main__':print(json.dumps(run(),indent=2))
