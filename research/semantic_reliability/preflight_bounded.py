"""Offline tests for all-or-nothing batching and evidence preservation."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.semantic_reliability.bounded import pack,ask_bounded

def run():
 specs={f'q{i}':{'instructions':'Unchanged source '+str(i),'criteria':{'yes':'yes','no':'no'}} for i in range(5)}
 groups=pack({},specs,max_bytes=60000,max_questions=2);assert [len(g) for g in groups]==[2,2,1]
 assert {k:v for g in groups for k,v in g.items()}==specs
 BadRequest=type('TypeSafeBadRequestError',(Exception,),{})
 class Fake:
  calls=0
  def system_one(self,*,state,questions):
   self.calls+=1
   if len(questions)>2:raise BadRequest('max_tokens_exceeded')
   return SimpleNamespace(answers={k:SimpleNamespace(choice='yes') for k in questions},raw_http_response=SimpleNamespace(json=lambda:{'model':'fake','usage':{}}))
 f=Fake();r=ask_bounded(f,{},specs,max_questions=30);assert r['complete'] and len(r['answers'])==5 and len(r['calls'])==5
 assert sum('error' in c for c in r['calls'])==2
 r=ask_bounded(Fake(),{},specs,max_requests=1);assert not r['complete'] and r['answers'] is None
 huge={'q':{'instructions':'x'*5000,'criteria':{'yes':'yes'}}};f=Fake();r=ask_bounded(f,{},huge,max_bytes=1000);assert not r['complete'] and f.calls==0
 class OtherFailure:
  calls=0
  def system_one(self,**kwargs):self.calls+=1;raise RuntimeError('network_failure')
 f=OtherFailure();r=ask_bounded(f,{},specs);assert not r['complete'] and f.calls==1
 return {'offline_batch_checks':7,'all_pass':True,'provider_calls':0}
if __name__=='__main__':print(run())
