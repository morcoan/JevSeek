"""Offline accounting and frozen-result verification; no model calls."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.verified_search.data import CACHE,evaluate,execute,normalized
from research.verified_search.experiment import select,majority,pool_view
from research.dynamic_questions.analyze import usage
from research.decoding_control.providers import save


def analyze(directory):
    data=json.loads((directory/'results.json').read_text(encoding='utf-8'));calls=json.loads((directory/'calls.json').read_text(encoding='utf-8'));m=data['manifest']
    for f,sha in m['source_sha256'].items():assert hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest()==sha,f
    assert hashlib.sha256((CACHE/'selection.json').read_bytes()).hexdigest()==m['selection_sha256']
    selection=json.loads((CACHE/'selection.json').read_text(encoding='utf-8'));tasks={t['id']:t for t in selection[m['phase']]}
    small=m.get('variant')=='qwen3-1.7b';self_provider='qwen' if small else 'deepseek'
    providers=['qwen','deepseek','jev'] if small else ['deepseek','jev']
    arms=['direct','first_executable','majority','self_pair','jev_pair','self_global','jev_global','oracle','random_expected']
    if small:arms+=['strong_pair','strong_global']
    outcomes={a:[] for a in arms};bydb={};verified=0;rows=[];total_unique=0;judged=0;timearms={a:[] for a in ['direct','majority','self_pair','jev_pair']}
    for r in data['results']:
        task=tasks[r['task']];passed=[]
        for c in r['candidates']:
            assert evaluate(task,c['sql'])==c['evaluation'];passed.append(c['evaluation']['pass']);verified+=1
            ex=execute(task['db_id'],c['sql'])
            if 'error' not in c['execution']:assert normalized(ex['rows'])==normalized(c['execution']['rows'])
        assert majority(r['candidates'])==r['majority']
        total_unique+=len(r['mapping']);judged+=len(r['mapping'])>1
        for provider,j in r['judges'].items():
            if 'answers' in j:
                choice,glob,scores=select(r['questions'],j['answers'],r['mapping'],r['first_executable'])
                assert (choice,glob,scores)==(j['selected'],j['global_selected'],j['scores'])
        ix={'direct':0,'first_executable':r['first_executable'],'majority':r['majority'],'self_pair':r['judges'][self_provider]['selected'],
            'jev_pair':r['judges']['jev']['selected'],'self_global':r['judges'][self_provider]['global_selected'],'jev_global':r['judges']['jev']['global_selected']}
        if small:ix.update(strong_pair=r['judges']['deepseek']['selected'],strong_global=r['judges']['deepseek']['global_selected'])
        out={a:passed[k] for a,k in ix.items()};out.update(oracle=any(passed),random_expected=sum(passed)/3)
        for a,value in out.items():outcomes[a].append(value)
        bucket=bydb.setdefault(r['db_id'],{'tasks':0,**{a:0 for a in arms}});bucket['tasks']+=1
        for a,value in out.items():bucket[a]+=value
        gen=[calls[c['call']] for c in r['candidates']];gs=sum(c['seconds'] for c in gen)
        timearms['direct'].append(gen[0]['seconds']);timearms['majority'].append(gs)
        for arm,p in [('self_pair',self_provider),('jev_pair','jev')]:
            i=r['judges'][p]['call'];timearms[arm].append(gs+(calls[i]['seconds'] if i is not None else 0))
        rows.append({'task':r['task'],'db_id':r['db_id'],'outcomes':out,'pool_pass':passed,'choices':ix})
    scores={a:sum(v) for a,v in outcomes.items()};paired={}
    for b in ['direct','first_executable','majority','self_pair']+(['strong_pair'] if small else []):
        paired['jev_vs_'+b]={'rescues':sum(a and not x for a,x in zip(outcomes['jev_pair'],outcomes[b])),
                            'regressions':sum(not a and x for a,x in zip(outcomes['jev_pair'],outcomes[b]))}
    summary={'phase':m['phase'],'variant':m.get('variant','deepseek-flash'),'tasks':len(rows),'scores':scores,'paired':paired,'by_database':bydb,'rows':rows,
        'development_gate_passed':scores['jev_pair']>scores['direct'] and scores['jev_pair']>=scores['majority'] and paired['jev_vs_first_executable']['rescues']>=1,
        'total_unique_executable_queries':total_unique,'tasks_judged':judged,
        'provider_errors':sum('error' in c for c in calls),'judge_errors':sum('error' in j for r in data['results'] for j in r['judges'].values()),
        'actual_usage':{p:usage([c for c in calls if c['provider']==p]) for p in providers},
        'nonexecuting_candidates':sum('error' in c['execution'] for r in data['results'] for c in r['candidates']),
        'timing':{a:{'median_serial_seconds':statistics.median(v),'sum_serial_seconds':sum(v)} for a,v in timearms.items()},
        'judge_median_seconds':{p:statistics.median(c['seconds'] for c in calls if c['provider']==p and c['stage']=='judge') if any(c['provider']==p and c['stage']=='judge' for c in calls) else None for p in providers},
        'recomputed_candidates':verified,'source_hashes_match':True,'metric':'row-multiset agreement on originalDB, not official Spider accuracy/test-suite'}
    save(directory/'summary.json',summary);save(Path(__file__).parent/(('small_' if small else '')+m['phase']+'_summary.json'),summary)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();s=analyze(a.directory);print(json.dumps({k:v for k,v in s.items() if k not in ['rows','by_database']},indent=2))
