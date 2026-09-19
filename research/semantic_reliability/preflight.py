"""No network: Boolean properties, uncertainty and cache/binding invariants."""
from __future__ import annotations
import itertools
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.semantic_reliability.runtime import *


def run():
    checks=0
    atom=['atom','p'];other=['atom','q']
    for p,q in itertools.product([False,True],repeat=2):
        values={'p':'supported' if p else 'refuted','q':'supported' if q else 'refuted'}
        for expr,expected in [(['and',atom,other],p and q),(['or',atom,other],p or q),(['implies',atom,other],not p or q),(['not',atom],not p)]:
            assert evaluate_expression(expr,values)['truth']==('supported' if expected else 'refuted');checks+=1
    for expr,values,expected in [(['not',atom],{'p':'unknown'},'unknown'),(['or',atom,['not',atom]],{'p':'unknown'},'supported'),
                                (['implies',atom,other],{'p':'unknown','q':'supported'},'supported'),
                                (['and',atom,other],{'p':'refuted','q':'unknown'},'refuted'),
                                (atom,{'p':'conflict'},'conflict')]:
        assert evaluate_expression(expr,values)['truth']==expected;checks+=1
    for expr in [['exec','anything'],['atom','missing'],['not',atom,other]]:
        try:evaluate_expression(expr,{'p':'unknown','q':'supported'})
        except ValueError:checks+=1
        else:raise AssertionError('invalid AST accepted')
    deep=atom
    for i in range(20):deep=['not',deep]
    try:evaluate_expression(deep,{'p':'supported'})
    except ValueError:checks+=1
    else:raise AssertionError('depth guard failed')
    assert merge_polarities('supported','refuted')[0]==Truth.TRUE;checks+=1
    assert merge_polarities('supported','supported')[0]==Truth.UNKNOWN;checks+=1
    assert merge_polarities('conflict','refuted')[0]==Truth.CONFLICT;checks+=1
    class Client:
        count=0
        def system_one(self,*,state,questions):
            self.count+=1
            return SimpleNamespace(answers={k:SimpleNamespace(choice='refuted' if k.endswith('_not') else 'supported',confidence=.9) for k in questions},
                raw_http_response=SimpleNamespace(json=lambda:{'model':'fake','usage':{}}))
    client=Client();engine=ScopedEvaluator(client)
    query=Query('a','claim',(Evidence('e','fact'),))
    first,call=engine.assess([query],'dual');assert client.count==1 and first['a']['truth']=='supported';checks+=1
    first['a']['evidence'].clear();second,call=engine.assess([query],'dual');assert client.count==1 and call is None and second['a']['evidence'];checks+=1
    engine.assess([Query('a','claim',(Evidence('e','changed'),))],'dual');assert client.count==2;checks+=1
    engine.assess([Query('a','claim',(Evidence('e','changed','2'),))],'dual');assert client.count==3;checks+=1
    engine.assess([Query('a','claim',(Evidence('e2','changed','2'),))],'dual');assert client.count==4;checks+=1
    engine.assess([query],'focused');assert client.count==5;checks+=1
    assert not second['a']['semantic_proof'];checks+=1
    return {'offline_checks':checks,'all_pass':True,'provider_calls':0}

if __name__=='__main__':print(run())
