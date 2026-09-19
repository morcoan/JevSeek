"""Independent offline truth/assignment checks; no inference."""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
from math import comb
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.semantic_constraints.tasks import all_tasks,visible,evaluate,preflight
from research.semantic_constraints.experiment import solve_labels
from research.dynamic_questions.analyze import usage
from research.decoding_control.providers import save


def analyze(directory):
    data=json.loads((directory/'results.json').read_text(encoding='utf-8'));calls=json.loads((directory/'calls.json').read_text(encoding='utf-8'));m=data['manifest']
    for f,sha in m['source_sha256'].items():assert hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest()==sha,f
    assert preflight()['fixture_sha256']==m['fixture_sha256']
    tasks={t['id']:t for t in all_tasks() if t['split']==m['phase']}
    arms=['direct','qwen_solver','jev_solver','strong_solver','solver_without_semantics'];scores={a:0 for a in arms};feasible={a:0 for a in arms};outcomes={a:[] for a in arms};timings={a:[] for a in arms};rows=[];verified=0
    edge={a:{'total':0,'correct':0,'false_positive':0,'false_negative':0,'unknown':0} for a in arms if a.endswith('_solver')}
    for r in data['results']:
        t=tasks[r['task']];assert r['state']==visible(t)
        # Independent list/min formulation, not the solver under test.
        feasible_costs=[sum(t['hosts'][h]['cost'] for h in chosen) for chosen in itertools.permutations(t['hosts'],len(t['jobs']))
                        if all(t['truth_matrix'][j+'_'+h] for j,h in zip(t['jobs'],chosen))]
        assert feasible_costs and min(feasible_costs)==t['oracle']['cost']
        rr={'task':t['id'],'optimal_cost':t['oracle']['cost'],'outcomes':{}}
        for a,ar in r['arms'].items():
            assert evaluate(t,ar['assignment'])==ar['evaluation'];verified+=1
            ev=ar['evaluation'];scores[a]+=ev['optimal'];feasible[a]+=ev['feasible'];outcomes[a].append(ev['optimal']);rr['outcomes'][a]=ev
            if ar['call'] is not None:
                c=calls[ar['call']]
                if c['provider']=='jev':payload=c['state']
                elif c['provider']=='deepseek':payload=json.loads(c['task'])['evidence']
                elif c['stage']=='direct':payload=c['payload']
                else:payload=c['payload']['evidence']
                assert payload==visible(t)
                timings[a].append(c['seconds']+(0 if c['provider']=='jev' else ar['solver_seconds']))
            else:timings[a].append(ar['solver_seconds'])
            if 'answers' in ar:
                found,cost,_=solve_labels(t,ar['answers']);assert found==ar['assignment'] and cost==ar['predicted_cost']
                for key,label in ar['answers'].items():
                    pred=label=='eligible';actual=t['truth_matrix'][key];e=edge[a];e['total']+=1;e['correct']+=pred==actual and label!='unknown'
                    e['false_positive']+=pred and not actual;e['false_negative']+=not pred and actual;e['unknown']+=label=='unknown'
        rows.append(rr)
    paired={}
    for b in ['direct','qwen_solver','strong_solver','solver_without_semantics']:
        rescue=sum(a and not x for a,x in zip(outcomes['jev_solver'],outcomes[b]));regress=sum(not a and x for a,x in zip(outcomes['jev_solver'],outcomes[b]));n=rescue+regress
        p=min(1.,2*sum(comb(n,i) for i in range(min(rescue,regress)+1))/2**n) if n else 1.
        paired['jev_vs_'+b]={'rescues':rescue,'regressions':regress,'sign_p_descriptive':p}
    summary={'phase':m['phase'],'tasks':len(rows),'optimal_scores':scores,'feasible_scores':feasible,'paired':paired,'edge_accuracy':edge,'rows':rows,
        'development_gate_passed':scores['jev_solver']>scores['direct'] and scores['jev_solver']>scores['solver_without_semantics'] and scores['jev_solver']>=scores['qwen_solver'],
        'actual_usage':{p:usage([c for c in calls if c['provider']==p]) for p in ['qwen','deepseek','jev']},
        'timing':{a:{'median_call_plus_solver_seconds':statistics.median(v),'sum_seconds':sum(v)} for a,v in timings.items()},
        'provider_errors':sum('error' in c for c in calls),'arm_errors':sum('error' in a for r in data['results'] for a in r['arms'].values()),
        'recomputed_assignments':verified,'independent_reference_cost_check':True,'source_fixture_hashes_match':True,'visible_only_payloads_verified':True,
        'scope':'Synthetic6capability/Booleanrequirement placement tasks; exact solver included; domain-limited system augmentation, not general intelligence.'}
    save(directory/'summary.json',summary);save(Path(__file__).parent/(m['phase']+'_summary.json'),summary)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();s=analyze(a.directory);print(json.dumps({k:v for k,v in s.items() if k!='rows'},indent=2))
