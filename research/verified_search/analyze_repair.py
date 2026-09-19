"""Offline verification/accounting for one-pass corrective guidance."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.verified_search.data import CACHE,evaluate
from research.verified_search.repair import FACETS,visible_state,validate_answers
from research.dynamic_questions.analyze import usage
from research.decoding_control.providers import save


def analyze(directory):
    data=json.loads((directory/'results.json').read_text(encoding='utf-8'));calls=json.loads((directory/'calls.json').read_text(encoding='utf-8'));m=data['manifest']
    for f,sha in m['source_sha256'].items():assert hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest()==sha,f
    assert hashlib.sha256((CACHE/'selection.json').read_bytes()).hexdigest()==m['selection_sha256']
    sel=json.loads((CACHE/'selection.json').read_text(encoding='utf-8'));tasks={t['id']:t for t in sel[m['phase']]}
    arms=['direct','plain','all_hints','self_guided','jev_guided','strong_guided'];outs={a:[] for a in arms};timearms={a:[] for a in arms};deployed={a:[] for a in arms}
    bydb={};rows=[];verified=0;flags={p:{k:0 for k in FACETS} for p in ['qwen','jev','deepseek']};different=0;critic_errors=0
    for r in data['results']:
        task=tasks[r['task']];base=r['original'];out={'direct':base['evaluation']['pass']}
        assert evaluate(task,base['sql'])==base['evaluation'];verified+=1
        assert json.loads(json.dumps(visible_state(task,base['sql'],base['execution'])))==r['state']
        basecall=r['original_generation'];timearms['direct'].append(basecall['seconds']);deployed['direct'].append(basecall)
        for p,cr in r['critics'].items():
            critic_errors+='error' in cr
            if cr['answers'] is not None:
                validate_answers(cr['answers'])
                for k,v in cr['answers'].items():flags[p][k]+=v=='fix'
        ja=r['critics']['jev']['answers'];sa=r['critics']['qwen']['answers']
        if ja and sa:different+=sum(ja[k]!=sa[k] for k in FACETS)
        for a,ar in r['arms'].items():
            assert evaluate(task,ar['sql'])==ar['evaluation'];verified+=1;out[a]=ar['evaluation']['pass']
            c=calls[ar['call']];payload=c['payload'];assert payload['evidence']==r['state']
            sequence=[basecall,c]
            if a in ['self_guided','jev_guided','strong_guided']:
                p={'self_guided':'qwen','jev_guided':'jev','strong_guided':'deepseek'}[a];cr=r['critics'][p]
                sequence.append(calls[cr['call']])
                expected={k:{'status':status,'meaning':FACETS[k]} for k,status in cr['answers'].items()} if cr['answers'] else None
                assert payload.get('assessments')==expected
            elif a=='all_hints':assert payload['checklist']==FACETS
            else:assert set(payload)=={'evidence'}
            deployed[a]+=sequence;timearms[a].append(sum(x['seconds'] for x in sequence))
        for a,v in out.items():outs[a].append(v)
        bucket=bydb.setdefault(r['db_id'],{'tasks':0,**{a:0 for a in arms}});bucket['tasks']+=1
        for a,v in out.items():bucket[a]+=v
        rows.append({'task':r['task'],'db_id':r['db_id'],'outcomes':out})
    scores={a:sum(v) for a,v in outs.items()};paired={}
    for b in ['direct','plain','all_hints','self_guided','strong_guided']:
        paired['jev_vs_'+b]={'rescues':sum(a and not x for a,x in zip(outs['jev_guided'],outs[b])),
                            'regressions':sum(not a and x for a,x in zip(outs['jev_guided'],outs[b]))}
    providers=['qwen','deepseek','jev']
    summary={'phase':m['phase'],'variant':'corrective_guidance','tasks':len(rows),'scores':scores,'paired':paired,'by_database':bydb,'rows':rows,
        'development_gate_passed':scores['jev_guided']>scores['direct'] and scores['jev_guided']>scores['plain'] and scores['jev_guided']>=scores['all_hints'] and scores['jev_guided']>=scores['self_guided'],
        'fix_labels':flags,'jev_self_label_disagreements':different,'provider_errors':sum('error' in c for c in calls),'critic_errors':critic_errors,
        'actual_usage':{p:usage([c for c in calls if c['provider']==p]) for p in providers},
        'deployed_usage':{a:{p:usage([c for c in deployed[a] if c['provider']==p]) for p in providers} for a in arms},
        'timing':{a:{'median_serial_seconds':statistics.median(v),'sum_serial_seconds':sum(v)} for a,v in timearms.items()},
        'critic_median_seconds':{p:statistics.median(c['seconds'] for c in calls if c['provider']==p and c['stage']=='critic') for p in providers},
        'recomputed_queries':verified,'source_hashes_match':True,'matched_payloads_verified':True,
        'metric':'column-ordered row-multiset agreement on original publicDB, not official Spider score'}
    save(directory/'summary.json',summary);save(Path(__file__).parent/('repair_'+m['phase']+'_summary.json'),summary)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();s=analyze(a.directory);print(json.dumps({k:v for k,v in s.items() if k not in ['rows','by_database','deployed_usage']},indent=2))
