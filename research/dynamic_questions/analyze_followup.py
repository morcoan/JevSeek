"""Recompute the exploratory scaffolding diagnostic without further inference."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.dynamic_questions.tasks import TASKS,evaluate
from research.dynamic_questions.analyze import usage
from research.decoding_control.providers import save


def analyze(directory,source):
    data=json.loads((directory/'results.json').read_text());calls=json.loads((directory/'calls.json').read_text())
    oldcalls=json.loads((source/'calls.json').read_text());oldresults=json.loads((source/'results.json').read_text())
    assert len(data['results'])==16
    for name,digest in data['manifest']['source_sha256'].items():assert hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()==digest,name
    assert hashlib.sha256((source/'results.json').read_bytes()).hexdigest()==data['manifest']['source_results_sha256']
    assert hashlib.sha256((source/'calls.json').read_bytes()).hexdigest()==data['manifest']['source_calls_sha256']
    arms=['direct','questions_only','questions_ds','questions_jev'];outcomes={a:[] for a in arms};per={a:[] for a in arms};armcalls={a:[] for a in arms}
    verified=0;disagreements=[];nquestions=0;unknown={'ds':0,'jev':0}
    for t,r,old in zip(TASKS,data['results'],oldresults['results']):
        assert t['id']==r['task']==old['task']
        state=r['shared_state'];qs=r.get('questions',[]);nquestions+=len(qs)
        baseline=evaluate(t,t['candidates'][r['original_direct_patch']]);assert baseline==r['original_direct_evaluation'];verified+=1;outcomes['direct'].append(baseline['pass'])
        before=[oldcalls[r['original_read_call']],oldcalls[r['original_patch_call']]]
        armcalls['direct']+=before;per['direct'].append(sum(c['seconds'] for c in before))
        for a,ar in r['arms'].items():
            if ar.get('patch') in t['candidates']:assert evaluate(t,t['candidates'][ar['patch']])==ar['evaluation'];verified+=1
            outcomes[a].append(ar['evaluation']['pass'])
            rows=[oldcalls[r['original_read_call']]]+[c for c in calls if c['task_id']==t['id'] and (c['stage']=='question_author' or c in [calls[i] for i in ar['calls']])]
            armcalls[a]+=rows;per[a].append(sum(c['seconds'] for c in rows))
            for idx in ar['calls']:
                c=calls[idx];payload=c['payload'] if c['provider']=='jev' else json.loads(c['task'])
                assert payload['evidence']==state and payload['questions']==qs
                if c['stage'].endswith('_choose'):
                    assert payload.get('assessments')==ar.get('answers')
        da=r['arms']['questions_ds'].get('answers',{});ja=r['arms']['questions_jev'].get('answers',{})
        unknown['ds']+=sum(v=='unknown' for v in da.values());unknown['jev']+=sum(v=='unknown' for v in ja.values())
        for q in qs:
            if da.get(q['id'])!=ja.get(q['id']):disagreements.append({'task':t['id'],'question':q['id'],'ds':da.get(q['id']),'jev':ja.get(q['id'])})
    pairs={}
    for a,b in [('questions_jev','direct'),('questions_ds','direct'),('questions_only','direct'),('questions_jev','questions_ds'),('questions_jev','questions_only')]:
        pairs[a+'_vs_'+b]={'rescues':sum(x and not y for x,y in zip(outcomes[a],outcomes[b])),'regressions':sum(not x and y for x,y in zip(outcomes[a],outcomes[b]))}
    summary={'kind':'posthoc_same_cases_shared_evidence_diagnostic','tasks':16,'scores':{a:sum(outcomes[a]) for a in arms},'paired':pairs,
       'generated_questions':nquestions,'unknown_answers':unknown,'answer_disagreements':disagreements,
       'invalid_question_lists':sum('questions_error' in r for r in data['results']),
       'valid_question_subset':{'tasks':sum('questions' in r for r in data['results']),
           'direct':sum(r['original_direct_evaluation']['pass'] for r in data['results'] if 'questions' in r),
           **{a:sum(r['arms'][a]['evaluation']['pass'] for r in data['results'] if 'questions' in r) for a in arms[1:]}},
       'maximum_question_author_seconds':max(c['seconds'] for c in calls if c['stage']=='question_author'),
       'arm_errors':{a:sum('error' in r['arms'][a] for r in data['results']) for a in arms[1:]},
       'timing':{a:{'median_serial_seconds':statistics.median(per[a]),'sum_serial_seconds':sum(per[a])} for a in arms},
       'deployed_arm_usage':{a:{p:usage([c for c in armcalls[a] if c['provider']==p]) for p in ['deepseek','jev']} for a in arms},
       'actual_followup_usage':{p:usage([c for c in calls if c['provider']==p]) for p in ['deepseek','jev']},
       'stage_median_seconds':{s:statistics.median(c['seconds'] for c in calls if c['stage']==s) for s in sorted({c['stage'] for c in calls})},
       'api_errors':sum('error' in c for c in calls),'recomputed_repairs':verified,'source_hashes_match':True,'matched_question_evidence_inputs':True,
       'scope':'Exploratory follow-up on same16easy closed-world cases; not independent/full coding/weak-model validation. Questions generated once per patch decision, not persistent-program reuse.'}
    save(directory/'summary.json',summary);save(Path(__file__).parent/'followup_summary.json',summary)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('source',type=Path);a=p.parse_args();print(json.dumps(analyze(a.directory,a.source),indent=2))
