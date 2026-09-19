"""Public Spider data and constrained SQLite evaluation; never executes model Python.
Dataset mirror is pinned. SQL cannot read host files, write, attach databases or
invoke arbitrary extensions. Gold queries/answers stay outside provider payloads.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[2]
CACHE=ROOT/'.local/research/verified-search/data'
REVISION='20060fadce13ab8a88c24d60dc7ad39e3eced695'
BASE=f'https://huggingface.co/datasets/minktn/spider-data/resolve/{REVISION}/spider_data/'


def database(db_id):
    assert re.fullmatch(r'[a-zA-Z0-9_]+',db_id)
    return CACHE/'database'/db_id/(db_id+'.sqlite')


def connect(db_id):
    # Work on a disposable in-memory copy, never the persistent benchmark DB.
    source=sqlite3.connect(database(db_id).as_uri()+'?mode=ro',uri=True)
    db=sqlite3.connect(':memory:')
    try:source.backup(db)
    finally:source.close()
    db.execute('PRAGMA trusted_schema=OFF');db.execute('PRAGMA temp_store=MEMORY');db.execute('PRAGMA query_only=ON')
    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,2_000_000)
    db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH,30000)
    db.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH,100)
    db.setlimit(sqlite3.SQLITE_LIMIT_VDBE_OP,100000)
    db.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED,0)
    allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE}
    functions={'abs','avg','coalesce','count','dense_rank','first_value','ifnull','lag','last_value','lead','max','min','nullif','nth_value','ntile','percent_rank','rank','round','row_number','sign','sum','total','iif','like','glob','length','lower','upper','trim','ltrim','rtrim','replace','substr','substring','instr','date','datetime','strftime','julianday','unixepoch','typeof'}
    db.set_authorizer(lambda action,a,b,c,d:sqlite3.SQLITE_OK if action in allowed and (action!=sqlite3.SQLITE_FUNCTION or str(b).lower() in functions) else sqlite3.SQLITE_DENY)
    ticks=0
    def stop():
        nonlocal ticks
        ticks+=1
        return int(ticks>10000)
    db.set_progress_handler(stop,1000)
    return db


def execute(db_id,sql):
    if not isinstance(sql,str) or not 0<len(sql)<=30000:return {'error':'invalid_sql_length'}
    db=connect(db_id)
    try:
        cur=db.execute(sql);rows=cur.fetchmany(1001)
        if len(rows)>1000:return {'error':'row_limit'}
        return {'columns':[d[0] for d in cur.description or []],'rows':rows}
    except Exception as exc:
        # SQLite diagnostics contain generated SQL identifiers, not host secrets.
        return {'error':type(exc).__name__,'message':str(exc)[:300]}
    finally:db.close()


def schema(db_id):
    db=sqlite3.connect(database(db_id).as_uri()+'?mode=ro',uri=True)
    try:
        tables=db.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        result=[]
        for name,ddl in tables:
            safe='"'+name.replace('"','""')+'"'
            cursor=db.execute('SELECT * FROM '+safe+' LIMIT 2')
            result.append({'ddl':ddl,'sample_columns':[d[0] for d in cursor.description],'sample_rows':cursor.fetchall()})
        return result
    finally:db.close()


def cell(v):
    if isinstance(v,float):return round(v,7)
    if isinstance(v,bytes):return ('bytes',v.hex())
    return v


def normalized(rows):return Counter(tuple(cell(v) for v in row) for row in rows)


def evaluate(task,sql):
    gold=execute(task['db_id'],task['query']);pred=execute(task['db_id'],sql)
    assert 'error' not in gold,task['id']
    if 'error' in pred:return {'pass':False,'error':pred['error']}
    # Primary metric is column-ordered row-MULTISET agreement on one DB.
    # Record ordered agreement separately: tied ORDER BY values can admit many
    # correct orders, while unordered comparison can miss sorting mistakes.
    ordered=bool(re.search(r'\border\s+by\b',task['query'],re.I))
    a=[tuple(cell(v) for v in r) for r in gold['rows']];b=[tuple(cell(v) for v in r) for r in pred['rows']]
    return {'pass':normalized(a)==normalized(b),'ordered_reference':ordered,'ordered_agreement':a==b,
            'reference_rows':len(a),'predicted_rows':len(b)}


def download(relative):
    import requests
    target=CACHE/relative
    if target.exists():return target
    target.parent.mkdir(parents=True,exist_ok=True)
    response=requests.get(BASE+relative,timeout=90);response.raise_for_status()
    temporary=target.with_suffix(target.suffix+'.part');temporary.write_bytes(response.content);temporary.replace(target)
    return target


def prepare():
    CACHE.mkdir(parents=True,exist_ok=True)
    raw=json.loads(download('dev.json').read_text(encoding='utf-8'))
    download('tables.json')
    # Only compositional records; no provider performance influences selection.
    eligible=[];seen=set();excluded=[]
    for i,r in enumerate(raw):
        q=r['query'];complexity=len(re.findall(r'\bselect\b',q,re.I))+2*len(re.findall(r'\b(?:having|intersect|except|union)\b',q,re.I))
        if complexity<3:continue
        fingerprint=json.dumps(r['sql'],sort_keys=True,separators=(',',':'))
        if (r['db_id'],fingerprint) in seen:continue
        seen.add((r['db_id'],fingerprint));download(f'database/{r["db_id"]}/{r["db_id"]}.sqlite')
        task={'id':f'spider-dev-{i}','index':i,'db_id':r['db_id'],'question':r['question'],'query':q,'complexity':complexity}
        execution=execute(r['db_id'],q)
        if 'error' in execution or not execution['rows']:
            excluded.append({'id':task['id'],'reason':'reference_error_or_empty'});continue
        eligible.append(task)
    rng=random.Random(194731);bydb={}
    for t in eligible:bydb.setdefault(t['db_id'],[]).append(t)
    names=sorted(bydb);rng.shuffle(names)
    # Entire DBs, not merely questions, held out from exploratory prompts.
    development_dbs=names[:max(3,len(names)//3)]
    def take(dbs,n):
        groups={db:rng.sample(bydb[db],len(bydb[db])) for db in dbs};out=[]
        while len(out)<n and any(groups.values()):
            for db in dbs:
                if groups[db] and len(out)<n:out.append(groups[db].pop())
        return out
    development=take(development_dbs,12);confirmation=take([d for d in names if d not in development_dbs],28)
    assert len(development)>=8 and len(confirmation)>=20,(len(development),len(confirmation),names)
    hashes={str(p.relative_to(CACHE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in CACHE.rglob('*') if p.is_file() and p.suffix in {'.sqlite','.json'} and p.name!='selection.json'}
    obj={'dataset':'Spider dev via minktn/spider-data','revision':REVISION,'selection_seed':194731,
         'eligibility':'SQL SELECT count +2*HAVING/INTERSECT/EXCEPT/UNION count >=3; unique parsed SQL within DB; nonempty executable gold',
         'eligible':len(eligible),'eligible_databases':len(names),'excluded_reference':excluded,'development':development,'confirmation':confirmation,'file_sha256':hashes}
    path=CACHE/'selection.json';path.write_text(json.dumps(obj,indent=2),encoding='utf-8')
    return {'development':len(development),'confirmation':len(confirmation),'databases':len(names),'eligible':len(eligible),'selection_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

if __name__=='__main__':print(json.dumps(prepare(),indent=2))
