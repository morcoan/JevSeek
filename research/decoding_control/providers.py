"""Research-only prefix interface. No application runtime imports except key storage.
Transport-specific prefix flags live here, not in the steering algorithm.
Other endpoints must implement/validate assistant-prefix continuation explicitly.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def credentials():
    from dotenv import dotenv_values
    from jevseek.credentials import CredentialStore
    env={**dotenv_values(ROOT/'.env'),**os.environ}
    store=CredentialStore();vault=store.load() if store.supported else {}
    return (vault.get('deepseek') or env.get('DS_KEY') or env.get('DEEPSEEK_API_KEY') or env.get('LLM_API_KEY'),
            vault.get('jev') or env.get('JEV_KET') or env.get('TYPESAFE_API_KEY'))


def save(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(path)


class DeepSeekPrefix:
    def __init__(self,key,model='deepseek-flash'):
        from openai import OpenAI
        self.client=OpenAI(api_key=key,base_url='https://api.deepseek.com/beta',timeout=90,max_retries=0)
        self.model=model
    def generate(self,system,task,prefix='',limit=512,temperature=.4,logprobs=False,json_output=False):
        messages=[{'role':'system','content':system},{'role':'user','content':task}]
        if prefix:messages.append({'role':'assistant','content':prefix,'prefix':True})
        row={'provider':'deepseek','requested_model':self.model,'system':system,'task':task,'prefix':prefix,
             'limit':limit,'temperature':temperature,'logprobs_requested':logprobs,'json_output':json_output}
        start=time.perf_counter()
        try:
            response=self.client.chat.completions.create(model=self.model,messages=messages,max_tokens=limit,
                temperature=temperature,reasoning_effort='none',extra_body={'thinking':{'type':'disabled'}},
                logprobs=logprobs,**({'top_logprobs':5} if logprobs else {}),
                **({'response_format':{'type':'json_object'}} if json_output else {}))
            choice=response.choices[0];msg=choice.message
            row.update(model=response.model,finish=choice.finish_reason,usage=response.usage.model_dump() if response.usage else {},
                       text=msg.content or '')
            if choice.logprobs:row['logprobs']=choice.logprobs.model_dump()
            if getattr(msg,'reasoning_content',None):raise ValueError('Unexpected thinking output')
            if choice.finish_reason not in {'length','stop'}:raise ValueError('Unusable finish reason')
        except Exception as exc:row['error']=type(exc).__name__
        row['seconds']=time.perf_counter()-start
        return row
    def close(self):self.client.close()


def jev_client(key):
    from typesafe_sdk import TypeSafeClient,RetryPolicy
    return TypeSafeClient(api_key=key,model='jev-1.13.0',timeout=30,retry=RetryPolicy(max_retries=0))
