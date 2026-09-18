"""Controlled JIT vs frozen-sequence benchmark. No turn/call limit.
Run from repo root: python benchmarks/compare_routing.py jit|pre
Four action adapters; read/write/edit delegate to OpenHands FileEditorExecutor.
Bash is a test-runner subprocess with fixed allowed commands (not an OS sandbox).
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
os.environ['OPENHANDS_SUPPRESS_BANNER']='1'
import litellm
from typesafe_sdk import TypeSafeClient, Choice
from openhands.tools.file_editor import FileEditorAction
from openhands.tools.file_editor.impl import FileEditorExecutor

BASE=Path(__file__).resolve().parent
FIXTURE=BASE/'build_engine'
TOOLS={'read':'Inspect existing source, specification, or tests. No changes.',
       'write':'Create a NEW file with full content.',
       'edit':'Modify an existing file with exact text replacement, including a complete rewrite.',
       'bash':'Execute the public or independent acceptance tests; observe pass/fail and errors.'}
SCHEMAS={
'read': {'path':'relative path'},
'write': {'path':'relative path','content':'complete file text'},
'edit': {'path':'relative path','old':'exact existing text','new':'replacement text'},
'bash': {'command':'python acceptance.py OR python -m unittest -v test_public.py'}}
SYSTEM=('You supply arguments for exactly the tool selected by Jev, not a plan or another tool. '
        'Return only a JSON object matching that tool schema. Use full observed source and results. '
        'Fix implementation, never weaken tests. Only engine.py and new extra test files may be changed. '
        'No internet, external packages or shell workarounds. Schemas: '+json.dumps(SCHEMAS))


def main(mode):
    dest=BASE/'results'/f'{mode}-{time.strftime("%Y%m%d-%H%M%S")}'
    work=dest/'workspace'; work.mkdir(parents=True)
    for name in ['engine.py','SPEC.md','test_public.py']: shutil.copy(FIXTURE/name,work/name)
    evaluator=FIXTURE/'acceptance_suite.py'
    launcher=f'import runpy\nrunpy.run_path({str(evaluator)!r}, run_name="__main__")\n'
    (work/'acceptance.py').write_text(launcher)
    task=('Complete engine.py according to the following specification. Initial workspace files: '
          'engine.py (unfinished implementation), SPEC.md, test_public.py, acceptance.py.\n'+(FIXTURE/'SPEC.md').read_text())
    initial={'user_intent':task,'initial_files':['engine.py','SPEC.md','test_public.py','acceptance.py']}
    history=[]; metrics=[]; started=time.perf_counter()
    log=dest/'events.jsonl'
    def event(kind,**fields):
        with log.open('a',encoding='utf-8') as f: f.write(json.dumps({'kind':kind,**fields},ensure_ascii=False)+'\n')
    def jev(state,instructions,criteria):
        t=time.perf_counter()
        response=client.system_one(state=state,questions={'decision':Choice(instructions=instructions,criteria=criteria)})
        a=response.answers['decision']; data=response.raw_http_response.json()
        m={'provider':'jev','seconds':time.perf_counter()-t,'response':data}; metrics.append(m); event('jev',**m)
        return a.choice
    ds_messages=[{'role':'system','content':SYSTEM},{'role':'user','content':task}]
    def ds(messages,json_mode=False):
        t=time.perf_counter()
        kwargs={'response_format':{'type':'json_object'}} if json_mode else {}
        r=litellm.completion(model='deepseek/deepseek-chat',api_key=os.getenv('DS_KEY'),base_url=os.getenv('LLM_BASE_URL','https://api.deepseek.com/v1'),messages=messages,temperature=0,**kwargs)
        metrics.append({'provider':'deepseek','seconds':time.perf_counter()-t,'usage':r.usage.model_dump()})
        event('deepseek',**metrics[-1]); return r.choices[0].message.content
    def execute(tool,p):
        if tool=='bash':
            allowed={'python acceptance.py':[sys.executable,'acceptance.py'], 'python -m unittest -v test_public.py':[sys.executable,'-m','unittest','-v','test_public.py']}
            if p['command'] not in allowed: raise ValueError('Only the two documented test commands are allowed')
            r=subprocess.run(allowed[p['command']],cwd=work,capture_output=True,text=True,timeout=120)
            return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
        path=(work/p['path']).resolve()
        if not path.is_relative_to(work.resolve()): raise ValueError('Path outside workspace')
        if tool!='read' and (path.name in ['SPEC.md','test_public.py','acceptance.py'] or (path.exists() and path.name!='engine.py')): raise ValueError('Evaluator file is read-only')
        kwargs={'command':{'read':'view','write':'create','edit':'str_replace'}[tool],'path':str(path)}
        if tool=='write': kwargs['file_text']=p['content']
        if tool=='edit': kwargs.update(old_str=p['old'],new_str=p['new'])
        result=editor(FileEditorAction(**kwargs))
        return result.model_dump(mode='json')
    client=TypeSafeClient(api_key=os.getenv('JEV_KET') or os.getenv('TYPESAFE_API_KEY'),model='jev-1.13.0')
    editor=FileEditorExecutor(workspace_root=str(work.resolve()))
    plan=[]
    if mode in ('pre', 'pre_explicit'):
        lo,hi=0,100
        while lo<hi:
            mid=(lo+hi)//2
            count_question='Estimate total individual tool calls needed to complete and verify this task; choose the interval.'
            if mode=='pre_explicit':
                count_question += ' Count tool invocations, not tests, functions, requirements, or lines. One edit can implement the entire module and one bash call can run all tests. Estimate the shortest plausible successful sequence.'
            choice=jev(initial,count_question,{'low':f'{lo} through {mid} calls','high':f'{mid+1} through {hi} calls'})
            if choice=='low': hi=mid
            else: lo=mid+1
        event('count',count=lo); print('PRE count',lo,flush=True)
        for i in range(lo):
            plan_question='Select the next tool in a frozen sequence that must complete the goal; no execution observations exist yet.'
            if mode=='pre_explicit':
                plan_question += ' This is offline scheduling: assume earlier scheduled tools have executed successfully by this future step. Do not keep selecting the first tool merely because execution has not started. Advance toward implementation and verification within the fixed total.'
            tool=jev({**initial,'fixed_count':lo,'previous_selected_tools':plan,'next_index':i+1},plan_question,TOOLS)
            plan.append(tool); print('PRE select',i+1,tool,flush=True)
        event('frozen_plan',tools=plan)
    step=0
    while True:
        if mode=='jit':
            tool=jev({**initial,'completed_turns':history},'Select the next single tool using user intent and actual completed turns, not model plans. Choose done only when implementation is complete and independent acceptance tests have passed.',{**TOOLS,'done':'All requested work is complete, verified by passing acceptance tests.'})
        else:
            if step==len(plan): break
            tool=plan[step]
        print(mode,'step',step+1,tool,flush=True)
        if tool=='done': break
        ds_messages.append({'role':'user','content':f'Jev selected {tool}. Supply its arguments only. Schema: {json.dumps(SCHEMAS[tool])}'})
        text=ds(ds_messages,True)
        ds_messages.append({'role':'assistant','content':text})
        try:
            payload=json.loads(text); obs=execute(tool,payload)
        except Exception as e:
            payload={'raw':text}; obs={'error':f'{type(e).__name__}: {e}'}
        turn={'tool':tool,'arguments':payload,'observation':obs}
        history.append(turn); event('turn',**turn)
        ds_messages.append({'role':'user','content':'Actual tool observation:\n'+json.dumps(obs,ensure_ascii=False)})
        step+=1
        print(json.dumps(obs,ensure_ascii=True)[:240],flush=True)
    # Evaluator is independent, not an agent-written self-test or router assertion.
    verdict=subprocess.run([sys.executable,'acceptance.py'],cwd=work,capture_output=True,text=True,timeout=120)
    (dest/'acceptance.txt').write_text(verdict.stdout+verdict.stderr,encoding='utf-8')
    summary=ds([{'role':'system','content':'Summarize actual work and verification in a few sentences. Do not claim success on failures.'}, {'role':'user','content':json.dumps({'user_intent':task,'turns':history,'independent_verification':{'exit_code':verdict.returncode,'output':verdict.stdout+verdict.stderr}})}])
    result={'mode':mode,'pass':verdict.returncode==0,'tool_turns':step,'plan':plan,'seconds':time.perf_counter()-started,'metrics':metrics,'summary':summary}
    (dest/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('RESULT',json.dumps({k:v for k,v in result.items() if k!='metrics'}),flush=True)
    client.close()

if __name__=='__main__': main(sys.argv[1])
