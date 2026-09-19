from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import save
from research.semantic_constraints.tasks import all_tasks,evaluate
from research.semantic_constraints.experiment import solve_labels

def analyze(path):
 d=json.loads((path/'results.json').read_text(encoding='utf-8'));cs=json.loads((path/'calls.json').read_text(encoding='utf-8'));ts={t['id']:t for t in all_tasks()}
 for f,h in d['manifest']['source_sha256'].items():assert hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest()==h
 stats={a:{'optimal':0,'feasible':0,'correct_edges':0,'false_positive':0,'false_negative':0,'unknown':0,'regressions':0} for a in ['historical','focused','dual']}
 for r in d['results']:
  t=ts[r['task']]
  for a,v in r['arms'].items():
   assert evaluate(t,v['assignment'])==v['evaluation']
   found,cost,_=solve_labels(t,v['answers']);assert found==v['assignment']
   s=stats[a];s['optimal']+=v['evaluation']['optimal'];s['feasible']+=v['evaluation']['feasible'];s['regressions']+=r['arms']['historical']['evaluation']['optimal'] and not v['evaluation']['optimal']
   for k,label in v['answers'].items():
    expected=t['truth_matrix'][k];actual=label=='eligible'
    s['correct_edges']+=actual==expected and label!='unknown';s['false_positive']+=actual and not expected;s['false_negative']+=not actual and expected;s['unknown']+=label=='unknown'
 selected=next((a for a in ['focused','dual'] if stats[a]['optimal']==len(d['results']) and stats[a]['regressions']==0),None)
 out={'kind':'known_case_diagnostic_NOT_holdout','tasks':len(d['results']),'stats':stats,'selected_policy':selected,'new_jev_calls':len(cs),'errors':sum('error' in c for c in cs),'source_hashes_match':True,'assignments_recomputed':len(d['results'])*3}
 save(path/'summary.json',out);save(Path(__file__).parent/'diagnostic_summary.json',out);return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args();print(json.dumps(analyze(a.path),indent=2))
