"""Hand-authored closed-world repair fixtures. No model-generated code is executed.
Each task has one hidden contract file, two plausible distractor files and four
candidate replacements. Test cases and winning candidate are never provider state.
"""
from __future__ import annotations
import copy
import hashlib
import random

TASKS=[]

def add(name,issue,bug,contract,candidates,cases,files=('contract.md','view.py','client.py')):
    rng=random.Random(name); order=list(range(4));rng.shuffle(order)
    docs={files[0]:contract,files[1]:'Presentation layer: forwards inputs and displays the returned value. No additional filtering or normalization.',
          files[2]:'Transport layer: values are passed through unchanged. No retries, sorting, authorization or caching here.'}
    TASKS.append(dict(id=name,issue=issue,source='def solve(x):\n    '+bug+'\n',files=docs,
                      candidates={f'p{i}':'def solve(x):\n    '+candidates[j]+'\n' for i,j in enumerate(order)},
                      correct='p'+str(order.index(0)),tests=cases,relevant=files[0]))

add('lease_boundary','A lease remains usable at a boundary where consumers reject it.',
    'return x[0] <= x[1]',
    'Lease protocol: x=[now,expires]. A lease is active strictly before expires. expires=None means it never expires; zero is a real deadline.',
    ['return x[1] is None or x[0] < x[1]','return x[1] is None or x[0] <= x[1]',
     'return not x[1] or x[0] < x[1]','return x[1] is not None and x[0] < x[1]'],
    [([10,10],False),([0,0],False),([2,None],True),([2,3],True),([4,3],False)],('lease_spec.md','lease_badge.py','lease_client.py'))
add('retry_budget','Some requests make the wrong number of retry attempts.',
    'return x[0] < x[1]',
    'x=[failures_so_far,max_retries]. failures includes the just-failed initial attempt. max_retries excludes the initial attempt. -1 alone means unlimited retries. Other negative budgets allow none.',
    ['return x[1] == -1 or (x[1] >= 0 and x[0] <= x[1])','return x[1] == -1 or x[0] < x[1]',
     'return x[1] < 0 or x[0] <= x[1]','return x[0] <= x[1]'],
    [([1,1],True),([2,1],False),([1,0],False),([100,-1],True),([1,-2],False)],('retry_policy.md','retry_widget.py','request_client.py'))
add('cursor_order','Pagination loses or repeats records when IDs arrive out of order.',
    'return [v for v in x[0] if v > x[1]][:x[2]]',
    'x=[ids,cursor,limit]. Return distinct IDs strictly greater than cursor, numerically ascending, then apply limit. A nonpositive limit returns no IDs.',
    ['return sorted(set(v for v in x[0] if v > x[1]))[:max(0,x[2])]',
     'return sorted(v for v in x[0] if v > x[1])[:max(0,x[2])]',
     'return sorted(set(v for v in x[0] if v >= x[1]))[:max(0,x[2])]',
     'return sorted(set(v for v in x[0] if v > x[1]))[:x[2]]'],
    [([[5,3,3,2,4],2,3],[3,4,5]),([[2,3],2,3],[3]),([[1,2,3],0,-1],[]),([[],0,2],[])],('cursor_protocol.md','list_view.py','feed_client.py'))
add('zero_override','Explicitly disabling the timeout sometimes restores the default.',
    'return x[0] or x[1]',
    'x=[override,default]. Only None requests the default. Zero disables timeout; negative values are rejected upstream and must be passed through here, not clamped.',
    ['return x[1] if x[0] is None else x[0]','return x[0] or x[1]',
     'return x[1] if x[0] is None else max(0,x[0])','return x[0] if x[0] else 0'],
    [([0,30],0),([None,30],30),([-2,30],-2),([4,30],4)],('timeout_rules.md','settings_view.py','socket_client.py'))
add('role_gate','A role check behaves incorrectly for users with multiple roles.',
    'return set(x[0]) == set(x[1])',
    'x=[user_roles,required_roles]. Access requires every required role. Empty required_roles means unrestricted. Extra user roles are harmless.',
    ['return set(x[1]).issubset(set(x[0]))','return bool(set(x[0]) & set(x[1]))',
     'return bool(x[1]) and set(x[1]).issubset(set(x[0]))','return set(x[0]).issubset(set(x[1]))'],
    [([['a','b'],['a']],True),([['a'],['a','b']],False),([[],[]],True),([['a'],[]],True),([[],['a']],False)],('access_policy.md','role_badge.py','identity_client.py'))
add('latest_completion','Overlapping login attempts sometimes display an obsolete completion.',
    'return x[0][-1][1] if x[0] else None',
    'x=[completion_events,current_generation]. Each event is [generation,result] in arrival order. Only events matching current_generation are eligible; use the last such event. No eligible event yields None. Failed results may be None and must not be skipped.',
    ['return next((v for g,v in reversed(x[0]) if g == x[1]),None)',
     'return next((v for g,v in reversed(x[0]) if g == max(e[0] for e in x[0])),None)',
     'return next((v for g,v in x[0] if g == x[1]),None)',
     'return next((v for g,v in reversed(x[0]) if g == x[1] and v is not None),None)'],
    [([[[2,'new'],[1,'old']],2],'new'),([[[1,'old']],2],None),([[[2,'ok'],[2,None]],2],None),([[[2,'a'],[2,'b']],2],'b'),([[],2],None)],('attempt_lifecycle.md','login_button.py','auth_client.py'))
add('interval_touch','Availability intervals that merely touch are incorrectly reported as conflicting.',
    'return x[0] <= x[3] and x[2] <= x[1]',
    'x=[a_start,a_end,b_start,b_end]. Intervals are half-open. Empty or reversed intervals have no occupied time. Return whether their occupied times overlap.',
    ['return x[0] < x[1] and x[2] < x[3] and max(x[0],x[2]) < min(x[1],x[3])',
     'return x[0] < x[2] < x[1] or x[2] < x[0] < x[3]',
     'return x[0] <= x[3] and x[2] <= x[1]',
     'return x[0] < x[3] and x[2] < x[1]'],
    [([0,2,2,4],False),([0,3,2,4],True),([2,2,0,4],False),([3,1,0,4],False),([0,4,2,2],False),([0,2,0,2],True)],('reservation_semantics.md','calendar_view.py','booking_client.py'))
add('duplicate_refresh','Refreshing an existing cache key unexpectedly changes eviction order.',
    'return list(dict(x).items())',
    'x is a sequence of [key,value] updates. Return [key,value] pairs from least to most recently updated. A repeated key replaces its value AND moves it to the end. Keys and values are strings.',
    ['d = {}; [(d.pop(k,None),d.update({k:v})) for k,v in x]; return [[k,v] for k,v in d.items()]',
     'return [[k,v] for k,v in dict(x).items()]',
     'return [[k,v] for k,v in sorted(dict(x).items())]',
     'd = {}; [d.setdefault(k,v) for k,v in x]; return [[k,v] for k,v in d.items()]'],
    [([['a','1'],['b','2'],['a','3']],[['b','2'],['a','3']]),([['z','1'],['a','2']],[['z','1'],['a','2']]),([],[])],('cache_contract.md','cache_panel.py','store_client.py'))
add('event_watermark','An incremental event reader drops late events with equal timestamps.',
    'return [e for e in x[0] if e[0] > x[1][0]]',
    'x=[events,watermark]. Each event and watermark is [timestamp,id]. Return every event lexicographically greater than the watermark, sorted lexicographically. IDs break equal timestamp ties. Do not deduplicate.',
    ['return sorted([e for e in x[0] if tuple(e) > tuple(x[1])])',
     'return sorted([e for e in x[0] if e[0] >= x[1][0]])',
     'return [e for e in x[0] if tuple(e) > tuple(x[1])]',
     'return sorted([e for e in x[0] if e[0] > x[1][0] or e[1] > x[1][1]])'],
    [([[[3,1],[2,4],[2,3],[1,9]],[2,3]],[[2,4],[3,1]]),([[[1,1],[1,1]],[0,0]],[[1,1],[1,1]]),([[],[0,0]],[])],('event_protocol.md','event_table.py','stream_client.py'))
add('case_identity','Identity matching disagrees between callers for international names.',
    'return x[0].lower() == x[1].lower()',
    'x=[left,right]. Apply Unicode casefold to both strings. Whitespace is significant and MUST NOT be stripped. No Unicode normalization beyond casefold is requested.',
    ['return x[0].casefold() == x[1].casefold()',
     'return x[0].strip().casefold() == x[1].strip().casefold()',
     'return x[0].lower() == x[1].lower()',
     'return x[0] == x[1]'],
    [(['Straße','STRASSE'],True),([' a','a'],False),(['A','a'],True),(['é','e'],False)],('identity_rules.md','name_input.py','directory_client.py'))
add('batch_ack','A batch acknowledgment drops records that should be retried.',
    'return [v for v in x[0] if v not in x[1]]',
    'x=[pending_ids,acked_ids]. Acknowledgments consume occurrences, not all equal IDs. For each ack remove the earliest remaining occurrence. Ignore unmatched acks. Preserve remaining order.',
    ['r = list(x[0]); [r.remove(a) for a in x[1] if a in r]; return r',
     'return [v for v in x[0] if v not in x[1]]',
     'r = list(reversed(x[0])); [r.remove(a) for a in x[1] if a in r]; return list(reversed(r))',
     'return sorted(set(x[0])-set(x[1]))'],
    [([[1,2,1,3],[1]],[2,1,3]),([[1,1,2],[1,1]],[2]),([[2,1],[9]],[2,1]),([[],[1]],[])],('ack_protocol.md','queue_view.py','broker_client.py'))
add('negative_bucket','Pre-epoch timestamps land in the wrong time bucket.',
    'return int(x[0] / x[1])',
    'x=[timestamp,width] with integer timestamp and positive integer width. Buckets are [k*width,(k+1)*width); return integer k. Must remain exact for arbitrarily large Python integers.',
    ['return x[0] // x[1]','return int(x[0] / x[1])',
     'return int(x[0] / x[1]) - (1 if x[0] < 0 else 0)','return round(x[0] / x[1])'],
    [([-1,10],-1),([-10,10],-1),([11,10],1),([0,10],0),([100000000000000000001,10],10000000000000000000)],('bucket_spec.md','timeline_view.py','metrics_client.py'))
add('empty_search','An optional search filter treats explicit empty selection as no filter.',
    'return x[0] if not x[1] else [v for v in x[0] if v in x[1]]',
    'x=[items,selected]. selected=None means unrestricted. selected=[] intentionally selects nothing. Otherwise preserve item order and duplicate occurrences whose values are selected.',
    ['return list(x[0]) if x[1] is None else [v for v in x[0] if v in x[1]]',
     'return list(x[0]) if not x[1] else [v for v in x[0] if v in x[1]]',
     'return list(set(x[0]) & set(x[1] or []))',
     'return [] if x[1] is None else [v for v in x[0] if v in x[1]]'],
    [([[3,1,3],None],[3,1,3]),([[1,2],[]],[]),([[3,1,3],[3]],[3,3]),([[],None],[])],('filter_spec.md','filter_dropdown.py','search_client.py'))
add('stable_priority','Equal-priority jobs run in inconsistent order after the priority fix.',
    'return sorted(x)',
    'x is a list of [job_id,priority]. Larger priority runs first. Ties retain original input order, NOT ID order. Duplicate IDs are allowed and must be retained.',
    ['return sorted(x,key=lambda e:-e[1])','return sorted(x,key=lambda e:(-e[1],e[0]))',
     'return sorted(x,key=lambda e:e[1])','return list(reversed(sorted(x,key=lambda e:e[1])))'],
    [([['z',2],['a',2],['b',3]],[['b',3],['z',2],['a',2]]),([['a',1],['a',2]],[['a',2],['a',1]]),([],[])],('scheduling_policy.md','job_list.py','worker_client.py'))
add('path_scope','A path-prefix authorization check admits sibling namespaces.',
    'return x[0].startswith(x[1])',
    'x=[path,scope], already canonical absolute POSIX paths with no trailing slash except root. Permit scope itself and descendants separated by slash. Root scope permits all absolute paths. No filesystem resolution here.',
    ['return x[1] == "/" or x[0] == x[1] or x[0].startswith(x[1]+"/")',
     'return x[0] == x[1] or x[0].startswith(x[1]+"/")',
     'return x[0].startswith(x[1])',
     'return x[0].startswith(x[1].rstrip("/")+"/")'],
    [(['/app2','/app'],False),(['/app/x','/app'],True),(['/app','/app'],True),(['/x','/'],True),(['/','/'],True)],('namespace_policy.md','path_picker.py','file_client.py'))
add('first_present','Configuration fallback ignores explicitly false feature flags.',
    'return next((v for v in x if v),None)',
    'x lists configuration values in descending precedence. Return the first value that is not None. False, zero, empty string and empty list are meaningful overrides. All None or empty input returns None.',
    ['return next((v for v in x if v is not None),None)',
     'return next((v for v in x if v),None)',
     'return next((v for v in reversed(x) if v is not None),None)',
     'return next((v for v in x if v is not None and v != ""),None)'],
    [([None,False,True],False),([None,0,4],0),([None,'','x'],''),([None,[],[1]],[]),([None,None],None),([],None)],('precedence_rules.md','flag_view.py','config_client.py'))

def evaluate(task,source):
    # Only repository-owned prewritten code is accepted, never API text.
    assert source in [task['source'],*task['candidates'].values()]
    ns={};exec(compile(source,'<owned-repair-fixture>','exec'),ns)
    failures=[]
    for n,(inp,expected) in enumerate(task['tests']):
        try:
            actual=ns['solve'](copy.deepcopy(inp))
            if actual != expected or type(actual) is not type(expected):failures.append(n)
        except Exception:failures.append(n)
    return {'pass':not failures,'failed_cases':failures,'total':len(task['tests'])}

def validate():
    report=[]
    for t in TASKS:
        outcomes={k:evaluate(t,v) for k,v in t['candidates'].items()}
        assert outcomes[t['correct']]['pass'],t['id']
        assert not evaluate(t,t['source'])['pass'],t['id']
        report.append({'task':t['id'],'passing':[k for k,v in outcomes.items() if v['pass']],'cases':len(t['tests'])})
    return report

if __name__=='__main__':
    import json
    print(json.dumps(validate(),indent=2))
