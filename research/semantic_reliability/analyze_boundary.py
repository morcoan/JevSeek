"""Offline publication audit of the already completed transport/NLI studies.
Requires private original traces and the separately downloaded public datasets.
Never calls a provider. Exports labels/metrics only, not document or prompt bodies.
"""
from __future__ import annotations
import hashlib,json,statistics
from collections import Counter
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.semantic_reliability.ordering import parse,specs,solve,selection
from research.semantic_reliability.transport import select_new
from research.semantic_reliability.nli import selected,infer_specs,decode,DS_SYSTEM
from research.semantic_reliability.ordering_experiment import DIRECT,COMPILE
from research.flash_integration.analyze import usage
BASE=ROOT/'.local/research/semantic-reliability'


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def check_sources(m):
    for name,h in m['source_sha256'].items():assert sha(Path(__file__).parent/name)==h


def transport(name):
    p=BASE/name;d=read(p/'results.json');m=d['manifest'];cs=read(p/'calls.json');cases=read(p/'selection.json');check_sources(m)
    assert hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest()==m['case_sha256']
    expected=([t for t in selection()['confirmation'] if t['size']==7][:8] if m['phase']=='replay' else select_new())
    assert cases==expected;ts={t['id']:t for t in cases};records=[];by={}
    for row in d['results']:
        t=ts[row['task']];context,rules,options=parse(t['input']);qs,_=specs(context,rules,options);out={'id':t['id'],'gold':t['target'],'predictions':{}}
        for arm,a in row['arms'].items():
            calls=[cs[i] for i in a['calls']]
            if arm=='jev_compiler':
                merged={};seen={}
                for c in calls:
                    assert c['state']=={'purpose':'Independent scoped sentence-to-constraint translation.'}
                    for k,v in c['questions'].items():assert qs[k]==v and k not in seen;seen[k]=v
                    merged.update(c['answers'])
                assert seen==qs and merged==a['answers'] and a['complete']
                assert solve(context,rules,options,merged)==a['solver'];choice=a['solver']['choice']
            elif arm=='ds_compiler':
                c=calls[0];assert c['system']==COMPILE and json.loads(c['task'])=={'questions':qs}
                answers=json.loads(c['text'])['answers'];assert answers==a['answers'];assert solve(context,rules,options,answers)==a['solver'];choice=a['solver']['choice']
            elif arm=='qwen_direct':
                c=calls[0];assert c['system']==DIRECT and c['payload']=={'problem':t['input']};choice=json.loads(c['text'])['choice']
            else:
                c=calls[0];assert c['state']=={'problem':t['input']};choice=c['answer']
            assert choice==a['choice'] and a['correct']==(choice==t['target'])
            out['predictions'][arm]=choice
            stats=by.setdefault(arm,{'correct':0,'total':0,'calls':[],'times':[]});stats['correct']+=a['correct'];stats['total']+=1;stats['calls']+=calls
            stats['times'].append(sum(c['seconds'] for c in calls)+a.get('solver_seconds',0))
        records.append(out)
    for stats in by.values():stats['usage']=usage(stats.pop('calls'));stats['median_call_plus_solver_seconds']=statistics.median(stats.pop('times'))
    return {'status':'completed','phase':m['phase'],'not_fresh_quality_sample':m['phase']=='replay','arms':by,'per_case_labels':records,'source_sha256':m['source_sha256'],
            'original_results_sha256':sha(p/'results.json'),'original_calls_sha256':sha(p/'calls.json'),'provider_calls':dict(Counter(c['provider'] for c in cs))}


def nli():
    p=BASE/'contract-nli-1789818731115722900';d=read(p/'results.json');m=d['manifest'];cs=read(p/'calls.json');cases=read(p/'selection.json');check_sources(m)
    current,hashes=selected();assert current==cases and hashes==m['dataset_hashes']
    assert hashlib.sha256(json.dumps(cases,sort_keys=True,ensure_ascii=False).encode()).hexdigest()==m['selection_sha256']
    ts={t['id']:t for t in cases};records=[];splits={}
    for row in d['results']:
        t=ts[row['task']];out={'document_id':t['id'],'split':t['split'],'gold':t['gold'],'predictions':{}}
        for arm,a in row['arms'].items():
            calls=[cs[i] for i in a['calls']]
            if arm=='deepseek':
                c=calls[0];assert c['system']==DS_SYSTEM;assert json.loads(c['task'])=={'document':t['text'],'hypotheses':t['hypotheses']};pred=json.loads(c['text'])['answers']
            else:
                qs,mapping=infer_specs(t['hypotheses'],arm);merged={};seen={}
                for c in calls:
                    assert c['state']=={'evidence':{'document':t['text']}}
                    for k,v in c['questions'].items():assert qs[k]==v and k not in seen;seen[k]=v
                    merged.update(c['answers'])
                assert seen==qs and merged==a['answers'] and a['complete'];pred,reasons=decode(merged,mapping,arm);assert reasons==a['reasons']
            assert pred==a['predictions'];correct=sum(pred.get(k)==v for k,v in t['gold'].items());assert correct==a['correct']
            stats=splits.setdefault(t['split'],{}).setdefault(arm,{'correct':0,'total':0,'false_entailments':0,'abstentions':0,'calls':[]})
            stats['correct']+=correct;stats['total']+=len(t['gold']);stats['false_entailments']+=sum(pred.get(k)=='Entailment' and v!='Entailment' for k,v in t['gold'].items());stats['abstentions']+=sum(pred.get(k) is None for k in t['gold']);stats['calls']+=calls
            out['predictions'][arm]=pred
        records.append(out)
    for arms in splits.values():
        for stats in arms.values():stats['usage']=usage(stats.pop('calls'))
    return {'status':'completed_boundary_probe_not_production_grounding','splits':splits,'per_document_labels':records,'source_sha256':m['source_sha256'],'dataset_hashes':hashes,
            'original_results_sha256':sha(p/'results.json'),'original_calls_sha256':sha(p/'calls.json'),'provider_calls':dict(Counter(c['provider'] for c in cs)),
            'attribution':'ContractNLI, Koreeda and Manning (2021), CC BY4.0; https://github.com/stanfordnlp/contract-nli; no full contract text republished here.'}


def run():
    result={'new_provider_calls':0,'transport_replay':transport('transport-replay-1789817432745845800'),'transport_fresh':transport('transport-fresh-1789817689318340800'),'contract_nli':nli()}
    (Path(__file__).parent/'boundary_summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'all_pass':True,'new_provider_calls':0,'transport_replay_cases':8,'transport_fresh_cases':20,'nli_documents':12,'transport_fresh_correct':{a:v['correct'] for a,v in result['transport_fresh']['arms'].items()},'nli_test_correct':{a:v['correct'] for a,v in result['contract_nli']['splits']['test'].items()}},indent=2))
if __name__=='__main__':run()
