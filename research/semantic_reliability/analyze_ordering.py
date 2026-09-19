from __future__ import annotations
import argparse,hashlib,json,statistics
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import save
from research.dynamic_questions.analyze import usage
from research.semantic_reliability.ordering import DATA,selection,parse,specs,solve

def analyze(path):
 d=json.loads((path/'results.json').read_text(encoding='utf-8'));calls=json.loads((path/'calls.json').read_text(encoding='utf-8'));m=d['manifest']
 for f,h in m['source_sha256'].items():assert hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest()==h
 assert hashlib.sha256((DATA/'ordering-selection.json').read_bytes()).hexdigest()==m['selection_sha256']
 ts={t['id']:t for t in selection()[m['phase']]};arms=['qwen_direct','jev_direct','jev_compiler','ds_compiler'];scores={a:0 for a in arms};abstain={a:0 for a in arms};outs={a:[] for a in arms};timing={a:[] for a in arms};by_size={};proofs=0
 for r in d['results']:
  t=ts[r['task']];context,rules,opts=parse(t['input']);qs,_=specs(context,rules,opts);bucket=by_size.setdefault(str(t['size']),{'tasks':0,**{a:0 for a in arms}});bucket['tasks']+=1
  for a,v in r['arms'].items():
   assert v['correct']==(v['choice']==t['target']);scores[a]+=v['correct'];bucket[a]+=v['correct'];abstain[a]+=v['choice'] is None;outs[a].append(v['correct'])
   c=calls[v['call']];timing[a].append(c['seconds']+v.get('solver_seconds',0))
   if 'answers' in v:assert solve(context,rules,opts,v['answers'])==v['solver'];proofs+=1
   if a=='qwen_direct':assert c['payload']=={'problem':t['input']}
   elif a=='jev_direct':assert c['state']=={'problem':t['input']}
   elif a=='jev_compiler':assert c['questions']==qs
   else:assert json.loads(c['task'])=={'questions':qs}
 paired={}
 for b in ['qwen_direct','jev_direct','ds_compiler']:
  paired['jev_compiler_vs_'+b]={'rescues':sum(a and not z for a,z in zip(outs['jev_compiler'],outs[b])),'regressions':sum(not a and z for a,z in zip(outs['jev_compiler'],outs[b]))}
 n=len(d['results']);out={'phase':m['phase'],'tasks':n,'scores':scores,'abstentions':abstain,'by_size':by_size,'paired':paired,
    'development_gate_passed':scores['jev_compiler']>=10 and (scores['jev_compiler']>scores['qwen_direct'] or scores['qwen_direct']==n),
    'actual_usage':{p:usage([c for c in calls if c['provider']==p]) for p in ['qwen','jev','deepseek']},
    'arm_median_call_solver_seconds':{a:statistics.median(v) for a,v in timing.items()},'errors':sum('error' in c for c in calls),
    'conditional_certificates_recomputed':proofs,'inputs_hashes_verified':True,'scope':'External public synthetic BBH ordering; conditional proof assumes correct semantic translation, not a general language-proof guarantee.'}
 save(path/'summary.json',out);save(Path(__file__).parent/('ordering_'+m['phase']+'_summary.json'),out);return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args();print(json.dumps(analyze(a.path),indent=2))
