"""Recompute saved inference results WITHOUT provider calls.
Usage: python research/decoding_control/analyze.py PILOT_DIR GAP_DIR
Raw prompts/queries stay in private directories; this writes aggregate summary.json.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import save
from research.decoding_control.tasks import evaluate
from research.decoding_control.experiment import summarize,usage
from research.decoding_control.gap_diagnostic import choose


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def hashes(manifest):
    for name,digest in manifest['source_sha256'].items():
        assert hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()==digest, name


def main(pilot,gap):
    d=read(pilot/'results.json');calls=read(pilot/'calls.json');hashes(d['manifest'])
    assert len(d['results'])==12 and len(calls)==120
    checked=0;canonical_scores=Counter();same_prefix_different_outcomes=0
    for r in d['results']:
        assert evaluate(r['task'],calls[r['direct_call']]['text'])['pass']==r['scores']['direct'];checked+=1
        stem=calls[r['stem_call']]['text'];tails=[];canonical={}
        for k,block in enumerate(r['blocks']):
            t=calls[block]['text'];canonical[k]=next((j for j in range(k) if calls[r['blocks'][j]]['text']==t),k)
            b=r['branches'][str(k)];ci=b['tail_call'];tail=calls[ci]
            assert tail['prefix']==stem+t
            assert b['sql']==stem+t+tail['text']
            assert evaluate(r['task'],b['sql'])==b['evaluation'];checked+=1;tails.append(ci)
            if canonical[k]!=k and b['evaluation']['pass']!=r['branches'][str(canonical[k])]['evaluation']['pass']:
                same_prefix_different_outcomes+=1
        assert max(r['selectors'].values())<min(tails), 'Future evidence leaked to selectors'
        for arm in ['self','jev','jev_veto']:
            selected=r['selected'][arm]
            canonical_scores[arm]+=r['branches'][str(canonical[selected])]['evaluation']['pass'] if selected is not None else False
    summary=summarize(d['results'],calls);assert summary==d['summary']
    summary.update(recomputed_queries=checked,selection_before_suffix_verified=True,exact_prefix_retention_verified=True,
        canonical_duplicate_outcome_counts=dict(canonical_scores),identical_prefix_changed_suffix_outcomes=same_prefix_different_outcomes,
        all_identical_pools=sum(len(set(calls[i]['text'] for i in r['blocks']))==1 for r in d['results']),
        abstentions={a:sum(r['selected'][a] is None for r in d['results']) for a in ['self','jev']},
        candidate_passes=sum(b['evaluation']['pass'] for r in d['results'] for b in r['branches'].values()),
        stage_seconds={s:{'median':statistics.median(c['seconds'] for c in calls if c['stage']==s),'sum':sum(c['seconds'] for c in calls if c['stage']==s)} for s in sorted({c['stage'] for c in calls})},
        task_scores=[{'task':r['task'],**r['scores']} for r in d['results']])
    gd=read(gap/'results.json');gc=read(gap/'calls.json');hashes(gd['manifest'])
    assert hashlib.sha256((pilot/'results.json').read_bytes()).hexdigest()==gd['manifest']['source_results_sha256']
    assert hashlib.sha256((pilot/'calls.json').read_bytes()).hexdigest()==gd['manifest']['source_calls_sha256']
    followup={'status':'EXPLORATORY_POSTHOC_CACHED_ROLLOUTS_NOT_NEW_END_TO_END_RUN','calls':len(gc),
              'errors':sum('error' in c for c in gc),'usage':usage(gc),'seconds_sum':sum(c['seconds'] for c in gc),
              'seconds_median':statistics.median(c['seconds'] for c in gc),'horizons':{}}
    for h in ['short','lookahead']:
        rs=[r for r in gd['results'] if r['horizon']==h]
        for r in rs:assert choose({int(k):v for k,v in r['scores'].items()})==r['selected']
        followup['horizons'][h]={'scores':{a:sum(r['outcomes'][a] for r in rs) for a in ['first','jev','literal','random_expected','oracle']},
            'selected_changes':sum(r['selected']!=0 for r in rs),'visible_complete_candidates':sum(r['visible_complete'] for r in rs),
            'rescues_vs_first':sum(r['outcomes']['jev'] and not r['outcomes']['first'] for r in rs),
            'regressions_vs_first':sum(r['outcomes']['first'] and not r['outcomes']['jev'] for r in rs)}
    result={'pilot':summary,'diagnostic':followup,'source_sha256':d['manifest']['source_sha256'],
            'interpretation':'No proven Jev-specific performance uplift. Generic prefix selection regressed. A post-hoc narrow-constraint/lookahead signal matched a simple literal baseline; no deployment warranted.'}
    save(Path(__file__).parent/'summary.json',result)
    save(pilot/'validation.json',{'queries_recomputed':checked,'hashes_match':True,'selection_before_suffix':True,'prefix_retention':True})
    print('48 queries re-evaluated unchanged; source hashes, decision-before-suffix and exact prefix retention verified. No inference.')
    print(json.dumps({'canonical_scores':dict(canonical_scores),'identical_prefix_changed_outcomes':same_prefix_different_outcomes,'diagnostic':followup},indent=2))


if __name__=='__main__':main(Path(sys.argv[1]),Path(sys.argv[2]))
