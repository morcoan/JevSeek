"""Fresh authored agent checkpoints. No provider code or private user traces."""
from __future__ import annotations
import copy,hashlib,json,random

REQUIREMENTS=[
 'The addressed recipient must actually receive the notification under the current consumer contract.',
 'Replaying the same logical notification with the same token must not deliver it twice.',
 'International notification text, including Japanese characters, must survive the wire byte-for-byte.'
]
PROBES={
 'delivery':'Submit an addressed envelope and inspect the recipient that actually received it, not merely the HTTP status.',
 'dedupe':'Submit one logical notification twice using the same request token and assert exactly one delivered notification.',
 'unicode':'Roundtrip accented Latin and Japanese text through the actual wire encoding and consumer decoder, asserting exact text equality.',
 'schema':'Check that configuration parses as JSON and all three values are strings.',
 'health':'Ping the service process and verify its health endpoint returns HTTP200; does not send a notification.',
 'ascii':'Roundtrip plain ASCII text only; non-ASCII behavior is not exercised.',
 'tls':'Check the mocked transport has TLS enabled; payload fields and delivery semantics are not tested.',
 'status':'Submit a request and check accepted status; the asynchronous consumer may still drop or duplicate it.'
}


def outcomes(config,expected):
 # Owned functional service simulation: actual encoding, addressed delivery, deduplication.
 def submit(text,nonce,seen,delivered):
  envelope={config['receiver_key']:'user-7','message':text};headers={config['token_header']:nonce}
  try:wire=json.dumps(envelope,ensure_ascii=False).encode(config['wire_codec']);decoded=json.loads(wire.decode('utf-8'))
  except (UnicodeError,LookupError,ValueError):return
  if decoded.get(expected['receiver_key'])!='user-7':return
  key=headers.get(expected['token_header'])
  if key and key in seen:return
  if key:seen.add(key)
  delivered.append(decoded['message'])
 seen=set();delivered=[];submit('hello','N0',seen,delivered);delivery=delivered==['hello']
 seen=set();delivered=[];submit('hello','N1',seen,delivered);submit('hello','N1',seen,delivered);dedupe=delivered==['hello']
 text='R\u00e9sum\u00e9 \u6771\u4eac';seen=set();delivered=[];submit(text,'N2',seen,delivered);unicode=delivered==[text]
 return {'delivery':delivery,'dedupe':dedupe,'unicode':unicode,'schema':all(isinstance(v,str) for v in config.values()),'health':True,'ascii':True,'tls':True,'status':True}


def fixtures():
 tasks=[]
 for i in range(12):
  rng=random.Random(731001+i);kind=['memory','coverage','loop'][i//4];name=['Cedar','Atlas','Harbor','Nimbus'][i%4];project=name+'-'+str(i)
  expected={'receiver_key':'dest_'+format(rng.getrandbits(24),'06x'),'token_header':'X-Replay-'+format(rng.getrandbits(20),'05x'),'wire_codec':'utf-8'}
  raw=[
   ('Consumer routing note',f'{project}: the current consumer locates the addressed user in the envelope member `{expected["receiver_key"]}`. A successful transport acknowledgement does not imply any recipient was resolved.'),
   ('Replay incident resolution',f'{project}: the receiving worker collapses repeated logical sends only when the stable token is supplied as HTTP field `{expected["token_header"]}`. A new attempt number is not a logical-send identifier.'),
   ('Wire interoperability note',f'{project}: the receiver decodes message bytes as UTF-8. Full text must survive, including accents and Japanese characters; ASCII-only smoke checks do not establish this.')]
  records=[]
  for title,text in raw:records.append({'title':title,'text':text,'scope':project,'revision':'current','kind':'observation'})
  # Same-project lexical distractors, other-project facts, obsolete snapshots. Random placement.
  for n in range(147 if kind=='memory' else 0):
   topic=['notification health endpoint','recipient display styling','retry dashboard counters','international help documentation','JSON schema audit','TLS maintenance'][n%6]
   records.append({'title':topic,'text':f'{project if n%3 else "OtherService"}: {topic}. This operational note concerns monitoring or presentation, not envelope routing, logical-send identity or full wire roundtrip. Ticket {rng.randrange(100000)}. Current dashboard values should not be copied into client configuration.',
                   'scope':project if n%3 else 'OtherService','revision':'obsolete' if n%7==0 else 'current','kind':'observation'})
  rng.shuffle(records)
  for n,r in enumerate(records):r['id']='r'+format(n,'03d')
  relevant=[r['id'] for r in records if r['title'] in {x[0] for x in raw}]
  keys=list(PROBES);rng.shuffle(keys);catalog={f'p{n}':{'description':PROBES[k]} for n,k in enumerate(keys)};probe_map={f'p{n}':k for n,k in enumerate(keys)}
  cfg={'receiver_key':'recipient','token_header':'X-Request-ID','wire_codec':'ascii'}
  if kind=='coverage':
   cfg=dict(expected)
   if i%4<3:cfg[list(cfg)[i%4]]=['recipient','X-Attempt','ascii'][i%4]
  history=[]
  if kind=='loop':
   states=[]
   if i%4==0:
    cfg={**expected,'receiver_key':'recipient'};states=[dict(cfg)]*3
   elif i%4==1:
    cfg={**expected,'token_header':'X-Attempt'};states=[dict(cfg)]*3
   else:
    states=[{'receiver_key':'recipient','token_header':'X-Attempt','wire_codec':'ascii'},
            {**expected,'token_header':'X-Attempt','wire_codec':'ascii'},
            {**expected,'wire_codec':'ascii'}];cfg=dict(states[-1])
   for n,s in enumerate(states):
    failures=[k for k,v in outcomes(s,expected).items() if k in {'delivery','dedupe','unicode'} and not v]
    history.append({'seq':n+1,'operation':['rewrite transport settings','adjust sender invocation','repeat consumer probe'][n],
                    'config':s,'failing_probes':failures,'output':['consumer contract assertion not satisfied','notification expectation failed again','observed delivery does not meet declared behavior'][n]})
  receipts=[{'probe':p,'revision':0,'passed':True} for p,k in probe_map.items() if k in {'schema','health','ascii'}]
  task={'id':kind+'-'+str(731001+i),'kind':kind,'goal':f'Resume maintenance of {project}. Configure the notification client to the CURRENT consumer contract and verify ALL three required behaviors on the resulting current revision. Do not count stale or merely healthy-process checks as behavioral proof. Use at most three probes per configure call.',
        'requirements':REQUIREMENTS,'project':project,'config':cfg,'revision':1,'receipts':receipts,'history':history,'records':records,'probe_catalog':catalog,
        'hidden':{'expected':expected,'probe_map':probe_map,'relevant_records':relevant}}
  tasks.append(task)
 return tasks


def fixture_hash():return hashlib.sha256(json.dumps(fixtures(),sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def evaluate(task,config,revision,receipts,finished):
 results=outcomes(config,task['hidden']['expected']);required={'delivery','dedupe','unicode'}
 verified={task['hidden']['probe_map'][r['probe']] for r in receipts if r['revision']==revision and r['passed']}
 behavior=all(results[k] for k in required);coverage=required<=verified
 return {'success':bool(behavior and coverage),'behavior_correct':behavior,'verified_current':coverage,'false_completion':bool(finished and not (behavior and coverage))}
