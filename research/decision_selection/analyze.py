"""Recompute a recorded pilot locally, without making provider requests.
Usage: python research/decision_selection/analyze.py PRIVATE_RUN_DIRECTORY
Writes only a credential-free aggregate here; raw prompts stay private.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.decision_selection.tasks import evaluate
from research.decision_selection.experiment import summarize,save


def main(directory):
    data=json.loads((directory/'results.json').read_text(encoding='utf-8'))
    calls=json.loads((directory/'calls.json').read_text(encoding='utf-8'))
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    for name,digest in manifest['source_sha256'].items():
        assert hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()==digest, 'Source changed since run'
    rows=data['results'];assert len(rows)==12 and len(calls)==84
    for r in rows:
        for arm in ['direct','first','self','jev']:
            final=r['arm_calls'][arm][-1]
            got=evaluate(r['task'],final.get('output',{}).get('sql'))['pass'] if final['stage'] in {'direct','conditioned_final'} else False
            assert got==r['scores'][arm], 'Saved metric mismatch'
    summary=summarize(rows,calls);assert summary==data['summary']
    summary.update(source_sha256=manifest['source_sha256'],requested_generator=manifest['generator'],requested_selector=manifest['selector'],
        returned_models=sorted({c.get('model') for c in calls if c.get('model')}),
        stage_seconds={stage:{'median':statistics.median(c['seconds'] for c in calls if c['stage']==stage),
                              'total':sum(c['seconds'] for c in calls if c['stage']==stage)} for stage in sorted({c['stage'] for c in calls})},
        selector_disagreements=sum(r['self']!=r['jev'] for r in rows),
        task_scores=[{'task':r['task'],**r['scores']} for r in rows],
        interpretation='12 hand-authored tasks, one sample each; no demonstrated Jev accuracy gain over same-pool self-selection. Latencies are counterfactual stage sums; oracle uses observed completions, not intrinsic plan validity.')
    save(Path(__file__).parent/'summary.json',summary)
    print('Recorded sources match; all 48 selected/direct outputs recomputed with unchanged results. No provider calls. Aggregate written.')


if __name__=='__main__':main(Path(sys.argv[1]))
