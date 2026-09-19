"""Opt-in research integration entrypoint; no app wiring or real actions.
The measured frozen loop is retained. New codec addresses prose+JSON violations.
"""
from .integration import run_arm
from .answer_codec import recover_response


def solve(task,flash,jev,*,semantic_backend='jev',allow_experimental_grounding=False):
 if semantic_backend not in {'jev','deepseek'}:raise ValueError('unknown_backend')
 if set(task)!={'id','kind','visible'}:raise ValueError('visible_request_only')
 if task['kind']=='grounding' and semantic_backend=='jev' and not allow_experimental_grounding:
  raise ValueError('Jev_document_grounding_regressed_requires_explicit_experimental_opt_in')
 row,calls=run_arm(task,'jev_tool' if semantic_backend=='jev' else 'self_tool',flash,jev)
 row['strict_answer']=row['answer']
 final=next((c for c in reversed(calls) if c['stage'] in {'report','route'}),None)
 if final:
  row['answer'],row['format_status']=recover_response(task,final)
 row['scope']='Research proposed decision only; no effects or execution authorization.'
 return row,calls
