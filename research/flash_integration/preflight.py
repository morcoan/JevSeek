from __future__ import annotations
import json,itertools
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.flash_integration.tasks import fixtures,check,evaluate
from research.flash_integration.integration import prepare,process,run_arm,BACKEND
from research.semantic_reliability.engine import assignment_bounds


def run():
 checks=0
 for t in fixtures():
  state,qs,mapping=prepare(t['kind'],t['visible']);assert qs and all(1<=len(q['criteria'])<=255 for q in qs.values());checks+=1
  if t['kind']=='allocation':
   answers={k:'supported' if t['hidden']['truth_matrix'][j+'_'+h] else 'refuted' for k,(j,h) in mapping.items()}
  elif t['kind']=='ordering':answers={'choice':t['hidden']['gold']}
  else:answers={k:t['hidden']['gold'][v] for k,v in mapping.items()}
  tool=process(t['kind'],t['visible'],answers);assert evaluate(t,tool['proposed_answer'])['correct'];assert not tool['analysis']['semantic_proof'];checks+=1
  class FakeFlash:
   def call(self,messages,tools=None,**kwargs):
    if tools:
     request=json.loads(messages[1]['content']);assert set(request)=={'request_id','kind','request'} and request['request']==t['visible']
     message={'role':'assistant','tool_calls':[{'id':'test_call','type':'function','function':{'name':'decision_analysis','arguments':json.dumps({'request_id':t['id']})}}]}
    elif messages[0]['content']==BACKEND:
     assert json.loads(messages[1]['content'])=={'state':state,'questions':qs};message={'role':'assistant','content':json.dumps({'answers':answers})}
    else:
     result=json.loads(messages[-1]['content']);message={'role':'assistant','content':json.dumps(result['proposed_answer'])}
    return {'message':message,'seconds':0,'provider':'deepseek'}
  row,calls=run_arm(t,'self_tool',FakeFlash(),None);assert len(calls)==3 and row['tool_used'] and row['matches_tool'] and evaluate(t,row['answer'])['correct'];checks+=1
 # Every completion of unknown edges must lie between optimistic and conservative costs.
 items=['a','b'];slots=['x','y','z'];costs={'x':1,'y':2,'z':4};keys=list(itertools.product(items,slots))
 for values in itertools.product(['supported','refuted','unknown'],repeat=6):
  relation=dict(zip(keys,values));r=assignment_bounds(items,slots,costs,relation);unknown=[k for k,v in relation.items() if v=='unknown']
  for bits in itertools.product(['supported','refuted'],repeat=len(unknown)):
   world={**relation,**dict(zip(unknown,bits))};actual=assignment_bounds(items,slots,costs,world)['cost']
   if actual is not None:assert r['optimistic_lower_cost']<=actual
   if r['cost'] is not None:assert actual is not None and actual<=r['cost']
  checks+=1
 return {**check(),'offline_checks':checks,'provider_calls':0,'all_pass':True}
if __name__=='__main__':print(json.dumps(run(),indent=2))
