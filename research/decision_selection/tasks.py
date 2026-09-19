"""Hand-authored SQL transfer probes; not a standardized benchmark.
Only prompt/schema are sent to providers. Independent Python reference functions
and deterministic test data remain evaluator-side. Generated SQL is SELECT-only,
in-memory, authorizer restricted and bounded by a SQLite instruction budget.
"""
from collections import defaultdict, deque
import random
import sqlite3
import statistics

SCHEMA = '''SQLite tables:
accounts(id INTEGER PRIMARY KEY, grp TEXT NOT NULL)
events(id INTEGER PRIMARY KEY, account_id INTEGER, day INTEGER NOT NULL, kind TEXT NOT NULL, value INTEGER)
bookings(id INTEGER PRIMARY KEY, resource TEXT NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL)
links(src INTEGER NOT NULL, dst INTEGER NOT NULL)
No foreign keys. NULL/orphan event account_ids exist. Events can share a day and value.
Days are integer calendar days; intervals have start < end. Links can duplicate and cycle.
Return exactly the requested columns; row order is irrelevant unless explicitly stated.
No access to actual table contents at generation time. Must work on arbitrary valid data.
'''
TASKS = [
 ('anti_null', 'Return account id for accounts with no paid event, regardless of paid value. NULL and orphan account_ids must not exclude unrelated accounts.'),
 ('latest_filter', 'Return id of each account whose most recent event is paid. Most recent means maximum (day,id) lexicographically among ALL its events, not just paid events. Accounts without events excluded.'),
 ('second_distinct', 'For EVERY account return (id, second_value), the second largest DISTINCT non-NULL value among paid events, or NULL if fewer than two such values. Repeated equal values do not occupy two ranks.'),
 ('rolling_calendar', 'For each account/day having at least one paid event, return (account_id,day,total), total non-NULL paid values over calendar days [day-2,day] inclusive. Duplicate events count individually; NULL values count zero. Only real accounts; output one row per qualifying account/day.'),
 ('longest_streak', 'For EVERY account return (id,longest), the longest streak of consecutive integer days with paid events, zero if none. Multiple paid events on one day count as one active day. Value is irrelevant.'),
 ('universal_group', 'Return grp for groups where EVERY account has at least one paid event with value > 0. Multiple matching events do not compensate for a missing account. Every listed group has at least one account.'),
 ('halfopen_overlap', 'Return (first_id,second_id) for unordered pairs of bookings on the same resource whose half-open intervals [start,end) overlap. first_id < second_id. Merely touching endpoints is not overlap.'),
 ('reachability', 'Return one column node containing every node reachable from integer node 1 by a path of 1, 2, or 3 directed edges. Include 1 only if reachable by a nonempty such path. Deduplicate nodes and terminate even with cycles and duplicate edges.'),
 ('median', 'For EVERY account return (id,median_value), median of its non-NULL paid event values INCLUDING repeated values, or NULL if none. Even counts use arithmetic mean of two central values, preserving .5, not integer division.'),
 ('net_totals', 'For EVERY account return (id,net): sum paid values minus sum refund values; ignore other kinds; NULL values zero; no matching events zero. NULL and orphan account_ids must not create output accounts.'),
 ('dense_top', 'Calculate net as paid sum minus refund sum, NULL values zero, all other kinds ignored, missing events zero. Within each grp return (id,net) for EVERY account in the highest two DISTINCT net ranks, preserving ties. Groups with fewer than two ranks return all accounts.'),
 ('paid_after_refund', 'Return account id if its latest paid event is strictly AFTER its latest refund event, comparing events by (day,id). Require at least one of each kind. Ignore other kinds and value. Output each real account at most once.'),
]


def fixture(seed):
    r=random.Random(seed)
    accounts=[(i, 'abc'[(i-1)//3]) for i in range(1,10)]
    events=[]
    # Includes an empty account, ties, missing days, negative/zero/NULL values,
    # null foreign keys, and groups whose counts can be inflated by duplicates.
    for i in range(1,81):
        events.append((i,r.choice([None,99,1,2,3,4,5,6,7,8]),r.randrange(1,11),r.choice(['paid','refund','other']),r.choice([None,-4,0,1,1,3,8,8])))
    events.extend([(81,None,20,'paid',10),(82,1,11,'paid',3),(83,1,11,'other',3)])
    bookings=[(i,r.choice(['x','y']),s:=r.randrange(0,15),s+r.randrange(1,6)) for i in range(1,18)]
    links=[(r.randrange(1,8),r.randrange(1,8)) for _ in range(14)] + [(1,2),(2,1),(2,3),(3,4),(4,5),(1,2)]
    return accounts,events,bookings,links


def reference(name, data):
    accounts,events,bookings,links=data
    by={a:[e for e in events if e[1]==a] for a,_ in accounts}
    paid={a:[e for e in es if e[3]=='paid'] for a,es in by.items()}
    net={a:sum((e[4] or 0)*(1 if e[3]=='paid' else -1 if e[3]=='refund' else 0) for e in es) for a,es in by.items()}
    if name=='anti_null': return [(a,) for a in by if not paid[a]]
    if name=='latest_filter': return [(a,) for a,es in by.items() if es and max(es,key=lambda e:(e[2],e[0]))[3]=='paid']
    if name=='second_distinct':
        out=[]
        for a,es in paid.items():
            vals=sorted({e[4] for e in es if e[4] is not None},reverse=True)
            out.append((a,vals[1] if len(vals)>1 else None))
        return out
    if name=='rolling_calendar': return [(a,d,sum(e[4] or 0 for e in es if d-2<=e[2]<=d)) for a,es in paid.items() for d in sorted({e[2] for e in es})]
    if name=='longest_streak':
        out=[]
        for a,es in paid.items():
            prev=None; streak=best=0
            for d in sorted({e[2] for e in es}):
                streak=streak+1 if prev is not None and d==prev+1 else 1
                best=max(best,streak);prev=d
            out.append((a,best))
        return out
    if name=='universal_group': return [(g,) for g in sorted({g for _,g in accounts}) if all(any((e[4] or 0)>0 for e in paid[a]) for a,h in accounts if h==g)]
    if name=='halfopen_overlap': return [(i,j) for i,g,s,t in bookings for j,h,u,v in bookings if i<j and g==h and s<v and u<t]
    if name=='reachability':
        frontier={1};seen=set()
        for _ in range(3):
            frontier={v for u,v in links if u in frontier};seen|=frontier
        return [(v,) for v in seen]
    if name=='median': return [(a,statistics.median(vals) if (vals:=[e[4] for e in es if e[4] is not None]) else None) for a,es in paid.items()]
    if name=='net_totals': return list(net.items())
    if name=='dense_top': return [(a,net[a]) for a,g in accounts if net[a] in sorted({net[b] for b,h in accounts if h==g},reverse=True)[:2]]
    if name=='paid_after_refund':
        out=[]
        for a,es in by.items():
            p=[(e[2],e[0]) for e in es if e[3]=='paid'];f=[(e[2],e[0]) for e in es if e[3]=='refund']
            if p and f and max(p)>max(f):out.append((a,))
        return out
    raise ValueError(name)


def execute(sql,data):
    db=sqlite3.connect(':memory:')
    try:
        db.executescript('CREATE TABLE accounts(id INTEGER PRIMARY KEY,grp TEXT NOT NULL); CREATE TABLE events(id INTEGER PRIMARY KEY,account_id INTEGER,day INTEGER NOT NULL,kind TEXT NOT NULL,value INTEGER); CREATE TABLE bookings(id INTEGER PRIMARY KEY,resource TEXT NOT NULL,start INTEGER NOT NULL,end INTEGER NOT NULL); CREATE TABLE links(src INTEGER NOT NULL,dst INTEGER NOT NULL);')
        for table,rows in zip(['accounts','events','bookings','links'],data):
            if rows:db.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in rows[0])})',rows)
        db.commit();db.execute('PRAGMA query_only=ON')
        allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE}
        db.set_authorizer(lambda action,a,b,c,d: sqlite3.SQLITE_OK if action in allowed and not (action==sqlite3.SQLITE_FUNCTION and b in {'load_extension','writefile','readfile','randomblob','zeroblob'}) else sqlite3.SQLITE_DENY)
        ticks=0
        def budget():
            nonlocal ticks
            ticks+=1
            return int(ticks>2000)
        db.set_progress_handler(budget,1000)
        rows=db.execute(sql).fetchmany(10001)
        if len(rows)>10000:raise ValueError('Result limit')
        return sorted(rows,key=repr)
    finally:db.close()


def evaluate(name,sql):
    if not isinstance(sql,str) or len(sql)>12000:return {'pass':False,'error':'format'}
    for seed in range(20):
        data=fixture(seed)
        try:got=execute(sql,data)
        except Exception as exc:return {'pass':False,'failed_seed':seed,'error':type(exc).__name__}
        if got!=sorted(reference(name,data),key=repr):
            # Numeric SQLite integer/float equivalence is fine, sorting by repr
            # is stable here because first columns are unique ids or pairs.
            return {'pass':False,'failed_seed':seed,'error':'wrong_result'}
    return {'pass':True,'fixtures':20}
