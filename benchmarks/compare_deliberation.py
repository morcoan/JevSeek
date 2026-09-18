"""Flash 4.1: native max reasoning vs Jev-gated external deliberation.
The JIT router NEVER sees drafts. Shared evaluator and tools across all arms.
Usage: python benchmarks/compare_deliberation.py native|synthetic|synthetic_v2|plain
No turn/deliberation cap. V2 halts on repeated drafts/missing evidence, not forced enough.
Ctrl+C cancels; partial traces are not successes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from openai import OpenAI
from typesafe_sdk import Choice, TypeSafeClient
from compare_routing import BASE, FIXTURE, TOOLS, SCHEMAS, SYSTEM
from openhands.tools.file_editor import FileEditorAction
from openhands.tools.file_editor.impl import FileEditorExecutor

MODEL = 'deepseek-flash'
ROUTER_QUESTION = ('Select the next single tool using user intent and actual completed turns, not model plans. '
                   'Choose done only when implementation is complete and independent acceptance tests have passed.')
DRAFT_SYSTEM = ('Prepare a working analysis for generating arguments for the ALREADY SELECTED tool. '
                'You cannot select another tool or execute anything. Inspect the user requirements and actual observations. '
                'Give a concrete proposed solution/argument sketch, edge cases, and any unresolved issue. '
                'For simple read/test calls a short concrete argument sketch is enough. Do not invent evidence or '
                'claim unrun tests passed. If asked to continue, improve the draft rather than repeat it. '
                'These notes are advisory and will be consumed by a separate JSON argument-generation call.')
GATE_QUESTION = ('Does the latest working draft still leave a material issue that another deliberation pass '
                 'using the SAME available evidence could resolve before generating the selected tool arguments? '
                 'Judge coverage and consistency yourself, not the draft author claiming to be ready. '
                 'Do not require results of tools that have not run yet. This is a readiness decision, not proof of correctness.')
GATE_OPTIONS = {'continue': 'Yes: further analysis can address a concrete omission, contradiction or unresolved implementation detail.',
                'enough': 'No: enough to generate arguments and obtain real tool feedback; more prose is not necessary.'}


V2_QUESTION = ('Evaluate ONLY latest_draft for readiness to generate arguments for selected_tool. '
               'The next DeepSeek call will produce the complete JSON/code; a concrete design is enough here, '
               'so do not require full code or JSON in this advisory draft. Choose enough if the available '
               'evidence and design permit that generation. Choose a gap only for a specific defect fixable '
               'from the current evidence. Unrun tests are not a design gap. If essential facts are missing '
               'and only another tool/user could provide them, choose needs_evidence. Ignore the draft author claiming readiness.')
V2_OPTIONS = {
    'enough': 'Ready to generate the selected tool arguments now and obtain real execution feedback.',
    'schema_gap': 'The proposed action contradicts the selected tool schema or uses the wrong operation.',
    'design_gap': 'A concrete required behavior has no design yet and can be resolved from the supplied specification/source.',
    'contradiction': 'The proposed design contradicts supplied source, requirements, or actual observations.',
    'needs_evidence': 'An essential fact is unavailable; further drafting cannot supply it. Halt for observation or clarification.'}

class DeliberationStalled(RuntimeError):
    pass

class DeliberationNeedsEvidence(RuntimeError):
    pass

class DraftProgress:
    """Detect exact repeats/cycles ignoring whitespace. Does not detect paraphrases."""
    def __init__(self):
        self.seen = set()

    def observe(self, draft):
        key = hashlib.sha256(' '.join(draft.split()).encode()).hexdigest()
        if key in self.seen:
            raise DeliberationStalled('Repeated draft without new tool evidence')
        self.seen.add(key)


def request_options(mode, stage):
    native = mode == 'native' and stage == 'arguments'
    return {'model': MODEL, 'reasoning_effort': 'max' if native else 'none',
            'max_tokens': 131072,
            'extra_body': {'thinking': {'type': 'enabled' if native else 'disabled'}}}


def route_state(task, history):
    # Deliberation and gate decisions deliberately have no path into this state.
    return {'user_intent': task, 'completed_turns': history}


class Run:
    def __init__(self, mode):
        self.mode=mode
        self.dest=BASE/'deliberation_results'/f'{mode}-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}'
        self.work=self.dest/'workspace'; self.work.mkdir(parents=True)
        for n in ['engine.py','SPEC.md','test_public.py']: shutil.copy(FIXTURE/n,self.work/n)
        (self.work/'acceptance.py').write_text(f'import runpy\nrunpy.run_path({str(FIXTURE / "acceptance_suite.py")!r}, run_name="__main__")\n')
        self.task=('Complete engine.py according to this specification. Initial files: engine.py (unfinished), '
                   'SPEC.md, test_public.py, acceptance.py.\n'+(FIXTURE/'SPEC.md').read_text())
        self.history=[]; self.metrics=[]; self.started=time.perf_counter()
        self.ds=OpenAI(api_key=os.environ['DS_KEY'],base_url=os.getenv('LLM_BASE_URL','https://api.deepseek.com/v1'),timeout=240,max_retries=0)
        self.jev=TypeSafeClient(api_key=os.getenv('JEV_KET') or os.getenv('TYPESAFE_API_KEY'),model='jev-1.13.0')
        self.editor=FileEditorExecutor(workspace_root=str(self.work.resolve()))
        self.messages=[{'role':'system','content':SYSTEM},{'role':'user','content':self.task}]
        self.event('config',mode=mode,model=MODEL,options=request_options(mode,'arguments'),
                   fixture_hashes={n:hashlib.sha256((FIXTURE/n).read_bytes()).hexdigest() for n in ['engine.py','SPEC.md','test_public.py','acceptance_suite.py']},
                   router_question=ROUTER_QUESTION,draft_system=DRAFT_SYSTEM,
                   gate_question=V2_QUESTION if mode=='synthetic_v2' else GATE_QUESTION,
                   gate_options=V2_OPTIONS if mode=='synthetic_v2' else GATE_OPTIONS)

    def event(self,kind,**data):
        with (self.dest/'events.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps({'kind':kind,**data},ensure_ascii=False)+'\n')

    def choose(self,stage,state,question,criteria):
        t=time.perf_counter()
        response=self.jev.system_one(state=state,questions={'decision':Choice(instructions=question,criteria=criteria)})
        raw=response.raw_http_response.json()
        m={'provider':'jev','stage':stage,'seconds':time.perf_counter()-t,'response':raw}
        self.metrics.append(m); self.event('jev',**m)
        return response.answers['decision'].choice

    def completion(self,stage,messages,json_mode=False):
        opts=request_options(self.mode,stage)
        if json_mode: opts['response_format']={'type':'json_object'}
        self.event('request',stage=stage,options=opts,messages=messages)
        t=time.perf_counter()
        r=self.ds.chat.completions.create(messages=messages,**opts)
        choice=r.choices[0]; msg=choice.message
        reasoning=getattr(msg,'reasoning_content',None) or ''
        m={'provider':'deepseek','stage':stage,'seconds':time.perf_counter()-t,
           'model':r.model,'fingerprint':r.system_fingerprint,'usage':r.usage.model_dump(),
           'finish_reason':choice.finish_reason,'native_reasoning_chars':len(reasoning)}
        self.metrics.append(m); self.event('deepseek',**m,content=msg.content)
        if choice.finish_reason != 'stop': raise RuntimeError(f'Incomplete {stage}: {choice.finish_reason}')
        if not msg.content: raise RuntimeError(f'Empty {stage} output')
        if self.mode!='native' and reasoning: raise RuntimeError('Non-thinking request unexpectedly returned native reasoning')
        return msg.content

    def arguments(self,tool):
        prompt=f'Jev selected {tool}. Supply its arguments only. Schema: {json.dumps(SCHEMAS[tool])}'
        self.messages.append({'role':'user','content':prompt})
        extras=[]
        if self.mode in ('synthetic', 'synthetic_v2'):
            drafts=[]
            progress=DraftProgress()
            working=[{'role':'system','content':DRAFT_SYSTEM},
                     {'role':'user','content':json.dumps({'user_intent':self.task,'actual_turns':self.history,
                                                        'selected_tool':tool,'schema':SCHEMAS[tool]})}]
            while True:
                draft=self.completion('draft',working)
                drafts.append(draft); working.append({'role':'assistant','content':draft})
                if self.mode=='synthetic_v2':
                    progress.observe(draft)
                    gate=self.choose('gate',{'user_intent':self.task,'actual_turns':self.history,
                                            'selected_tool':tool,'schema':SCHEMAS[tool],'latest_draft':draft},V2_QUESTION,V2_OPTIONS)
                else:
                    gate=self.choose('gate',{'user_intent':self.task,'actual_turns':self.history,
                                            'selected_tool':tool,'schema':SCHEMAS[tool],'working_drafts':drafts},GATE_QUESTION,GATE_OPTIONS)
                self.event('gate',tool=tool,round=len(drafts),decision=gate)
                print(self.mode,'draft',len(drafts),gate,flush=True)
                if gate=='enough': break
                if gate=='needs_evidence':
                    raise DeliberationNeedsEvidence('Gate requests evidence unavailable from further drafting')
                feedback=('The independent readiness gate requested another pass. Re-examine the selected tool arguments, address concrete gaps, and produce an improved draft. No new execution evidence is available.')
                if self.mode=='synthetic_v2':
                    feedback=f'Fix the identified gap: {gate}: {V2_OPTIONS[gate]}. Produce a revised complete argument-design sketch. Do not invent new evidence.'
                working.append({'role':'user','content':feedback})
            advisory=[drafts[-1]] if self.mode=='synthetic_v2' else drafts
            extras=[{'role':'user','content':'Advisory working drafts (not executed evidence):\n'+json.dumps(advisory)+'\nNow output ONLY the selected tool argument JSON.'}]
        text=self.completion('arguments',self.messages+extras,True)
        # Only final arguments and real observations persist across tool turns.
        self.messages.append({'role':'assistant','content':text})
        return text

    def execute(self,tool,p):
        if tool=='bash':
            allowed={'python acceptance.py':[sys.executable,'acceptance.py'],
                     'python -m unittest -v test_public.py':[sys.executable,'-m','unittest','-v','test_public.py']}
            r=subprocess.run(allowed[p['command']],cwd=self.work,capture_output=True,text=True,timeout=120)
            return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
        path=(self.work/p['path']).resolve()
        if not path.is_relative_to(self.work.resolve()): raise ValueError('Outside workspace')
        if tool!='read' and (path.name in ['SPEC.md','test_public.py','acceptance.py'] or (path.exists() and path.name!='engine.py')):
            raise ValueError('Read-only evaluator file')
        kw={'command':{'read':'view','write':'create','edit':'str_replace'}[tool],'path':str(path)}
        if tool=='write': kw['file_text']=p['content']
        if tool=='edit': kw.update(old_str=p['old'],new_str=p['new'])
        return self.editor(FileEditorAction(**kw)).model_dump(mode='json')

    def run(self):
        error=None
        try:
            while True:
                tool=self.choose('router',route_state(self.task,self.history),ROUTER_QUESTION,
                                 {**TOOLS,'done':'All requested work is complete, verified by passing acceptance tests.'})
                print(self.mode,'turn',len(self.history)+1,tool,flush=True)
                if tool=='done': break
                text=self.arguments(tool)
                try:
                    args=json.loads(text); observation=self.execute(tool,args)
                except Exception as exc:
                    args={'raw':text}; observation={'error':f'{type(exc).__name__}: {exc}'}
                turn={'tool':tool,'arguments':args,'observation':observation}
                self.history.append(turn); self.event('turn',**turn)
                self.messages.append({'role':'user','content':'Actual tool observation:\n'+json.dumps(observation)})
        except (Exception,KeyboardInterrupt) as exc:
            error=type(exc).__name__
            self.event('interrupted',error=error)
        verdict=subprocess.run([sys.executable,'acceptance.py'],cwd=self.work,capture_output=True,text=True,timeout=120)
        output=verdict.stdout+verdict.stderr
        (self.dest/'acceptance.txt').write_text(output,encoding='utf-8')
        unchanged=all((self.work/n).read_bytes()==(FIXTURE/n).read_bytes() for n in ['SPEC.md','test_public.py'])
        summary=None
        if error is None:
            try:
                summary=self.completion('summary',[{'role':'system','content':'Summarize only observed execution and test results. No proposed code or tool calls; report failures honestly.'},
                                                   {'role':'user','content':json.dumps({'user_intent':self.task,'actual_turns':self.history,'final_verification':output})}])
            except Exception as exc:
                error=type(exc).__name__
                self.event('summary_failed',error=error)
        result={'mode':self.mode,'model':MODEL,'pass':verdict.returncode==0 and unchanged and error is None,
                'artifact_pass':verdict.returncode==0 and unchanged,'error':error,
                'seconds':time.perf_counter()-self.started,'tool_turns':len(self.history),'fixture_integrity':unchanged,
                'metrics':self.metrics,'summary':summary}
        (self.dest/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('RESULT',self.dest,json.dumps({k:v for k,v in result.items() if k not in ('metrics','summary')}),flush=True)
        self.ds.close(); self.jev.close()
        return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['native','synthetic','synthetic_v2','plain'])
    Run(parser.parse_args().mode).run()
