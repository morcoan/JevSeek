"""Owned research-only Qwen3-1.7B server. No app preferences or other servers touched."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import requests

ROOT=Path(__file__).resolve().parents[2]
MODEL_REVISION='90862c4b9d2787eaed51d12237eafdfe7c5f6077'
MODEL_NAME='Qwen3-1.7B-Q8_0.gguf'
MODEL_SHA256='061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a'
MODEL_SIZE=1834426016
MODEL_DIR=ROOT/'.local/research/verified-search/model'
RUNTIME=ROOT/'.jevseek/bonsai-validation/bonsai/runtime-cuda/llama-server.exe'


def model_file():
    target=MODEL_DIR/MODEL_NAME;MODEL_DIR.mkdir(parents=True,exist_ok=True)
    if not target.exists():
        part=target.with_suffix('.part');part.unlink(missing_ok=True)
        url=f'https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/{MODEL_REVISION}/{MODEL_NAME}'
        with requests.get(url,stream=True,timeout=(30,120)) as response:
            response.raise_for_status();count=0;checkpoint=0
            with part.open('wb') as output:
                for chunk in response.iter_content(8*1024*1024):
                    output.write(chunk);count+=len(chunk)
                    if count-checkpoint>=128*1024*1024:
                        print(json.dumps({'downloaded_bytes':count,'expected_bytes':MODEL_SIZE}),flush=True);checkpoint=count
        assert part.stat().st_size==MODEL_SIZE
        with part.open('rb') as downloaded:
            assert hashlib.file_digest(downloaded,'sha256').hexdigest()==MODEL_SHA256
        part.replace(target)
    with target.open('rb') as source:digest=hashlib.file_digest(source,'sha256').hexdigest()
    assert target.stat().st_size==MODEL_SIZE and digest==MODEL_SHA256
    return target


class LocalServer:
    def __init__(self):self.process=None;self.job=None;self.log=None;self.token=secrets.token_urlsafe(32)
    def __enter__(self):
        import win32job
        import win32api
        import win32con
        model=model_file();assert RUNTIME.is_file()
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        self.url=f'http://127.0.0.1:{port}/v1'
        env={k:v for k,v in os.environ.items() if not k.upper().startswith('LLAMA_ARG_') and k.upper()!='JEV_KET' and not any(x in k.upper() for x in ['KEY','TOKEN','SECRET','PASSWORD'])}
        self.log=(MODEL_DIR/('server-'+str(time.time_ns())+'.log')).open('wb')
        cmd=[str(RUNTIME),'-m',str(model),'--host','127.0.0.1','--port',str(port),'--api-key',self.token,'--alias','qwen3-1.7b-research',
             '-c','16384','-np','1','-ngl','auto','--reasoning','off','--chat-template-kwargs','{"enable_thinking":false}','--no-webui']
        self.process=subprocess.Popen(cmd,cwd=RUNTIME.parent,env=env,stdin=subprocess.DEVNULL,stdout=self.log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        try:
            self.job=win32job.CreateJobObject(None,'');limits=win32job.QueryInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation)
            limits['BasicLimitInformation']['LimitFlags']|=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation,limits)
            handle=win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS,False,self.process.pid)
            try:win32job.AssignProcessToJobObject(self.job,handle)
            finally:handle.Close()
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                if self.process.poll() is not None:raise RuntimeError('Owned model server exited during startup')
                try:
                    r=requests.get(f'http://127.0.0.1:{port}/health',headers={'Authorization':'Bearer '+self.token},timeout=2)
                    if r.status_code==200:break
                except requests.RequestException:pass
                time.sleep(.5)
            else:raise TimeoutError('Owned model startup timeout')
            self.identity={'model_repository':'Qwen/Qwen3-1.7B-GGUF','model_revision':MODEL_REVISION,'model_file':MODEL_NAME,'model_sha256':MODEL_SHA256,
                           'runtime_exe_sha256':hashlib.sha256(RUNTIME.read_bytes()).hexdigest(),'thinking':False,'context_tokens':16384,'pid':self.process.pid}
            print(json.dumps({'owned_model_ready':True,'pid':self.process.pid,'model':MODEL_NAME}),flush=True)
            return self
        except BaseException:self.__exit__(None,None,None);raise
    def __exit__(self,*args):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=10)
        if self.job:self.job.Close();self.job=None
        if self.log:self.log.close();self.log=None


class LocalGenerator:
    def __init__(self,server):
        from openai import OpenAI
        import httpx
        self.client=OpenAI(api_key=server.token,base_url=server.url,timeout=180,max_retries=0,http_client=httpx.Client(trust_env=False))
    def generate(self,system,payload,*,schema,limit=1200,temperature=.7,seed=0):
        row={'provider':'qwen','stage':'generate','system':system,'payload':payload,'limit':limit,'temperature':temperature,'seed':seed};start=time.perf_counter()
        try:
            response=self.client.chat.completions.create(model='qwen3-1.7b-research',messages=[{'role':'system','content':system},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],
                max_tokens=limit,temperature=temperature,seed=seed,top_p=.8,
                response_format={'type':'json_schema','json_schema':{'name':'research_response','strict':True,'schema':schema}},
                extra_body={'chat_template_kwargs':{'enable_thinking':False}})
            choice=response.choices[0];message=choice.message
            row.update(text=message.content or '',finish=choice.finish_reason,usage=response.usage.model_dump() if response.usage else {},model=response.model)
            if getattr(message,'reasoning_content',None):raise ValueError('Unexpected reasoning trace')
        except Exception as exc:row['error']=type(exc).__name__
        row['seconds']=time.perf_counter()-start;return row
    def close(self):self.client.close()

if __name__=='__main__':model_file();print('Pinned model downloaded and SHA-256 verified; no server started.')
