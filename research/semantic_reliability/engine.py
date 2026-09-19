"""Reusable research interface. Judgments are assumptions, never permissions/proofs.
Reuses tested wording while adding bounded transport and immutable, scope-aware cache.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,itertools,json
from .runtime import Evidence,Query,Truth,specification,merge_polarities,evaluate_expression
from .bounded import ask_bounded

ENGINE_VERSION='scoped-engine-1'

@dataclass(frozen=True)
class Judgment:
    truth:str
    reason:str
    fingerprint:str
    source_versions:tuple[tuple[str,str,str],...]
    scope_revision:str
    model:str
    semantic_proof:bool=False


class SemanticEngine:
    """Caller owns client and supplies current source snapshots + scope revision."""
    def __init__(self,client,model='jev-1.13.0',max_bytes=60000,max_requests=16):
        self.client=client;self.model=model;self.max_bytes=max_bytes;self.max_requests=max_requests;self._cache={}
    def clear(self):self._cache.clear()
    def assess(self,queries,*,scope_revision,mode='focused'):
        if not isinstance(scope_revision,str) or not scope_revision:raise ValueError('explicit_scope_revision_required')
        if mode not in {'focused','dual'} or not 1<=len(queries)<=256 or len({q.id for q in queries})!=len(queries):raise ValueError('mode_count_or_ids')
        ready={};pending={};groups={};keys={}
        for q in queries:
            if not q.id or not q.claim or not q.evidence or any(not e.id or not e.text for e in q.evidence):raise ValueError('empty_claim_or_source')
            if len({e.id for e in q.evidence})!=len(q.evidence):raise ValueError('duplicate_source_id')
            positive=specification(q);negative=specification(q,True) if mode=='dual' else None
            fingerprint=hashlib.sha256(json.dumps([ENGINE_VERSION,self.model,scope_revision,mode,positive,negative],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            keys[q.id]=fingerprint
            if fingerprint in self._cache:ready[q.id]=self._cache[fingerprint];continue
            if fingerprint in groups:groups[fingerprint].append(q);continue
            groups[fingerprint]=[q];label='q'+str(len(groups)-1);pending[label]=positive
            if negative:pending[label+'_not']=negative
        result={'calls':[],'answers':{},'complete':True,'errors':[]}
        if pending:
            result=ask_bounded(self.client,{'role':'Independent evidence-scoped decisions. All relevant evidence is explicitly in each question.'},pending,max_bytes=self.max_bytes,max_requests=self.max_requests)
        answers=result.get('answers') or result.get('partial_answers',{})
        for i,(fingerprint,aliases) in enumerate(groups.items()):
            label='q'+str(i);q=aliases[0]
            if label not in answers or (mode=='dual' and label+'_not' not in answers):truth,reason='unknown','assessment_unavailable'
            elif mode=='dual':v,reason=merge_polarities(answers[label],answers[label+'_not']);truth=v.value
            else:truth,reason=answers[label],'single_scoped_judgment'
            judgment=Judgment(truth,reason,fingerprint,tuple((e.id,e.revision,e.digest) for e in q.evidence),scope_revision,self.model)
            if reason!='assessment_unavailable':self._cache[fingerprint]=judgment
            for alias in aliases:ready[alias.id]=judgment
        return {'judgments':{k:asdict(v) for k,v in ready.items()},'calls':result['calls'],'complete':result['complete'],'errors':result['errors'],
                'model_assessed_not_observed_truth':True}


def assignment_bounds(items,slots,costs,judgments):
    """Cost bounds across unknown edges. NO guarantee labels match the real world.
    A conservative plan may be feasible without being provably cheapest.
    """
    if not items or len(items)>len(slots) or len(slots)>8 or len(set(items))!=len(items) or len(set(slots))!=len(slots):raise ValueError('assignment_shape_or_budget')
    if any(not isinstance(v,str) or not v or len(v)>128 for v in [*items,*slots]):raise ValueError('invalid_identifier')
    # Integer units only: no floating-point claim of exact monetary optimality.
    if set(costs)!=set(slots) or any(type(v) is not int or not 0<=v<=10**12 for v in costs.values()):raise ValueError('nonnegative_integer_costs_required')
    expected={(i,s) for i in items for s in slots}
    if set(judgments)!=expected:raise ValueError('incomplete_relation')
    relation={k:Truth(v) for k,v in judgments.items()}
    def best(optimistic):
        winner=None;price=None
        for chosen in itertools.permutations(slots,len(items)):
            accepted=all((relation[i,s]!=Truth.FALSE if optimistic else relation[i,s]==Truth.TRUE) for i,s in zip(items,chosen))
            if accepted:
                cost=sum(costs[s] for s in chosen)
                if price is None or cost<price:price=cost;winner=dict(zip(items,chosen))
        return winner,price
    proposed,upper=best(False);possible,lower=best(True)
    uncertain=[{'item':i,'slot':s,'truth':relation[i,s].value} for i in items for s in slots if relation[i,s] in {Truth.UNKNOWN,Truth.CONFLICT}]
    status=('infeasible_under_assessments' if possible is None else 'needs_more_evidence' if proposed is None else
            'optimal_under_assessments' if upper==lower else 'feasible_optimality_unresolved')
    return {'status':status,'proposed_assignment':proposed,'cost':upper,'optimistic_lower_cost':lower,
            'optimistic_witness':possible,'uncertain_edges':uncertain,'semantic_proof':False,'execute_authorized':False}
