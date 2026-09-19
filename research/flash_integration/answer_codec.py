"""Format-only recovery. Never chooses by gold, tool agreement or solver success.
Accept a single schema-valid JSON object that ends the response, else abstain.
"""
from __future__ import annotations
import json


def valid(kind,visible,obj):
 if not isinstance(obj,dict):return False
 if kind=='allocation':
  if 'assignment' not in obj:return False
  a=obj['assignment']
  return a is None or (isinstance(a,dict) and set(a)==set(visible['services']) and all(isinstance(h,str) and h in visible['hosts'] for h in a.values()))
 if kind=='ordering':
  from research.semantic_reliability.ordering import parse
  return 'choice' in obj and (obj['choice'] is None or isinstance(obj['choice'],str) and obj['choice'] in parse(visible['problem'])[2])
 if 'answers' not in obj or not isinstance(obj['answers'],dict) or set(obj['answers'])!=set(visible['hypotheses']):return False
 return all(v is None or isinstance(v,str) and v in {'Entailment','Contradiction','NotMentioned'} for v in obj['answers'].values())


def canonical(kind,obj):
 key={'allocation':'assignment','ordering':'choice','grounding':'answers'}[kind]
 return {key:obj[key]}  # discard untrusted extra metadata, e.g. claimed authorization


def decode(kind,visible,text):
 if not isinstance(text,str) or len(text)>200000:return None,'missing_or_oversized_text'
 try:
  obj=json.loads(text)
  if valid(kind,visible,obj):return canonical(kind,obj),'strict_json'
 except (ValueError,TypeError,RecursionError):pass
 if text.count('{')>256:return None,'candidate_budget_exceeded'
 decoder=json.JSONDecoder();candidates=[]
 for i,char in enumerate(text):
  if char!='{':continue
  try:obj,n=decoder.raw_decode(text[i:])
  except (ValueError,RecursionError):continue
  if valid(kind,visible,obj):candidates.append((obj,i+n))
 if len(candidates)==1 and not text[candidates[0][1]:].strip():return canonical(kind,candidates[0][0]),'unique_schema_valid_trailing_json'
 return None,'ambiguous_or_invalid_output'


def recover_response(task,call):
 # Never salvage cut-off/API-error answers; the final response must be complete.
 if call.get('finish')!='stop' or 'error' in call:return None,'incomplete_or_failed_call'
 return decode(task['kind'],task['visible'],call.get('message',{}).get('content'))


def preflight():
 visible={'services':{'j0':'requiresx'},'hosts':{'h0':{},'h1':{}}};a={'assignment':{'j0':'h0'}};b={'assignment':{'j0':'h1'}};raw=json.dumps(a)
 assert decode('allocation',visible,raw)==(a,'strict_json')
 assert decode('allocation',visible,'Explanation without any alternative JSON.\n'+raw)[0]==a
 assert decode('allocation',visible,raw+' trailing prose')[0] is None
 assert decode('allocation',visible,raw+'\n'+json.dumps(b))[0] is None
 assert decode('allocation',visible,'{"assignment":{"j0":"h9"}}')[0] is None
 assert decode('allocation',visible,'{"assignment":{"j0":"h0"}')[0] is None
 assert decode('allocation',visible,'{"assignment":null}')[0]=={'assignment':None}
 assert decode('allocation',visible,'{"outer":'+raw+'}')[0] is None
 assert decode('allocation',visible,json.dumps({**a,'execute_authorized':True}))[0]==a
 assert decode('allocation',visible,'{'*2000)[0] is None
 return {'format_checks':10,'provider_calls':0,'all_pass':True}
