"""Offline reproduction, payload checks and accounting for typed sketches."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.verified_search.data import CACHE,evaluate
from research.verified_search.sketch import slots,resolve,RECIPES
from research.dynamic_questions.analyze import usage
from research.decoding_control.providers import save


def analyze(directory):
    data=json.loads((directory/'results.json').read_text(encoding='utf-8'));calls=json.loads((directory/'calls.json').read_text(encoding='utf-8'));m=data['manifest']
    for f,sha in m['source_sha256'].items():assert hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest()==sha,f
    assert hashlib.sha256((CACHE/'selection.json').read_bytes()).hexdigest()==m['selection_sha256']
    sel=json.loads((CACHE/'selection.json').read_text(encoding='utf-8'));tasks={t['id']:t for t in sel[m['phase']]}
    arms=['plain','all_recipes','self_sketch','jev_sketch','strong_sketch'];outs={a:[] for a in arms};timings={a:[] for a in arms};deployed={a:[] for a in arms};bydb={};rows=[];verified=0;interpreters_failed=0
    for r in data['results']:
        task=tasks[r['task']];state,qs,vocab=slots(task)
        assert json.loads(json.dumps(state))==r['state'];assert qs==r['questions'];assert vocab==r['vocabulary']
        assert set(state)=={'question','schema'}
        for p,ir in r['interpreters'].items():
            interpreters_failed+='error' in ir
            if ir['sketch'] is not None:assert resolve(ir['answers'],qs,vocab)==ir['sketch']
            c=calls[ir['call']]
            payload=c['state'] if p=='jev' else (json.loads(c['task']) if p=='deepseek' else c['payload'])['evidence']
            assert payload==r['state']
        out={}
        for a,ar in r['arms'].items():
            assert evaluate(task,ar['sql'])==ar['evaluation'];verified+=1;out[a]=ar['evaluation']['pass']
            c=calls[ar['call']];assert c['payload']['evidence']==r['state'];seq=[c]
            if a in ['self_sketch','jev_sketch','strong_sketch']:
                p={'self_sketch':'qwen','jev_sketch':'jev','strong_sketch':'deepseek'}[a];ir=r['interpreters'][p]
                assert c['payload'].get('semantic_interpretation')==ir['sketch'];seq.append(calls[ir['call']])
            elif a=='all_recipes':assert c['payload']['generic_recipes']==RECIPES
            else:assert set(c['payload'])=={'evidence'}
            timings[a].append(sum(x['seconds'] for x in seq));deployed[a]+=seq
        for a,v in out.items():outs[a].append(v)
        bucket=bydb.setdefault(r['db_id'],{'tasks':0,**{a:0 for a in arms}});bucket['tasks']+=1
        for a,v in out.items():bucket[a]+=v
        rows.append({'task':r['task'],'db_id':r['db_id'],'outcomes':out})
    scores={a:sum(v) for a,v in outs.items()};paired={}
    from math import comb
    for b in ['plain','all_recipes','self_sketch','strong_sketch']:
        rescue=sum(a and not x for a,x in zip(outs['jev_sketch'],outs[b]));regress=sum(not a and x for a,x in zip(outs['jev_sketch'],outs[b]));n=rescue+regress
        p=min(1.,2*sum(comb(n,i) for i in range(min(rescue,regress)+1))/2**n) if n else 1.
        paired['jev_vs_'+b]={'rescues':rescue,'regressions':regress,'two_sided_sign_p_descriptive_only':p}
    providers=['qwen','deepseek','jev']
    summary={'phase':m['phase'],'variant':'typed_sketch','tasks':len(rows),'scores':scores,'paired':paired,'by_database':bydb,'rows':rows,
        'development_gate_passed':scores['jev_sketch']>scores['plain'] and scores['jev_sketch']>scores['all_recipes'] and scores['jev_sketch']>=scores['self_sketch'],
        'provider_errors':sum('error' in c for c in calls),'interpretation_errors':interpreters_failed,
        'actual_usage':{p:usage([c for c in calls if c['provider']==p]) for p in providers},
        'deployed_usage':{a:{p:usage([c for c in deployed[a] if c['provider']==p]) for p in providers} for a in arms},
        'timing':{a:{'median_serial_seconds':statistics.median(v),'sum_serial_seconds':sum(v)} for a,v in timings.items()},
        'interpreter_median_seconds':{p:statistics.median(c['seconds'] for c in calls if c['provider']==p and c['stage']=='interpret') for p in providers},
        'recomputed_queries':verified,'source_hashes_match':True,'matched_inputs_and_resolved_sketches_verified':True,
        'metric':'column-ordered row-multiset agreement on original publicDB; not official Spider accuracy',
        'statistics_warning':'Paired sign tests descriptive: tiny clusteredDB sample and multiple comparisons; no general significance claim.'}
    save(directory/'summary.json',summary);save(Path(__file__).parent/('sketch_'+m['phase']+'_summary.json'),summary)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();s=analyze(a.directory);print(json.dumps({k:v for k,v in s.items() if k not in ['rows','by_database','deployed_usage']},indent=2))
