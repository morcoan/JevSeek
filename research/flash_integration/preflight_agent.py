"""Offline public entrypoint checks, including malformed-prose recovery."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import sys,json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.flash_integration.tasks import fixtures,evaluate
from research.flash_integration.integration import prepare,BACKEND
from research.flash_integration.agent import solve
from research.flash_integration.answer_codec import preflight


def run():
 checks=0
 for kind in ['allocation','ordering','grounding']:
  t=next(t for t in fixtures() if t['kind']==kind);visible={k:t[k] for k in ['id','kind','visible']};state,qs,mapping=prepare(kind,t['visible'])
  if kind=='allocation':answers={k:'supported' if t['hidden']['truth_matrix'][j+'_'+h] else 'refuted' for k,(j,h) in mapping.items()}
  elif kind=='ordering':answers={'choice':t['hidden']['gold']}
  else:answers={k:t['hidden']['gold'][v] for k,v in mapping.items()}
  class FakeFlash:
   def call(self,messages,tools=None,**kwargs):
    if tools:message={'role':'assistant','tool_calls':[{'id':'t0','type':'function','function':{'name':'decision_analysis','arguments':json.dumps({'request_id':t['id']})}}]}
    elif messages[0]['content']==BACKEND:message={'role':'assistant','content':json.dumps({'answers':answers})}
    else:
     proposed=json.loads(messages[-1]['content'])['proposed_answer'];message={'role':'assistant','content':'Explanation outside the requested JSON.\n'+json.dumps({**proposed,'execute_authorized':True})}
    return {'message':message,'seconds':0,'provider':'deepseek','finish':'tool_calls' if tools else 'stop'}
  class FakeJev:
   def system_one(self,*,state,questions):
    return SimpleNamespace(answers={k:SimpleNamespace(choice=answers[k]) for k in questions},raw_http_response=SimpleNamespace(json=lambda:{'model':'fake','usage':{}}))
  for mode in ['jev','deepseek']:
   result,calls=solve(visible,FakeFlash(),FakeJev(),semantic_backend=mode,allow_experimental_grounding=True)
   assert result['tool_used'] and result['format_status']=='unique_schema_valid_trailing_json';assert evaluate(t,result['answer'])['correct'];assert 'execute_authorized' not in result['answer'];checks+=1
  if kind=='grounding':
   try:solve(visible,FakeFlash(),FakeJev())
   except ValueError:checks+=1
   else:raise AssertionError('regressing grounding path enabled without opt-in')
  try:solve(t,FakeFlash(),FakeJev())
  except ValueError:checks+=1
  else:raise AssertionError('hidden fields admitted by public interface')
 return {'entrypoint_checks':checks,'codec_checks':preflight(),'all_pass':True,'provider_calls':0}
if __name__=='__main__':print(json.dumps(run(),indent=2))
