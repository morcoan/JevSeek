"""Posthoc evidence-scope diagnosis; not a new heldout sample."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import credentials,jev_client,save
from research.semantic_constraints.tasks import all_tasks,evaluate,visible
from research.semantic_constraints.experiment import solve_labels
from research.semantic_reliability.runtime import Evidence,Query,ScopedEvaluator

SOURCE=ROOT/'.local/research/semantic-constraints/confirmation-1789810188726523200/results.json'


def queries_for(t):
    return [Query(j+'_'+h,'This candidate host satisfies the ENTIRE following requirement: '+requirement,
                   (Evidence('host:'+h,record['profile']),)) for j,requirement in t['jobs'].items() for h,record in t['hosts'].items()]


def mapped(judgments):return {k:'eligible' if v['truth']=='supported' else 'ineligible' if v['truth']=='refuted' else 'unknown' for k,v in judgments.items()}


def run():
    tasks=[t for t in all_tasks() if t['id'] in {'confirmation-'+str(97000+i) for i in range(12)}]
    original=json.loads(SOURCE.read_text(encoding='utf-8'));baseline={r['task']:r for r in original['results']}
    _,key=credentials();assert key
    directory=ROOT/'.local/research/semantic-reliability'/('diagnostic-'+str(time.time_ns()));directory.mkdir(parents=True)
    manifest={'kind':'posthoc_known_cases','source_sha256':{f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in ['runtime.py','diagnostic.py','DIAGNOSTIC_PROTOCOL.md']},
              'baseline_results_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'task_ids':[t['id'] for t in tasks],'max_requests':24}
    save(directory/'manifest.json',manifest);calls=[];rows=[];client=jev_client(key);evaluator=ScopedEvaluator(client)
    try:
        for ti,t in enumerate(tasks):
            row={'task':t['id'],'arms':{'historical':baseline[t['id']]['arms']['jev_solver']},'visible':visible(t)}
            for mode in (['focused','dual'] if ti%2==0 else ['dual','focused']):
                results,call=evaluator.assess(queries_for(t),mode);assert call is not None
                call['task_id']=t['id'];idx=len(calls);assert idx<24;calls.append(call);save(directory/'calls.json',calls)
                labels=mapped(results);found,cost,seconds=solve_labels(t,labels)
                row['arms'][mode]={'judgments':results,'answers':labels,'assignment':found,'predicted_cost':cost,'solver_seconds':seconds,'call':idx}
            for arm in row['arms'].values():arm['evaluation']=evaluate(t,arm['assignment'])
            rows.append(row);save(directory/'results.json',{'manifest':manifest,'results':rows})
            print(json.dumps({'task':t['id'],'optimal':{a:r['evaluation']['optimal'] for a,r in row['arms'].items()}}),flush=True)
    finally:client.close()
    print('Private diagnostic:',directory,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.run:run()
    else:print('No calls. Read DIAGNOSTIC_PROTOCOL.md; --run opts into24requests maximum.')
