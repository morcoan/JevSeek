"""Windows controller for local-only benchmark research. No DeepSeek option."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import re
import subprocess
import sys
import time
import tomllib

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.tbench4.vm import ssh_args, remote


def task_profile():
    rows=[]
    for path in sorted((ROOT/'.local/research/terminal-bench-4/tasks').glob('*/task.toml')):
        env=tomllib.loads(path.read_text())['environment'];reasons=[]
        if env.get('cpus',1)>4:reasons.append('more than 4 vCPUs')
        if env.get('memory_mb',1024)>4096:reasons.append('more than 4 GB task RAM')
        if env.get('gpus',0)>0:reasons.append('GPU passthrough required')
        if env.get('mcp_servers'):reasons.append('task MCP not supported by adapter')
        rows.append({'task':path.parent.name,'eligible':not reasons,'reasons':reasons,'cpus':env.get('cpus',1),'memory_mb':env.get('memory_mb',1024),'gpus':env.get('gpus',0)})
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list',action='store_true')
    group.add_argument('--smoke',action='store_true')
    group.add_argument('--task')
    parser.add_argument('--run',action='store_true',help='Explicitly allow local inference and billable Jev calls.')
    parser.add_argument('--port',type=int,default=8080,help='Existing local Prism llama-server port (loopback only).')
    parser.add_argument('--variant',choices=['prism','crack'],help='Require this exact pinned Bonsai variant before inference.')
    args=parser.parse_args()
    if args.list:
        rows=task_profile();print(json.dumps({'downloaded':len(rows),'eligible_in_current_vm':sum(r['eligible'] for r in rows),'tasks':rows},indent=2));return 0
    if not args.run:parser.error('Pass --run to authorize the smoke/task and Jev API costs. No DeepSeek is used.')
    if args.task:
        row=next((r for r in task_profile() if r['task']==args.task),None)
        if row is None or not row['eligible']:raise SystemExit('Unknown task or unsupported resources; run --list. Requirements will not be reduced.')
    if not 1<=args.port<=65535:raise SystemExit('Invalid local port.')
    if remote('test -f /var/lib/jevseek-sandbox-ready && docker info >/dev/null',stdout=subprocess.DEVNULL).returncode:
        raise SystemExit('Start the Linux VM first: python research/tbench4/vm.py start')
    import httpx
    from dotenv import dotenv_values
    from jevseek.bonsai import MODELS
    from jevseek.credentials import CredentialStore
    # Read only what is needed, without exporting .env values into child processes.
    key=os.environ.get('JEV_KET') or os.environ.get('TYPESAFE_API_KEY')
    if not key:
        local=dotenv_values(ROOT/'.env');key=local.get('JEV_KET') or local.get('TYPESAFE_API_KEY');del local
    try:key=CredentialStore().load().get('jev') or key
    except Exception:pass
    if not key:raise SystemExit('Configure a Jev key first. A DeepSeek key is neither required nor forwarded.')
    token=os.environ.get('BONSAI_API_KEY','local-bonsai')
    with httpx.Client(trust_env=False,timeout=10,headers={'Authorization':'Bearer '+token}) as client:
        r=client.get(f'http://127.0.0.1:{args.port}/props');r.raise_for_status();props=r.json()
        path=Path(props.get('model_path',''))
        model=next((m for m in MODELS.values() if m['file']==path.name),None)
        if model is None or props.get('model_alias')!='bonsai':raise SystemExit('The local server is not a recognized requested Bonsai model/alias.')
        if args.variant and model != MODELS[args.variant]:raise SystemExit('Loaded Bonsai variant does not match the explicitly requested variant. No inference started.')
        if not path.is_file() or path.stat().st_size!=model['size']:raise SystemExit('Loaded model path/size could not be verified locally.')
        with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        if digest!=model['sha256']:raise SystemExit('Bonsai model SHA-256 does not match the pinned research model.')
    output=ROOT/'.local/research/runs'/str(time.time_ns());output.mkdir(parents=True)
    base=ssh_args()
    # Reverse forwarding listens only on VM loopback. Task containers cannot use it.
    command=base[:-1]+['-o','ExitOnForwardFailure=yes','-R',f'127.0.0.1:18080:127.0.0.1:{args.port}',base[-1],
                     'cd ~/jevseek-bench && .venv/bin/python -m research.tbench4.guest_run '+('--smoke' if args.smoke else '--task '+shlex.quote(args.task))]
    env={k:v for k,v in os.environ.items() if k.upper()!='JEV_KET' and not any(s in k.upper() for s in ('KEY','TOKEN','SECRET','PASSWORD'))}
    print('Running local Bonsai + Jev only. Jev is billable. One container trial; no cloud sandbox or DeepSeek fallback.',flush=True)
    with (output/'run.log').open('wb') as log:
        result=subprocess.run(command,input=json.dumps({'jev_key':key,'local_key':token}).encode(),env=env,stdout=log,stderr=log)
    manifest={'task':'integration-smoke (NOT Terminal-Bench)' if args.smoke else args.task,'model':model['label'],'model_sha256':digest,'task_dataset_commit':'452bf305c6daa62fc59061d22133a7cbc7c1572e','exit_code':result.returncode,'deepseek_enabled':False,'concurrency':1,'jevresearch_cost_unknown':True,'note':'Verifier results, not CLI exit status or agent completion, determine success. Raw guest results stay in ~/jevseek-bench/jobs.'}
    for line in reversed((output/'run.log').read_text('utf-8',errors='replace').splitlines()):
        try:summary=json.loads(line)
        except ValueError:continue
        if not isinstance(summary,dict) or 'job' not in summary:continue
        name=Path(summary['job']).name
        if summary['job']!='/home/research/jevseek-bench/jobs/'+name or not re.fullmatch(r'[A-Za-z0-9_-]+',name):raise RuntimeError('Unexpected guest job path; refusing to collect it.')
        manifest['result']=summary
        with (output/'harbor-results.tar.gz').open('wb') as archive:
            fetched=remote('cd ~/jevseek-bench/jobs && tar -czf - -- '+shlex.quote(name),stdout=archive,stderr=subprocess.PIPE)
        manifest['raw_results_collected']=fetched.returncode==0
        break
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(f'Run finished with exit code {result.returncode}. Local log: {output / "run.log"}')
    if 'result' in manifest:print(json.dumps(manifest['result'],indent=2))
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
