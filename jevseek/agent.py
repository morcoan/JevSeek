"""UI-neutral synchronous JIT loop. An event callback provides the UI boundary."""
from __future__ import annotations

import hashlib
import json
import threading
import uuid
from .context import Context, ContextOverflow, clip, encoded, size
from .models import SUMMARY_SYSTEM


class Agent:
    def __init__(self, session, models, tools, policy=None, instructions='', cancel=None):
        self.session=session; self.models=models; self.tools=tools
        self.context=Context(session,policy); self.instructions=instructions
        self.cancel=cancel or threading.Event()
        self.models.cancel=self.cancel

    def result(self, status, text):
        return {'session_id':self.session.id,'status':status,'summary':self.session.redactor.text(text),
                'session_dir':str(self.session.directory)}

    def run(self, prompt=None, *, compact=False, acknowledge_pending=False):
        """No turn limit. Cancellation is observed between calls, or via Ctrl+C.
        Interrupted in-flight effects require explicit acknowledgement, not replay.
        """
        s=self.session
        with s.lock:
            s.reload()
            if acknowledge_pending: s.acknowledge_pending()
            if s.pending():
                return self.result('needs_input','An earlier tool may have run before interruption. Inspect its effects, then explicitly acknowledge before resuming. It was NOT replayed.')
            if prompt:
                s.append('user',text=prompt)
            elif not any(e['kind']=='user' for e in s.events):
                return self.result('needs_input','Provide a task.')
            elif not compact:
                saved=s.saved_result()
                if saved: return saved
            entries=sorted(p.name for p in s.workspace.iterdir())
            s.append('run_started',model=self.models.settings.model,thinking='disabled',
                     shell_session='existing' if getattr(self.tools,'terminal',None) is not None else 'fresh',
                     workspace_entries={'entries':[clip(name,160) for name in entries[:32]],'total':len(entries),
                                        'truncated':len(entries)>32,
                                        'note':'Factual top-level listing at run start, NOT current after tool execution; not a proposed plan.'})
            last_user=max(e['seq'] for e in s.events if e['kind']=='user')
            try:
                catalog=self.tools.catalog()
                if compact:
                    for audience in ('router','model'): self.context.build(audience,force=True)
                errors=set()
                while True:
                    if self.cancel.is_set():
                        s.append('error',stage='cancelled',error='Cancelled between calls')
                        return self.result('cancelled','Cancelled. Session saved; no pending tool was replayed.')
                    state=self.context.build('router',self.models.route_overhead(catalog))
                    choice, confidence=self.models.route(state,catalog)
                    s.append('route',choice=choice,confidence=confidence,context_bytes=size(state))
                    if confidence < self.models.settings.confidence_floor: choice='ask'
                    if choice in ('done','ask'):
                        status='completed' if choice=='done' else 'needs_input'
                        latest=next((e for e in reversed(s.events) if e['kind'] in ('tool_finished','tool_uncertain') and e['seq']>last_user),None)
                        if latest and (latest['kind']=='tool_uncertain' or latest['data'].get('status') in ('error','running')):
                            status='needs_input'
                        state=self.context.build('model',size([SUMMARY_SYSTEM,self.instructions])+1024)
                        text=self.models.summary(state,status,self.instructions)
                        s.append('final',status=status,summary=text)
                        return self.result(status,text)
                    if choice not in catalog: raise ValueError('Router selected unavailable tool')
                    schema=self.tools.schemas[choice]
                    state=self.context.build('model',self.models.argument_overhead(schema,self.instructions))
                    args=self.models.arguments(state,choice,schema,self.instructions)
                    if self.cancel.is_set():
                        s.append('error',stage='cancelled',error='Cancelled before execution')
                        return self.result('cancelled','Cancelled before executing tool. Session saved.')
                    call_id=uuid.uuid4().hex
                    target=str(args.get('path',args.get('command',args.get('tool_slug',''))))
                    request,_=s.artifact(call_id+'-request',args,{'text':''})
                    s.append('tool_started',call_id=call_id,tool=choice,target=clip(target,1000),request=request)
                    # No retry wrapper around side effects. Only the models may be retried.
                    try:
                        observation=self.tools.execute(choice,args)
                    except Exception as exc:
                        observation={'text':f'{type(exc).__name__}: {exc}','is_error':True,'exit_code':None}
                    target=observation.get('target') or target
                    artifact,output=s.artifact(call_id,args,observation)
                    code=observation.get('exit_code')
                    status=('running' if observation.get('still_running') else
                            'error' if observation.get('is_error') or (code is not None and code!=0) else 'ok')
                    s.append('tool_finished',call_id=call_id,tool=choice,target=clip(target,1000),status=status,
                             exit_code=code,view_range=args.get('view_range'),
                             text=clip(observation.get('text',''),self.context.policy.result_chars),
                             arguments={'actual_argument_preview':clip(encoded(args),self.context.policy.result_chars)},
                             artifact=artifact,full_output=output)
                    if status=='error':
                        fingerprint=hashlib.sha256(encoded([choice,args,observation.get('text','')]).encode()).hexdigest()
                        if fingerprint in errors:
                            s.append('final',status='needs_input',summary='The same tool arguments failed repeatedly. Inspect the saved error/inputs before retrying; no success was assumed.')
                            return self.result('needs_input',s.events[-1]['data']['summary'])
                        errors.add(fingerprint)
            except (Exception,KeyboardInterrupt) as exc:
                # Keep provider credentials and possibly secret-bearing validation data out of diagnostics.
                kind='cancelled' if isinstance(exc,KeyboardInterrupt) else 'blocked'
                s.append('error',stage=kind,error=type(exc).__name__,message=clip(str(exc),2000))
                text=f'{type(exc).__name__}: run stopped; session saved. '
                if isinstance(exc,ContextOverflow): text+=str(exc)+' '
                if s.pending(): text+='A tool may have executed; inspect it before acknowledging interruption.'
                else: text+='Retry/resume after resolving the error; no side effect will be replayed automatically.'
                return self.result(kind,text)

    def close(self):
        for resource in (self.tools,self.models):
            try: resource.close()
            except Exception as exc:
                self.session.transient('cleanup_warning',error=type(exc).__name__)
