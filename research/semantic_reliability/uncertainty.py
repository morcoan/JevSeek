from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import credentials,jev_client,save
from research.semantic_reliability.runtime import Evidence,Query,ScopedEvaluator
from research.semantic_reliability.uncertainty_cases import CASES

def run():
 _,key=credentials();client=jev_client(key);engine=ScopedEvaluator(client)
 directory=ROOT/'.local/research/semantic-reliability'/('uncertainty-'+str(time.time_ns()));directory.mkdir(parents=True)
 manifest={'kind':'authored_stress_suite','source_sha256':{f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in ['runtime.py','uncertainty.py','uncertainty_cases.py','UNCERTAINTY_PROTOCOL.md']},'max_calls':2,'retries':0}
 save(directory/'manifest.json',manifest);queries=[Query(name,claim,(Evidence('source',text),)) for name,text,claim,gold in CASES];rows={};calls=[]
 try:
  for mode in ['focused','dual']:
   results,call=engine.assess(queries,mode);calls.append(call);rows[mode]=results;save(directory/'calls.json',calls)
 finally:client.close()
 summary={'cases':len(CASES),'mode':{}}
 for mode,results in rows.items():
  correct=0;false_accept=0;abstain=0;failed=[]
  for name,text,claim,gold in CASES:
   r=results[name];is_abstain=r['reason'] in {'assessment_disagreement','provider_or_schema_error'}
   match=r['truth']==gold and not is_abstain;correct+=match;false_accept+=r['truth']=='supported' and gold!='supported';abstain+=is_abstain
   if not match:failed.append({'id':name,'expected':gold,'actual':r['truth'],'reason':r['reason']})
  summary['mode'][mode]={'correct':correct,'false_accept':false_accept,'abstentions':abstain,'failures':failed}
 save(directory/'results.json',{'manifest':manifest,'judgments':rows,'summary':summary});save(directory/'summary.json',summary);save(Path(__file__).parent/'uncertainty_summary.json',summary)
 print(json.dumps(summary,indent=2));print('Private stress results:',directory)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
 if a.run:run()
 else:print('No calls. Read UNCERTAINTY_PROTOCOL.md; --run opts in.')
