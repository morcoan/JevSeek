"""Run each resource-eligible task once, sequentially, with CRACK + Jev only.

A STOP file in the sweep directory stops scheduling after the current task.
Interrupted sweeps are never automatically replayed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tomllib

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from filelock import FileLock
from research.tbench4.run import task_profile
from research.tbench4.vm import remote


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    rows=task_profile();tasks=[r['task'] for r in rows if r['eligible']]
    if not args.run:
        print(json.dumps({'variant':'crack','deepseek':False,'tasks':tasks,'count':len(tasks)},indent=2));return 0
    if len(rows)!=66 or len(tasks)!=33:raise SystemExit('Dataset/resource profile changed; review before launching.')
    home=ROOT/'.local/research/sweeps';home.mkdir(parents=True,exist_ok=True)
    with FileLock(str(home/'active.lock'),timeout=0):
        output=home/str(time.time_ns());output.mkdir()
        state={'status':'running','variant':'crack','providers':['bonsai','jev'],'deepseek_enabled':False,'concurrency':1,'attempts_per_task':1,'total':len(tasks),'tasks':tasks,'excluded':[r for r in rows if not r['eligible']],'completed':[],'current':None,'started_at':time.time()}
        def save():
            temp=output/'status.tmp';temp.write_text(json.dumps(state,indent=2),'utf-8');temp.replace(output/'status.json')
        save();print('Sweep directory: '+str(output),flush=True)
        try:
            for task in tasks:
                if (output/'STOP').exists():state['status']='stopped_before_next_task';break
                if shutil.disk_usage(ROOT).free<20*1024**3:raise RuntimeError('Host disk reserve reached; scheduling stopped.')
                check=remote("docker info >/dev/null && test -z \"$(docker ps -q)\" && df -B1 --output=avail / | tail -1",capture_output=True,text=True,timeout=35)
                if check.returncode:raise RuntimeError('VM unavailable or another container is active; scheduling stopped.')
                config=tomllib.loads((ROOT/'.local/research/terminal-bench-4/tasks'/task/'task.toml').read_text())
                needed=(config['environment'].get('storage_mb',10240)+5120)*1024**2
                if int(check.stdout.strip())<needed:raise RuntimeError('Guest disk reserve insufficient for next task; scheduling stopped without pruning evidence.')
                state['current']=task;save();print('Starting '+task,flush=True)
                before={p.name for p in (ROOT/'.local/research/runs').iterdir()}
                with (output/(task+'.log')).open('wb') as log:
                    result=subprocess.run([sys.executable,'-u',str(ROOT/'research/tbench4/run.py'),'--task',task,'--variant','crack','--run'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                new=[p for p in (ROOT/'.local/research/runs').iterdir() if p.name not in before and (p/'manifest.json').exists()]
                if len(new)!=1:raise RuntimeError('Controller failed before an unambiguous result was saved; inspect task log before resuming.')
                manifest=json.loads((new[0]/'manifest.json').read_text())
                if manifest.get('task')!=task:raise RuntimeError('Unexpected task result; stop for inspection.')
                state['completed'].append({'task':task,'controller_exit':result.returncode,'run_directory':str(new[0]),'result':manifest.get('result')})
                state['current']=None;save()
                if result.returncode:raise RuntimeError('Controller returned an error; inspect before scheduling further tasks.')
            else:state['status']='finished'
        except BaseException as exc:
            state['status']='paused_error';state['error']=str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__
        finally:
            state['updated_at']=time.time();save();print(json.dumps({'status':state['status'],'completed':len(state['completed']),'directory':str(output)}),flush=True)
        return 0 if state['status']=='finished' else 2


if __name__=='__main__':raise SystemExit(main())
