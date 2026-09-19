"""Opt-in, at most 4 DeepSeek calls; validates text-prefix and logprob transport.
No agent, user files, VM, shell execution or Jev requests. Not a quality benchmark.
"""
from pathlib import Path
import argparse
import sys
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import DeepSeekPrefix,credentials,save


def run():
    key,_=credentials()
    if not key:raise SystemExit('DeepSeek credential missing')
    p=ROOT/'.local/research/decoding-control'/('probe-'+str(time.time_ns()));p.mkdir(parents=True)
    g=DeepSeekPrefix(key);calls=[]
    system='Output only raw SQL. No code fences, explanation or comments. Complete the assistant prefix rather than repeating it.'
    task='SQLite: items(id INTEGER, amount INTEGER). Return id for items with amount greater than 7, ordered by id.'
    try:
        first=g.generate(system,task,limit=12,logprobs=True);calls.append(first);save(p/'calls.json',calls)
        if 'error' in first:raise RuntimeError('Initial generation failed')
        second=g.generate(system,task,prefix=first['text'],limit=80);calls.append(second);save(p/'calls.json',calls)
        forced='SELECT id FROM items WHERE amount > 7 ORDER BY'
        third=g.generate(system,task,prefix=forced,limit=12);calls.append(third);save(p/'calls.json',calls)
        import sqlite3
        db=sqlite3.connect(':memory:');db.executescript('CREATE TABLE items(id INTEGER, amount INTEGER);INSERT INTO items VALUES(2,9),(1,8),(3,7);')
        checks={}
        for name,text in [('resumed',first['text']+second.get('text','')),('forced',forced+third.get('text',''))]:
            try:checks[name]=db.execute(text).fetchall()==[(1,),(2,)]
            except sqlite3.Error:checks[name]=False
        db.close()
        entries=(first.get('logprobs') or {}).get('content') or []
        checks['logprobs_returned']=bool(entries)
        checks['logprob_bytes_reconstruct_text']=b''.join(bytes(t['bytes']) for t in entries if t.get('bytes')).decode('utf-8')==first['text']
        checks['no_reasoning_or_call_error']=all('error' not in c for c in calls)
        report={'checks':checks,'calls':len(calls),'partial_finish':first['finish'],'seconds':sum(c['seconds'] for c in calls),
                'interpretation':'Capability probe only. Text prefill is not native KV snapshot or exact token-ID control.'}
        save(p/'report.json',report);print(report);print(p)
        if not all(checks.values()):raise SystemExit(2)
    finally:g.close()


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--run',action='store_true');args=a.parse_args()
    if args.run:run()
    else:print('No calls. --run opts into at most four DeepSeek requests.')
