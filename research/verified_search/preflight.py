"""Offline dataset/evaluator guards, not a model run."""
from __future__ import annotations
import ast
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.verified_search.data import CACHE,execute,evaluate,schema
from research.verified_search.experiment import select,majority


def run():
    data=json.loads((CACHE/'selection.json').read_text());tasks=data['development']+data['confirmation']
    for t in tasks:
        assert evaluate(t,t['query'])['pass']
        json.dumps(schema(t['db_id']))
    db=tasks[0]['db_id']
    attempts=['DROP TABLE whatever','ATTACH DATABASE "x.sqlite" AS x','SELECT load_extension("x")','SELECT readfile(".env")','SELECT 1; SELECT 2',
              'WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t) SELECT sum(x) FROM t','SELECT randomblob(999999999)']
    for sql in attempts:assert 'error' in execute(db,sql),sql
    questions={'pair0':{'criteria':{'left':'','right':'','tie':''},'pair':['c0','c1']},'global':{'criteria':{'c0':'','c1':''}}}
    assert select(questions,{'pair0':'right','global':'c1'},{'c0':1,'c1':0},0)[:2]==(0,0)
    assert majority([{'execution':{'rows':[(1,)]}},{'execution':{'rows':[(2,)]}},{'execution':{'rows':[(2,)]}}])==1
    for p in Path(__file__).parent.glob('*.py'):ast.parse(p.read_text())
    result={'reference_queries':len(tasks),'readonly_guards':len(attempts),'development_databases':sorted({t['db_id'] for t in data['development']}),
            'confirmation_databases':sorted({t['db_id'] for t in data['confirmation']}),'all_pass':True}
    assert not set(result['development_databases']) & set(result['confirmation_databases'])
    return result

if __name__=='__main__':print(json.dumps(run(),indent=2))
