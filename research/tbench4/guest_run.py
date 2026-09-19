"""Linux-side entry point. Receives Jev credentials on SSH stdin, never argv/files."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import time
import tomllib


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    targets=parser.add_mutually_exclusive_group(required=True)
    targets.add_argument('--smoke',action='store_true')
    targets.add_argument('--task')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.smoke:task=root/'research/tbench4/smoke'
    else:
        if not args.task or Path(args.task).name!=args.task or args.task in ('.','..'):raise SystemExit('Use one exact local task directory name.')
        task=root/'terminal-bench-4/tasks'/args.task
    config=tomllib.loads((task/'task.toml').read_text())
    resources=config.get('environment',{})
    if resources.get('cpus',1)>4 or resources.get('memory_mb',1024)>4096 or resources.get('gpus',0)>0 or resources.get('mcp_servers'):
        raise SystemExit('Task exceeds this VM profile or needs unsupported GPU/MCP resources. Its requirements were NOT reduced.')
    # Clear any ambient cloud-provider credentials before importing orchestration.
    for key in list(os.environ):
        if any(word in key.upper() for word in ('KEY','TOKEN','PASSWORD','SECRET')) or key in ('JEV_KET','LLM_BASE_URL','LLM_MODEL'):
            os.environ.pop(key,None)
    os.environ.update(HARBOR_TELEMETRY='off',DO_NOT_TRACK='1',HF_HUB_DISABLE_TELEMETRY='1',LITELLM_LOCAL_MODEL_COST_MAP='True',BONSAI_BASE_URL='http://127.0.0.1:18080/v1')
    import sys
    request=json.loads(sys.stdin.read(16384))
    from research.tbench4.agent import configure_credentials
    configure_credentials(request.pop('jev_key'),request.pop('local_key','local-bonsai'))
    if request:raise SystemExit('Unexpected credential-channel fields.')
    # Credentials live only in the external agent's private memory, not Docker's
    # environment, task files, serialized Harbor config or child shell arguments.
    from harbor.cli.main import app
    name=('smoke' if args.smoke else args.task)+'-'+str(time.time_ns())
    app(args=['run','--path',str(task),'--agent','research.tbench4.agent:JevSeekBonsaiAgent','--model','bonsai','--env','docker','--n-concurrent','1','--n-attempts','1','--max-retries','0','--jobs-dir',str(root/'jobs'),'--job-name',name],standalone_mode=False)
    job=root/'jobs'/name
    providers=set()
    for path in job.rglob('events.jsonl'):
        for line in path.read_text().splitlines():
            event=json.loads(line)
            if event['kind']=='usage':providers.add(event['data']['provider'])
    if providers-{'bonsai','jev'}:raise RuntimeError('Forbidden provider in recorded usage.')
    trials=[json.loads(p.read_text()) for p in job.glob('*/result.json')]
    rewards=[(t.get('verifier_result') or {}).get('rewards') for t in trials]
    errors=sum(bool(t.get('exception_info')) for t in trials)
    print(json.dumps({'job':str(job),'usage_providers':sorted(providers),'smoke_not_benchmark_score':args.smoke,'deepseek_enabled':False,'verifier_rewards':rewards,'trial_errors':errors}))
    if args.smoke and (errors or rewards!=[{'reward':1.0}]):raise SystemExit('Integration smoke did not pass its real verifier.')


if __name__=='__main__':main()
