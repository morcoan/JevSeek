"""Cost-weighted re-analysis of saved responses: zero provider requests.
List-price estimates, not invoices. Reasoning is already in completion_tokens.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal as D
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))

@dataclass(frozen=True)
class Rates:
    input_miss: D
    input_hit: D
    output: D

RATES={
 'jev':Rates(D('.042'),D('.042'),D('0')),
 'deepseek_off_peak':Rates(D('.15'),D('.003'),D('.60')),
 'deepseek_peak':Rates(D('.30'),D('.006'),D('1.20')),
}
SOURCES={
 'jev':{'url':'https://docs.typesafe.ai/models.md','model':'jev-1.13.0','input_usd_per_million':'0.042','output_usd_per_million':'0','quote':'Price: Charged per input token. Output tokens are free.'},
 'deepseek':{'url':'https://api-docs.deepseek.com/quick_start/pricing','model':'DeepSeek-V4.1-Flash','off_peak':{'input_cache_hit':'0.003','input_cache_miss':'0.15','output':'0.60'},'peak':{'input_cache_hit':'0.006','input_cache_miss':'0.30','output':'1.20'},'peak_hours':'Monday-Friday 01:00-04:00 and06:00-10:00 UTC; all others off-peak'},
 'retrieved':'2026-09-19; official pages fetched via Exa, current public list prices, not account-specific invoices',
}


def counts(call):
    u=call['usage'];p=call['provider']
    if p=='jev':
        n=u['input_tokens'];hit=0;out=u['output_tokens']
    elif p=='deepseek':
        n=u['prompt_tokens'];out=u['completion_tokens']
        hit=u.get('prompt_cache_hit_tokens')
        nested=(u.get('prompt_tokens_details') or {}).get('cached_tokens')
        if hit is None:hit=nested
        if hit is None:raise ValueError('Unknown cache breakdown: do not silently price it as zero')
        if nested is not None and hit!=nested:raise ValueError('Conflicting cache counters')
        if u.get('prompt_cache_miss_tokens') is not None and u['prompt_cache_miss_tokens']!=n-hit:raise ValueError('Inconsistent cache breakdown')
    else:raise ValueError('Unsupported provider')
    if any(type(v) is not int or v<0 for v in [n,hit,out]) or hit>n:raise ValueError('Invalid usage')
    return n-hit,hit,out


def cost(call,period='off_peak'):
    miss,hit,out=counts(call)
    r=RATES['jev' if call['provider']=='jev' else 'deepseek_'+period]
    return (D(miss)*r.input_miss+D(hit)*r.input_hit+D(out)*r.output)/D(1_000_000)


def audit():
    from research.efficiency.tasks import fixtures,evaluate,fingerprint
    from research.efficiency.fastpath import render
    root=ROOT/'.local/research/efficiency/confirmation-1789831826798837800'
    data=json.loads((root/'results.json').read_text(encoding='utf-8'));ts={t['id']:t for t in fixtures()};m=data['manifest']
    assert fingerprint()==m['fixture_sha256']
    for name,expected in m['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected
    rows=data['results'];assert len(rows)==12
    names=['plain','thinking','jev_verbose','jev_compact'];calls={k:[] for k in names};correct={k:0 for k in names};hashes={}
    for row in rows:
        path=root/row['task']/'calls.json';hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        cs=json.loads(path.read_text(encoding='utf-8'));t=ts[row['task']];assert len(cs)==4
        for arm in names:
            v=row['arms'][arm];assert evaluate(t,v['answers'])==v['evaluation'];assert render(t['catalog'],t['queries'],v['answers'])==v['result']
            c=cs[v['call']];assert c['arm']==arm and 'error' not in c
            assert c['model']==('jev-1.13.0' if arm.startswith('jev_') else 'deepseek-flash')
            calls[arm].append(c);correct[arm]+=v['evaluation']['correct']
    scenarios={}
    for period in ['off_peak','peak']:
        money={a:sum((cost(c,period) for c in cs),D(0)) for a,cs in calls.items()};j=money['jev_compact']
        scenarios[period]={'estimated_usd_for_12_batches':{a:str(v) for a,v in money.items()},'compact_saving_fraction':{a:str(1-j/money[a]) for a in ['plain','thinking','jev_verbose']},
            'fallback_break_even_fraction_of_equal_cost_flash_requests':{a:str(1-j/money[a]) for a in ['plain','thinking']}}
    usage={a:{'requests':len(cs),'input_miss':sum(counts(c)[0] for c in cs),'input_hit':sum(counts(c)[1] for c in cs),'output':sum(counts(c)[2] for c in cs)} for a,cs in calls.items()}
    # Counterfactual caching sensitivity; no such hit rate was observed in these logs.
    n=usage['plain']['input_miss']+usage['plain']['input_hit'];o=usage['plain']['output'];j=sum((cost(c) for c in calls['jev_compact']),D(0));cache={}
    for period in ['off_peak','peak']:
        r=RATES['deepseek_'+period];all_miss=(D(n)*r.input_miss+D(o)*r.output)/D(1_000_000)
        cache[period]=str((all_miss-j)/(D(n)*(r.input_miss-r.input_hit)/D(1_000_000)))
    return {'kind':'posthoc_list_price_audit_of_saved_confirmation_NOT_new_quality_trial','sources':SOURCES,'new_provider_requests':0,'calls_repriced':48,'outcomes_and_rendered_results_recomputed':48,
        'accuracy':correct,'usage':usage,'scenarios':scenarios,'plain_flash_cache_hit_fraction_at_cost_equality':cache,'raw_call_sha256':hashes,
        'limits':['Saved choices/latencies unchanged; not an invoice or a new quality sample.','12batches repeat24semantic patterns from3authored catalogues, not96independent real-world tasks.','This is a selection endpoint, not a full coding agent. Upstream query/catalogue authoring and downstream narration/execution/fallback are excluded.','In an actual cascade, charge every Jev and Flash attempt, failure, retry, fallback and reporting call. Do not double-count reasoning tokens.','Fallback break-even assumes each fallback costs the average original Flash request; it is an economic bound, NOT an accuracy threshold or confidence calibration.','Candidate NONE answers are valid for the original selection service; solving the unavailable work may require a separately charged generative fallback.','Actual cache usage, peak hours, model version, contract rates and prices can change the result.']}


def checks():
    checks=0
    flash={'provider':'deepseek','usage':{'prompt_tokens':100,'completion_tokens':20,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60,'completion_tokens_details':{'reasoning_tokens':17}}}
    assert cost(flash)==D('.00002112');checks+=1
    assert cost(flash,'peak')==2*cost(flash);checks+=1
    jev={'provider':'jev','usage':{'input_tokens':100,'output_tokens':100000}}
    assert cost(jev)==D('.0000042');checks+=1
    jev['usage']['output_tokens']=0;assert cost(jev)==D('.0000042');checks+=1
    for u in [{'prompt_tokens':100,'completion_tokens':1}, {'prompt_tokens':1,'completion_tokens':2,'prompt_cache_hit_tokens':2}, {'prompt_tokens':10,'completion_tokens':2,'prompt_cache_hit_tokens':3,'prompt_cache_miss_tokens':8}]:
        try:cost({'provider':'deepseek','usage':u})
        except ValueError:checks+=1
        else:raise AssertionError('bad_usage_accepted')
    return checks

if __name__=='__main__':
    from research.decoding_control.providers import save
    output=audit();output['offline_cost_checks']=checks()
    save(ROOT/'research/cost_offload/summary.json',output)
    print(json.dumps({k:v for k,v in output.items() if k not in {'raw_call_sha256','limits'}},indent=2))
