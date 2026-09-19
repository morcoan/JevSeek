"""Live native Flash tool loop. Pure decision tools; never executes model code."""
from __future__ import annotations
import json,time
from research.semantic_reliability.runtime import Evidence,Query,specification
from research.semantic_reliability.bounded import ask_bounded
from research.semantic_reliability.engine import assignment_bounds
from research.semantic_reliability.ordering import parse
from research.semantic_reliability.nli import infer_specs

FORMATS={'allocation':'Return only JSON {"assignment":{"service_id":"host_id"}}, or null assignment if no plan can be justified.',
 'ordering':'Return only JSON {"choice":"option_letter"}.',
 'grounding':'For every hypothesis, classify it as Entailment, Contradiction or NotMentioned using only the document. Consider conditions, exceptions and cross-references; contractual duties do not prove behavior. Return only JSON {"answers":{"hypothesis_id":"label_or_null"}}. Null is an abstention, NOT NotMentioned.'}
BASE='Solve the supplied decision task accurately using only its evidence. Do not invent facts or claim real actions were executed. '
AGENT='You have a read-only decision_analysis tool for this structured request. Use it once to obtain scoped assessments and appropriate deterministic analysis. Assessments are fallible, not verified facts; you may correct its proposed answer using the original evidence. After the tool message give the final requested JSON. Do not call other tools or invent physical execution. '
BACKEND='Answer every independent typed question using ONLY its stated evidence and instructions. For each question return exactly one of its listed criterion IDs. Return JSON {"answers":{"question_id":"criterion_id"}}. No prose, rationale, omitted questions or invented IDs.'


class Flash:
 def __init__(self,key):
  from openai import OpenAI
  self.client=OpenAI(api_key=key,base_url='https://api.deepseek.com',timeout=180,max_retries=0)
 def close(self):self.client.close()
 def call(self,messages,*,tools=None,thinking=False,limit=2048):
  row={'provider':'deepseek','requested_model':'deepseek-flash','messages':json.loads(json.dumps(messages)),'thinking':thinking,'limit':limit}
  if tools:row['tools']=tools
  start=time.perf_counter()
  try:
   response=self.client.chat.completions.create(model='deepseek-flash',messages=messages,temperature=0,max_tokens=limit,
    reasoning_effort='high' if thinking else 'none',extra_body={'thinking':{'type':'enabled' if thinking else 'disabled'}},
    **({'tools':tools,'tool_choice':'auto','parallel_tool_calls':False} if tools else {'response_format':{'type':'json_object'}}))
   choice=response.choices[0];msg=choice.message;row.update(model=response.model,finish=choice.finish_reason,message=msg.model_dump(exclude_none=True),usage=response.usage.model_dump() if response.usage else {})
   if not thinking and getattr(msg,'reasoning_content',None):raise ValueError('unexpected_reasoning')
   if choice.finish_reason not in {'stop','tool_calls'}:raise ValueError('incomplete_response')
  except Exception as exc:row['error']=type(exc).__name__
  row['seconds']=time.perf_counter()-start;return row


def prepare(kind,visible):
 if kind=='allocation':
  qs={};mapping={}
  for j,req in visible['services'].items():
   for h,r in visible['hosts'].items():
    key='q'+str(len(qs));mapping[key]=(j,h);q=Query(key,'The candidate satisfies the ENTIRE following requirement: '+req,(Evidence('candidate:'+h,r['profile']),));qs[key]=specification(q)
  return {'role':'Independent evidence-scoped decisions. All relevant evidence is explicitly in each question.'},qs,mapping
 if kind=='ordering':
  _,_,opts=parse(visible['problem']);return {'problem':visible['problem']},{'choice':{'instructions':'Which single answer option is logically entailed by the stated ordering constraints? Use only the supplied facts.','criteria':opts}},{}
 qs,mapping=infer_specs(visible['hypotheses'],'standard');return {'evidence':{'document':visible['document']}},qs,mapping


def process(kind,visible,answers):
 state,qs,mapping=prepare(kind,visible);valid={k:v for k,v in answers.items() if k in qs and isinstance(v,str) and v in qs[k]['criteria']};invalid=sorted(set(qs)-set(valid))
 if kind=='allocation':
  relation={pair:valid.get(k,'unknown') for k,pair in mapping.items()}
  result=assignment_bounds(list(visible['services']),list(visible['hosts']),{k:v['cost'] for k,v in visible['hosts'].items()},relation)
  proposed={'assignment':result['proposed_assignment']};certificate=result
 elif kind=='ordering':proposed={'choice':valid.get('choice')};certificate={'semantic_proof':False,'method':'single_scoped_choice'}
 else:proposed={'answers':{key:valid.get(qid) for qid,key in mapping.items()}};certificate={'semantic_proof':False,'method':'document_grounded_NLI_not_legal_verification'}
 return {'proposed_answer':proposed,'analysis':certificate,'invalid_or_missing_questions':invalid,'physical_actions':False,'judgments_are_model_assessed':True}


def backend(kind,visible,provider,flash,jev):
 state,qs,mapping=prepare(kind,visible)
 if provider=='jev':
  result=ask_bounded(jev,state,qs,max_requests=2);answers=result.get('answers') or result.get('partial_answers',{});calls=result['calls'];errors=result['errors']
 else:
  c=flash.call([{'role':'system','content':BACKEND},{'role':'user','content':json.dumps({'state':state,'questions':qs},ensure_ascii=False)}]);calls=[c];answers={};errors=[]
  try:
   assert 'error' not in c;answers=json.loads(c['message']['content'])['answers'];assert isinstance(answers,dict)
  except Exception as exc:errors=[{'kind':type(exc).__name__}];answers={}
 start=time.perf_counter();tool_result=process(kind,visible,answers);solver_seconds=time.perf_counter()-start
 return tool_result,calls,{'answers':answers,'errors':errors,'solver_seconds':solver_seconds}


def parse_final(call):
 if 'error' in call:return None
 try:
  obj=json.loads(call['message']['content']);return obj if isinstance(obj,dict) else None
 except Exception:return None


def run_arm(task,arm,flash,jev):
 kind=task['kind'];visible=task['visible'];payload={'request_id':task['id'],'kind':kind,'request':visible}
 messages=[{'role':'system','content':BASE+FORMATS[kind]},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}];calls=[];start=time.perf_counter();row={'tool_used':False}
 if arm in {'direct','thinking'}:
  c=flash.call(messages,thinking=arm=='thinking',limit=8192 if arm=='thinking' else 2048);c['stage']='direct';calls.append(c);row['answer']=parse_final(c)
 else:
  messages[0]['content']=BASE+AGENT+FORMATS[kind]
  tool={'type':'function','function':{'name':'decision_analysis','description':'Analyze the current immutable request with scoped semantic assessments and deterministic constraint analysis where applicable. Read-only: no deployments or other effects. Judgments remain fallible.',
   'parameters':{'type':'object','properties':{'request_id':{'type':'string','enum':[task['id']]}},'required':['request_id'],'additionalProperties':False}}}
  c=flash.call(messages,tools=[tool],limit=2048);c['stage']='route';calls.append(c);row['answer']=parse_final(c)
  if 'error' not in c and c['message'].get('tool_calls'):
   try:
    tc=c['message']['tool_calls'];assert len(tc)==1 and tc[0]['function']['name']=='decision_analysis'
    arguments=json.loads(tc[0]['function']['arguments']);assert arguments=={'request_id':task['id']}
    row['tool_used']=True;result,subcalls,details=backend(kind,visible,'jev' if arm=='jev_tool' else 'deepseek',flash,jev)
    for sub in subcalls:sub['stage']='backend';calls.append(sub)
    row.update(tool_result=result,backend_details=details)
    messages.extend([c['message'],{'role':'tool','tool_call_id':tc[0]['id'],'content':json.dumps(result,ensure_ascii=False)}])
    final=flash.call(messages,limit=2048);final['stage']='report';calls.append(final);row['answer']=parse_final(final);row['matches_tool']=row['answer']==result['proposed_answer']
   except Exception as exc:row['integration_error']=type(exc).__name__;row['answer']=None
 row['wall_seconds']=time.perf_counter()-start
 return row,calls
