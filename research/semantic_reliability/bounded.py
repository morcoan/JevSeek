"""Bounded batching of INDEPENDENT typed questions, without truncation.
A token-limit bisection changes request packaging only; all failures are retained.
"""
from __future__ import annotations
import json,time


def payload_bytes(state,specs):return len(json.dumps({'state':state,'questions':specs},ensure_ascii=False,separators=(',',':')).encode('utf-8'))


def pack(state,specs,max_bytes=60000,max_questions=30):
 if not specs or max_bytes<1000 or max_questions<1:raise ValueError('invalid_budget_or_empty_questions')
 groups=[];group={}
 for k,v in specs.items():
  if not isinstance(v,dict) or set(v)!= {'instructions','criteria'} or not 1<=len(v['criteria'])<=255:raise ValueError('invalid_question')
  candidate={**group,k:v}
  if group and (len(candidate)>max_questions or payload_bytes(state,candidate)>max_bytes):groups.append(group);group={k:v}
  else:group=candidate
 if group:groups.append(group)
 return groups


def ask_bounded(client,state,specs,*,max_bytes=60000,max_questions=30,max_requests=16):
 from typesafe_sdk import Choice
 pending=pack(state,specs,max_bytes,max_questions);answers={};calls=[];errors=[]
 while pending:
  group=pending.pop(0)
  if len(calls)>=max_requests:errors.append({'kind':'request_budget_exhausted','questions':list(group)});break
  # Never split a single source/criterion or discard part of its evidence.
  if len(group)==1 and payload_bytes(state,group)>max_bytes:
   errors.append({'kind':'singleton_evidence_exceeds_budget','questions':list(group)});continue
  start=time.perf_counter();call={'provider':'jev','state':state,'questions':group,'payload_bytes':payload_bytes(state,group)}
  try:
   response=client.system_one(state=state,questions={k:Choice(instructions=v['instructions'],criteria=v['criteria']) for k,v in group.items()})
   raw=response.raw_http_response.json();got={k:v.choice for k,v in response.answers.items()}
   assert set(got)==set(group) and all(v in group[k]['criteria'] for k,v in got.items())
   assert not set(got)&set(answers);answers.update(got);call.update(answers=got,usage=raw.get('usage',{}),model=raw.get('model'))
  except Exception as exc:
   token_limit=type(exc).__name__=='TypeSafeBadRequestError' and 'max_tokens_exceeded' in str(exc)
   call.update(error=type(exc).__name__,error_kind='token_limit' if token_limit else 'provider_or_schema_error')
   if token_limit and len(group)>1:
    items=list(group.items());mid=len(items)//2;pending=[dict(items[:mid]),dict(items[mid:])]+pending
   else:errors.append({'kind':call['error_kind'],'questions':list(group)})
  call['seconds']=time.perf_counter()-start;calls.append(call)
 if set(answers)!=set(specs):return {'answers':None,'partial_answers':answers,'errors':errors or [{'kind':'missing_answers'}],'calls':calls,'complete':False}
 return {'answers':answers,'errors':errors,'calls':calls,'complete':True}
