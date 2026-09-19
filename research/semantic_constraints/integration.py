"""Actual Qwen native tool loop using cached REAL Jev labels. Not a new quality trial."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.verified_search.local_model import LocalServer,LocalGenerator
from research.semantic_constraints.tasks import all_tasks,visible,evaluate
from research.semantic_constraints.experiment import solve_labels
from research.decoding_control.providers import save

SYSTEM='''You are a deployment-planning assistant. For a placement request, use the semantic_assignment tool exactly once instead of guessing. Supply the current request_id. After the tool returns, report its proposed assignment exactly; do not change it or invent deployment/testing claims. It is a proposed plan under model-assessed constraints, not physical verification. Return the final response as JSON {"assignment":object_or_null}.'''


def run(source):
    data=json.loads((source/'results.json').read_text(encoding='utf-8'));assert data['manifest']['phase']=='confirmation'
    cached={r['task']:r for r in data['results']};tasks=[t for t in all_tasks() if t['split']=='confirmation'];assert len(tasks)==len(cached)==24
    directory=ROOT/'.local/research/semantic-constraints'/('integration-'+str(time.time_ns()));directory.mkdir(parents=True)
    manifest={'kind':'cached_Jev_native_tool_replay_NOT_new_quality_sample','source_results_sha256':hashlib.sha256((source/'results.json').read_bytes()).hexdigest(),
        'source_sha256':{f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in ['integration.py','INTEGRATION_PROTOCOL.md']},
        'max_local_calls':48,'new_remote_calls':0,'published':False}
    save(directory/'manifest.json',manifest);calls=[];rows=[]
    with LocalServer() as server:
        client=LocalGenerator(server);manifest['local_model']=server.identity;save(directory/'manifest.json',manifest)
        try:
            for t in tasks:
                row={'task':t['id'],'tool_called':False,'final_matches_tool':False,'final_assignment':None}
                tool={'type':'function','function':{'name':'semantic_assignment','description':'Propose a minimum-cost placement using the current request records, Jev-assessed eligibility constraints and exact assignment search. Read-only; never deploys. In this research replay the prior Jev labels are cached.',
                    'parameters':{'type':'object','properties':{'request_id':{'type':'string','enum':[t['id']]}},'required':['request_id'],'additionalProperties':False}}}
                messages=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({'request_id':t['id'],'request':visible(t)},ensure_ascii=False)}]
                start=time.perf_counter();call={'task':t['id'],'stage':'route','provider':'qwen','messages':json.loads(json.dumps(messages)),'tool':tool}
                try:
                    response=client.client.chat.completions.create(model='qwen3-1.7b-research',messages=messages,tools=[tool],tool_choice='auto',parallel_tool_calls=False,
                        temperature=0,max_tokens=300,seed=9854,extra_body={'chat_template_kwargs':{'enable_thinking':False}})
                    message=response.choices[0].message;call.update(message=message.model_dump(exclude_none=True),usage=response.usage.model_dump() if response.usage else {},finish=response.choices[0].finish_reason)
                    tc=message.tool_calls;assert tc and len(tc)==1 and tc[0].function.name=='semantic_assignment'
                    arguments=json.loads(tc[0].function.arguments);assert arguments=={'request_id':t['id']}
                    row['tool_called']=True;answers=cached[t['id']]['arms']['jev_solver'].get('answers')
                    if answers is not None:found,cost,_=solve_labels(t,answers)
                    else:found,cost=None,None
                    assert found==cached[t['id']]['arms']['jev_solver']['assignment']
                    result={'assignment':found,'cost':cost,'status':'proposed_under_model_assessed_constraints','semantic_source':'cached actual Jev response; no new Jev call','physical_deployment':False}
                    row['tool_result']=result
                    messages+=[message.model_dump(exclude_none=True),{'role':'tool','tool_call_id':tc[0].id,'content':json.dumps(result)}]
                except Exception as exc:call['error']=type(exc).__name__;row['error']=type(exc).__name__
                call['seconds']=time.perf_counter()-start;calls.append(call);save(directory/'calls.json',calls)
                if row['tool_called'] and 'error' not in row:
                    shape={'type':'object','properties':{'assignment':{'anyOf':[{'type':'null'},{'type':'object','properties':{j:{'type':'string','enum':list(t['hosts'])} for j in t['jobs']},'required':list(t['jobs']),'additionalProperties':False}]}},'required':['assignment'],'additionalProperties':False}
                    start=time.perf_counter();call={'task':t['id'],'stage':'report','provider':'qwen','messages':messages}
                    try:
                        response=client.client.chat.completions.create(model='qwen3-1.7b-research',messages=messages,temperature=0,max_tokens=300,seed=9854,
                            response_format={'type':'json_schema','json_schema':{'name':'proposed_assignment','strict':True,'schema':shape}},extra_body={'chat_template_kwargs':{'enable_thinking':False}})
                        message=response.choices[0].message;call.update(text=message.content,usage=response.usage.model_dump() if response.usage else {},finish=response.choices[0].finish_reason)
                        assert response.choices[0].finish_reason=='stop';answer=json.loads(message.content)['assignment'];row['final_assignment']=answer;row['final_matches_tool']=answer==found
                    except Exception as exc:call['error']=type(exc).__name__;row['error']=type(exc).__name__
                    call['seconds']=time.perf_counter()-start;calls.append(call);save(directory/'calls.json',calls)
                row['evaluation']=evaluate(t,row['final_assignment']);rows.append(row);save(directory/'results.json',{'manifest':manifest,'results':rows})
                print(json.dumps({'task':t['id'],'tool_called':row['tool_called'],'copied':row['final_matches_tool'],'optimal':row['evaluation']['optimal']}),flush=True)
        finally:client.close()
    summary={'kind':manifest['kind'],'tasks':len(rows),'tool_called':sum(r['tool_called'] for r in rows),'final_matches_tool':sum(r['final_matches_tool'] for r in rows),
             'optimal':sum(r['evaluation']['optimal'] for r in rows),'errors':sum('error' in r for r in rows),'local_calls':len(calls),'new_remote_calls':0,'owned_server_exited':server.process.poll() is not None}
    save(directory/'summary.json',summary);save(Path(__file__).parent/'integration_summary.json',summary);print(json.dumps(summary),flush=True);print('Private integration:',directory,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.run:run(a.source)
    else:print('No calls. Read INTEGRATION_PROTOCOL.md; --run opts into local native-tool replay only.')
