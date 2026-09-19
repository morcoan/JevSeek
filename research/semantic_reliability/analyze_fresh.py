from __future__ import annotations
import argparse,hashlib,itertools,json,statistics
from math import comb
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import save
from research.dynamic_questions.analyze import usage
from research.semantic_constraints.tasks import evaluate,visible
from research.semantic_constraints.experiment import solve_labels
from research.semantic_reliability.fresh_tasks import tasks,fingerprint
from research.semantic_reliability.fresh import make_queries

def analyze(path):
 d=json.loads((path/'results.json').read_text(encoding='utf-8'));calls=json.loads((path/'calls.json').read_text(encoding='utf-8'));m=d['manifest'];ts={t['id']:t for t in tasks()}
 for f,h in m['source_sha256'].items():assert hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest()==h
 assert fingerprint()==m['fixture_sha256'];arms=['legacy','revised_global','focused'];scores={a:0 for a in arms};feasible={a:0 for a in arms};edges={a:{'correct':0,'fp':0,'fn':0,'unknown':0,'total':0} for a in arms};outs={a:[] for a in arms};bydomain={};timings={a:[] for a in arms};verified=0
 for r in d['results']:
  t=ts[r['task']];assert r['visible']==visible(t)
  costs=[sum(t['hosts'][h]['cost'] for h in p) for p in itertools.permutations(t['hosts'],5) if all(t['truth_matrix'][j+'_'+h] for j,h in zip(t['jobs'],p))];assert min(costs)==t['oracle']['cost']
  group=bydomain.setdefault(t['domain'],{a:0 for a in arms})
  for a,v in r['arms'].items():
   assert evaluate(t,v['assignment'])==v['evaluation'];found,cost,_=solve_labels(t,v['answers']);assert found==v['assignment'] and cost==v['cost'];verified+=1
   scores[a]+=v['evaluation']['optimal'];feasible[a]+=v['evaluation']['feasible'];outs[a].append(v['evaluation']['optimal']);group[a]+=v['evaluation']['optimal']
   c=calls[v['call']] if v['call'] is not None else None;timings[a].append((c['seconds'] if c else 0)+v['solver_seconds'])
   if a=='focused':
    for q in make_queries(t):assert v['judgments'][q.id]['fingerprint']==q.fingerprint('jev-1.13.0','focused')
   for k,label in v['answers'].items():
    actual=t['truth_matrix'][k];pred=label=='eligible';s=edges[a];s['total']+=1;s['correct']+=pred==actual and label!='unknown';s['fp']+=pred and not actual;s['fn']+=not pred and actual;s['unknown']+=label=='unknown'
 paired={}
 for b in ['legacy','revised_global']:
  wins=sum(a and not z for a,z in zip(outs['focused'],outs[b]));losses=sum(not a and z for a,z in zip(outs['focused'],outs[b]));n=wins+losses
  paired['focused_vs_'+b]={'rescues':wins,'regressions':losses,'descriptive_sign_p':min(1.,2*sum(comb(n,i) for i in range(min(wins,losses)+1))/2**n) if n else 1.}
 out={'cases':len(d['results']),'optimal':scores,'feasible':feasible,'by_domain':bydomain,'edges':edges,'paired':paired,
      'usage':{a:usage([c for c in calls if c['arm']==a]) for a in arms},'median_call_solver_seconds':{a:statistics.median(v) for a,v in timings.items()},
      'calls':len(calls),'errors':sum('error' in c for c in calls),'assignments_recomputed':verified,'hashes_and_fingerprints_verified':True,
      'scope':'48fresh synthetic cases in3vocabularies, SAME Boolean/matching generator; not external real-world validation.'}
 save(path/'summary.json',out);save(Path(__file__).parent/'fresh_summary.json',out);return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args();print(json.dumps(analyze(a.path),indent=2))
