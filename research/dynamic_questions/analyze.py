"""Offline result verification and aggregate accounting; no provider calls."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.dynamic_questions.tasks import TASKS,evaluate
from research.dynamic_questions.experiment import initial,after_read,check_graph,decide,questions
from research.decoding_control.providers import save


def usage(rows):
    out={'input':0,'output':0,'cache_hit':0,'seconds':sum(r['seconds'] for r in rows),'calls':len(rows)}
    for r in rows:
        u=r.get('usage',{})
        out['input']+=u.get('prompt_tokens',u.get('input_tokens',0))
        out['output']+=u.get('completion_tokens',u.get('output_tokens',0))
        out['cache_hit']+=u.get('prompt_cache_hit_tokens',0)
    return out


def analyze(directory):
    data=json.loads((directory/'results.json').read_text());calls=json.loads((directory/'calls.json').read_text())
    assert len(data['results'])==len(TASKS)==16
    for name,digest in data['manifest']['source_sha256'].items():
        assert hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()==digest,name
    assert hashlib.sha256((ROOT/'research/decoding_control/providers.py').read_bytes()).hexdigest()==data['manifest']['provider_source_sha256']
    bytask={t['id']:t for t in TASKS};arms=['direct','ds_program','jev_program','compiler_fallback'];verified=0;nodecounts=[];unknowns={a:0 for a in arms};evaluations={a:0 for a in arms}
    for r in data['results']:
        t=bytask[r['task']];state=initial(t)
        if 'graph' in r:
            check_graph(r['graph'],state)
            nodecounts.append(sum(len(r['graph'][p]['nodes']) for p in ['read','patch']))
        for arm,ar in r['arms'].items():
            if ar.get('patch') in t['candidates']:
                assert evaluate(t,t['candidates'][ar['patch']])==ar['evaluation'];verified+=1
            if arm in ['ds_program','jev_program'] and 'graph' in r:
                current=state
                for step in ar['steps']:
                    phase=step['phase'];answers=step['answers'];actions=list(state['available_files']) if phase=='read' else [*t['candidates'],'abstain']
                    action,scores=decide(r['graph'][phase],answers,actions)
                    assert action==step['action'] and scores==step['scores']
                    unknowns[arm]+=sum(v=='unknown' for v in answers.values());evaluations[arm]+=len(answers)
                    if phase=='read':current=after_read(t,state,action)
        # Actual tool observations/DS and Jev question inputs must be reproducible.
        for arm in ['ds_program','jev_program','direct']:
            ar=r['arms'][arm];current=state
            for step,idx in zip(ar['steps'],ar['calls']):
                c=calls[idx];payload=c['payload'] if c['provider']=='jev' else json.loads(c['task'])
                assert payload['evidence']==current
                if arm!='direct':assert payload['questions']==questions(r['graph'][step['phase']])
                if step['phase']=='read':current=after_read(t,state,step['action'])
    scores={a:sum(r['arms'][a]['evaluation']['pass'] for r in data['results']) for a in arms}
    pairs={}
    for a,b in [('jev_program','direct'),('jev_program','ds_program'),('ds_program','direct'),('jev_program','compiler_fallback')]:
        pairs[a+'_vs_'+b]={'rescues':sum(r['arms'][a]['evaluation']['pass'] and not r['arms'][b]['evaluation']['pass'] for r in data['results']),
                         'regressions':sum(not r['arms'][a]['evaluation']['pass'] and r['arms'][b]['evaluation']['pass'] for r in data['results'])}
    timings={};tokens={}
    for arm in arms:
        per=[];allrows=[]
        for r in data['results']:
            tc=[c for c in calls if c['task_id']==r['task']]
            if arm=='direct':selected=[c for c in tc if c['stage'].startswith('direct_')]
            elif arm=='compiler_fallback':selected=[c for c in tc if c['stage']=='compile']
            else:
                prefix='ds_evaluate_' if arm=='ds_program' else 'jev_evaluate_'
                selected=[c for c in tc if c['stage']=='compile' or c['stage'].startswith(prefix)]
            allrows+=selected;per.append(sum(c['seconds'] for c in selected))
        timings[arm]={'sum_serial_seconds':sum(per),'median_serial_seconds':statistics.median(per)}
        tokens[arm]={p:usage([c for c in allrows if c['provider']==p]) for p in ['deepseek','jev']}
    graph_valid=[r for r in data['results'] if 'graph' in r]
    valid_scores={a:sum(r['arms'][a]['evaluation']['pass'] for r in graph_valid) for a in arms}
    summary={'tasks':16,'hidden_cases':sum(len(t['tests']) for t in TASKS),'scores':scores,'paired':pairs,
             'valid_graphs':len(graph_valid),'valid_graph_subset_scores':valid_scores,'compiled_nodes':sum(nodecounts),'unknown_answers':unknowns,'node_evaluations':evaluations,
             'median_nodes_valid_graph':statistics.median(nodecounts) if nodecounts else None,
             'relevant_reads':{a:sum(r['arms'][a].get('read_file')==bytask[r['task']]['relevant'] for r in data['results']) for a in arms[:3]},
             'arm_errors':{a:sum('error' in r['arms'][a] for r in data['results']) for a in arms},
             'timing':timings,'deployed_arm_usage':tokens,
             'actual_research_usage':{p:usage([c for c in calls if c['provider']==p]) for p in ['deepseek','jev']},
             'stage_median_seconds':{s:statistics.median(c['seconds'] for c in calls if c['stage']==s) for s in sorted({c['stage'] for c in calls})},
             'api_errors':sum('error' in c for c in calls),'recomputed_repairs':verified,
             'source_hashes_match':True,'tool_observations_and_policy_votes_verified':True,
             'scope':'Small closed-world owned patch-selection pilot; not open-ended coding or a weak-model test. Compilation included; failed programs counted. No retries.'}
    save(directory/'summary.json',summary);save(Path(__file__).parent/'summary.json',summary)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();print(json.dumps(analyze(a.directory),indent=2))
