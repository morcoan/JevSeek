"""Opt-in small-generator capability-gap experiment. See SMALL_MODEL_PROTOCOL.md."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import credentials,DeepSeekPrefix,jev_client,save
from research.verified_search.data import CACHE,schema,execute,evaluate
from research.verified_search.experiment import GENERATOR,DS_JUDGE,pool_view,select,majority
from research.verified_search.local_model import LocalServer,LocalGenerator

SQL_SCHEMA={'type':'object','properties':{'sql':{'type':'string'}},'required':['sql'],'additionalProperties':False}


def run(phase,development=None):
    from typesafe_sdk import Choice
    selection=json.loads((CACHE/'selection.json').read_text());tasks=selection[phase]
    files=['data.py','experiment.py','PROTOCOL.md','small_model.py','local_model.py','SMALL_MODEL_PROTOCOL.md']
    hashes={f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in files}
    if phase=='confirmation':
        assert development is not None
        prior=json.loads((development/'summary.json').read_text());assert prior['development_gate_passed']
        prior_m=json.loads((development/'manifest.json').read_text());assert prior_m['source_sha256']==hashes
    for name,digest in selection['file_sha256'].items():assert hashlib.sha256((CACHE/name).read_bytes()).hexdigest()==digest
    dk,jk=credentials();assert dk and jk
    directory=ROOT/'.local/research/verified-search'/('small-'+phase+'-'+str(time.time_ns()));directory.mkdir(parents=True)
    manifest={'phase':phase,'variant':'qwen3-1.7b','source_sha256':hashes,'selection_sha256':hashlib.sha256((CACHE/'selection.json').read_bytes()).hexdigest(),
        'provider_sha256':hashlib.sha256((ROOT/'research/decoding_control/providers.py').read_bytes()).hexdigest(),
        'task_ids':[t['id'] for t in tasks],'max_calls':len(tasks)*6,'retries':0,'published':False}
    save(directory/'manifest.json',manifest);calls=[];results=[]
    def record(row):
        assert len(calls)<manifest['max_calls']
        i=len(calls);calls.append(row);save(directory/'calls.json',calls);return i
    with LocalServer() as server:
        manifest['local_model']=server.identity;save(directory/'manifest.json',manifest)
        local=LocalGenerator(server);ds=DeepSeekPrefix(dk);jev=jev_client(jk)
        try:
            for ti,task in enumerate(tasks):
                evidence={'question':task['question'],'schema':schema(task['db_id'])};row={'task':task['id'],'db_id':task['db_id'],'candidates':[],'judges':{}}
                for k in range(3):
                    call=local.generate(GENERATOR,evidence,schema=SQL_SCHEMA,limit=1200,temperature=.7,seed=task['index']*11+k+723)
                    call.update(task_id=task['id'],stage='generate',sample=k);idx=record(call)
                    try:
                        assert 'error' not in call and call['finish']=='stop'
                        sql=json.loads(call['text'])['sql'];execution=execute(task['db_id'],sql)
                    except Exception as exc:sql='';execution={'error':'generation_'+type(exc).__name__}
                    row['candidates'].append({'sql':sql,'execution':execution,'call':idx})
                visible,questions,first=pool_view(task,row['candidates'])
                mapping={label:next(i for i,c in enumerate(row['candidates']) if c['sql']==v['sql']) for label,v in visible.items()}
                row.update(mapping=mapping,questions=questions,first_executable=first,majority=majority(row['candidates']))
                judge_state={**evidence,'candidates':visible}
                for provider in (['qwen','jev','deepseek'] if ti%2==0 else ['deepseek','jev','qwen']):
                    jr={'selected':first,'global_selected':first,'call':None}
                    if len(visible)>1:
                        request={'evidence':judge_state,'questions':{key:{'instructions':q['instructions'],'criteria':q['criteria']} for key,q in questions.items()}}
                        if provider in ['qwen','deepseek']:
                            if provider=='qwen':
                                props={key:{'type':'string','enum':list(q['criteria'])} for key,q in questions.items()}
                                shape={'type':'object','properties':{'answers':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}},'required':['answers'],'additionalProperties':False}
                                call=local.generate(DS_JUDGE,request,schema=shape,limit=600,temperature=0,seed=723+task['index'])
                            else:call=ds.generate(DS_JUDGE,json.dumps(request,ensure_ascii=False),limit=600,temperature=0,json_output=True)
                            call.update(task_id=task['id'],stage='judge');jr['call']=record(call)
                            try:
                                assert 'error' not in call and call['finish']=='stop'
                                answers=json.loads(call['text'])['answers'];primary,glob,scores=select(questions,answers,mapping,first)
                                jr.update(answers=answers,selected=primary,global_selected=glob,scores=scores)
                            except Exception as exc:jr['error']=type(exc).__name__
                        else:
                            call={'provider':'jev','task_id':task['id'],'stage':'judge','state':judge_state,'questions':questions};start=time.perf_counter()
                            try:
                                response=jev.system_one(state=judge_state,questions={key:Choice(instructions=q['instructions'],criteria=q['criteria']) for key,q in questions.items()})
                                raw=response.raw_http_response.json();answers={key:a.choice for key,a in response.answers.items()}
                                primary,glob,scores=select(questions,answers,mapping,first)
                                call.update(answers=answers,usage=raw.get('usage',{}),model=raw.get('model'));jr.update(answers=answers,selected=primary,global_selected=glob,scores=scores)
                            except Exception as exc:call['error']=type(exc).__name__;jr['error']=type(exc).__name__
                            call['seconds']=time.perf_counter()-start;jr['call']=record(call)
                    row['judges'][provider]=jr
                for c in row['candidates']:c['evaluation']=evaluate(task,c['sql'])
                results.append(row);save(directory/'results.json',{'manifest':manifest,'results':results})
                print(json.dumps({'task':task['id'],'pool_pass':[c['evaluation']['pass'] for c in row['candidates']],
                    'jev':row['judges']['jev']['selected'],'self':row['judges']['qwen']['selected'],'ds':row['judges']['deepseek']['selected'],
                    'majority':row['majority'],'calls':len(calls)}),flush=True)
            print('Private results:',directory,flush=True)
        finally:local.close();ds.close();jev.close()
    save(directory/'cleanup.json',{'owned_server_exited':server.process.poll() is not None,'exit_code':server.process.poll()})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','confirmation'],default='development');p.add_argument('--development',type=Path);p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.run:run(a.phase,a.development)
    else:print('No calls or model launch. Read SMALL_MODEL_PROTOCOL.md; --run opts in.')
