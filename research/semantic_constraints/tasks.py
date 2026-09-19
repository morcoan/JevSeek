"""Fresh synthetic deployment-matching problems with independent Boolean truth.
Only visible() is provider input. No model generates tests, truth or executed code.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import random

FEATURES=['durable','internet','gpu','arm','linux','public']
# Each sentence fully specifies ONE latent feature. Phrasings withheld by split.
TEXT={
 'durable':[
  ('Local files are discarded whenever the machine restarts.','Local files survive machine restarts.'),
  ('A reboot recreates an empty local data volume.','The local data volume retains its contents after reboot.'),
  ('Stored workload data is ephemeral across a restart.','Stored workload data remains intact across a restart.')],
 'internet':[
  ('Outbound public-internet connections are blocked.','Outbound public-internet connections are permitted.'),
  ('Public-network egress is prohibited by policy.','Policy allows egress to public-internet addresses.'),
  ('Workloads cannot initiate connections to the public internet.','Workloads may initiate connections to the public internet.')],
 'gpu':[
  ('No usable GPU is available to workloads.','A usable CUDA GPU is available to workloads.'),
  ('Workloads have CPU execution only, without a GPU.','Workloads can use a working NVIDIA CUDA accelerator.'),
  ('There is no working graphics accelerator for computation.','A functioning CUDA-capable accelerator is provided for computation.')],
 'arm':[
  ('Native binaries must target x86-64; no ARM emulation exists.','Native binaries must target ARM64; no x86 emulation exists.'),
  ('The processor runs AMD64 code and cannot emulate AArch64.','The processor runs AArch64 code and cannot emulate AMD64.'),
  ('This is a native Intel-compatible 64-bit platform, not an ARM platform.','This is a native 64-bit ARM platform, not an Intel-compatible platform.')],
 'linux':[
  ('The operating system is Windows Server, not Linux.','The operating system is Linux, not Windows.'),
  ('Its OS is Microsoft Windows rather than a Linux distribution.','Its OS is a Linux distribution rather than Microsoft Windows.'),
  ('Workloads run under the Windows operating system.','Workloads run under the Linux operating system.')],
 'public':[
  ('All hosted listeners are private-network only and unreachable from the public internet.','All hosted listeners are publicly reachable from the internet.'),
  ('Inbound service endpoints are confined to a private network.','Inbound service endpoints are exposed to the public internet.'),
  ('No external internet client can reach its workload listeners.','External internet clients can reach its workload listeners.')]
}
ATOMS={
 'durable':('local workload data is lost on restart','local workload data survives restart'),
 'internet':('outbound public-internet access is blocked','outbound public-internet access is allowed'),
 'gpu':('no usable compute GPU is present','a usable CUDA compute GPU is present'),
 'arm':('native x86-64 execution is provided without ARM emulation','native ARM64 execution is provided without x86 emulation'),
 'linux':('the operating system is Windows','the operating system is Linux'),
 'public':('listeners cannot be reached from the public internet','listeners can be reached from the public internet')
}


def truth(expr,bits):
    op=expr[0]
    if op=='atom':return bool(bits[expr[1]])==expr[2]
    if op=='and':return truth(expr[1],bits) and truth(expr[2],bits)
    if op=='or':return truth(expr[1],bits) or truth(expr[2],bits)
    if op=='not':return not truth(expr[1],bits)
    if op=='if':return not truth(expr[1],bits) or truth(expr[2],bits)
    raise ValueError(op)


def render(e,style):
    if e[0]=='atom':return ATOMS[e[1]][int(e[2])]
    a=render(e[1],style)
    if e[0]=='not':return 'it is NOT the case that ('+a+')'
    b=render(e[2],style)
    if e[0]=='and':return '('+a+') AND ('+b+')'
    if e[0]=='or':return 'at least one of ('+a+') OR ('+b+') holds; both are also acceptable'
    return 'if ('+a+'), then ('+b+'); when the if-condition is false this rule imposes no restriction'


def assignment(matrix,hosts,jobs):
    best=None;cost=None
    for chosen in itertools.permutations(hosts,len(jobs)):
        if all(matrix[(j,h)] for j,h in zip(jobs,chosen)):
            total=sum(hosts[h] for h in chosen)
            if cost is None or total<cost or (total==cost and chosen<tuple(best[j] for j in jobs)):
                best=dict(zip(jobs,chosen));cost=total
    return best,cost


def build(seed,split):
    r=random.Random(seed);style=2 if split=='confirmation' else seed%2
    for attempt in range(10000):
        latent={f'h{i}':dict(zip(FEATURES,[bool(r.getrandbits(1)) for _ in FEATURES])) for i in range(6)}
        costs={h:r.randrange(1,16) for h in latent};target=r.sample(list(latent),5);exprs={}
        for ji,host in enumerate(target):
            for trial in range(100):
                keys=r.sample(FEATURES,3);atoms=[['atom',key,bool(r.getrandbits(1))] for key in keys]
                kind=r.randrange(4)
                expr=(['and',atoms[0],atoms[1]] if kind==0 else ['and',atoms[0],['or',atoms[1],atoms[2]]] if kind==1 else ['and',atoms[0],['not',atoms[1]]] if kind==2 else ['and',atoms[0],['if',atoms[1],atoms[2]]])
                n=sum(truth(expr,b) for b in latent.values())
                if truth(expr,latent[host]) and 1<=n<=4:exprs[f'j{ji}']=expr;break
            else:break
        if len(exprs)<5:continue
        matrix={(j,h):truth(e,bits) for j,e in exprs.items() for h,bits in latent.items()}
        feasible=[p for p in itertools.permutations(latent,5) if all(matrix[(j,h)] for j,h in zip(exprs,p))]
        if len(feasible)<2:continue
        values={sum(costs[h] for h in p) for p in feasible}
        if len(values)<2:continue
        best,cost=assignment(matrix,costs,list(exprs))
        profiles={}
        for h,bits in latent.items():
            pieces=[TEXT[key][style][int(bits[key])] for key in FEATURES];r.shuffle(pieces)
            profiles[h]={'cost':costs[h],'profile':' '.join(pieces)}
        jobs={j:'The selected host must satisfy: '+render(e,style)+'. No other capability is required.' for j,e in exprs.items()}
        return {'id':split+'-'+str(seed),'split':split,'hosts':profiles,'jobs':jobs,'latent':latent,'expressions':exprs,
                'truth_matrix':{j+'_'+h:value for (j,h),value in matrix.items()},'oracle':{'assignment':best,'cost':cost},'feasible_assignments':len(feasible),'generator_attempt':attempt}
    raise RuntimeError('Fixture generation exhausted')


def visible(t):
    return {'goal':'Assign each service to exactly one host, with at most one service per host. Every host must satisfy its assigned service requirements. Among valid assignments minimize the SUM of the used host costs. Unused hosts cost nothing. All listed host facts are complete and definitive; do not assume emulation or additional capabilities.',
            'hosts':t['hosts'],'services':t['jobs']}


def evaluate(t,answer):
    jobs=list(t['jobs']);hosts=t['hosts']
    if not isinstance(answer,dict) or set(answer)!=set(jobs) or any(h not in hosts for h in answer.values()):return {'feasible':False,'optimal':False,'error':'shape'}
    if len(set(answer.values()))!=len(jobs):return {'feasible':False,'optimal':False,'error':'host_reused'}
    failed=[j for j,h in answer.items() if not truth(t['expressions'][j],t['latent'][h])]
    cost=sum(hosts[h]['cost'] for h in answer.values())
    return {'feasible':not failed,'optimal':not failed and cost==t['oracle']['cost'],'cost':cost,'violated_services':failed}


def all_tasks():return [build(87000+i,'development') for i in range(8)]+[build(97000+i,'confirmation') for i in range(24)]


def preflight():
    tasks=all_tasks()
    for t in tasks:
        assert evaluate(t,t['oracle']['assignment'])['optimal']
        matrix={(j,h):t['truth_matrix'][j+'_'+h] for j in t['jobs'] for h in t['hosts']}
        assert assignment(matrix,{h:v['cost'] for h,v in t['hosts'].items()},list(t['jobs']))==(t['oracle']['assignment'],t['oracle']['cost'])
        assert len(matrix)==30 and 0<sum(matrix.values())<30
        assert set(visible(t))=={'goal','hosts','services'}
    bits={f:False for f in FEATURES};bits['durable']=True
    assert truth(['if',['atom','gpu',True],['atom','internet',True]],bits)
    assert not truth(['and',['atom','durable',True],['atom','gpu',True]],bits)
    assert truth(['or',['atom','durable',True],['atom','gpu',True]],bits)
    assert not truth(['not',['atom','durable',True]],bits)
    for p,q in itertools.product([False,True],repeat=2):
        bits.update(durable=p,gpu=q)
        a=['atom','durable',True];b=['atom','gpu',True]
        assert truth(['and',a,b],bits)==(p and q)
        assert truth(['or',a,b],bits)==(p or q)
        assert truth(['not',a],bits)==(not p)
        assert truth(['if',a,b],bits)==((not p) or q)
    encoded=json.dumps(tasks,sort_keys=True,ensure_ascii=False).encode()
    return {'tasks':len(tasks),'pair_labels':960,'fixture_sha256':hashlib.sha256(encoded).hexdigest(),'all_oracle_assignments_pass':True}

if __name__=='__main__':print(json.dumps(preflight(),indent=2))
