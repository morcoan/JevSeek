"""New seeds and capability vocabularies; no old confirmation outcomes reused."""
from __future__ import annotations
import hashlib,json,random
from research.semantic_constraints.tasks import build,FEATURES,ATOMS,TEXT

# Three distinct vocabularies, but the SAME Boolean/task generator; disclose this.
DOMAINS={
 'deployment':{
  'durable':('Restarting wipes the workload files.','Restarting preserves the workload files.'),
  'internet':('The egress firewall prohibits connections to public internet addresses.','The egress firewall permits connections to public internet addresses.'),
  'gpu':('Workloads have no functioning GPU for computation.','Workloads have access to a functioning CUDA GPU.'),
  'arm':('Native execution is x86-64 only; ARM code is not emulated.','Native execution is ARM64 only; x86 code is not emulated.'),
  'linux':('The installed operating system is Windows rather than Linux.','The installed operating system is Linux rather than Windows.'),
  'public':('Workload listeners are inaccessible to internet clients.','Workload listeners are accessible to internet clients.')},
 'test_runners':{
  'durable':('Test cases reuse one shared filesystem without fresh isolation.','Every test case receives a freshly isolated filesystem.'),
  'internet':('Outbound networking from tests is disabled.','Outbound networking from tests is enabled.'),
  'gpu':('There is no graphical display service for tests.','A graphical display service is provided for tests.'),
  'arm':('The runner cannot execute Python3.12 programs.','The runner can execute Python3.12 programs.'),
  'linux':('Creating symbolic links is prohibited for test processes.','Creating symbolic links is permitted for test processes.'),
  'public':('Test processes cannot start child processes.','Test processes can start child processes.')},
 'document_processors':{
  'durable':('Original input documents are erased immediately after processing.','Original input documents are retained for90days after processing.'),
  'internet':('Processing works without an internet connection.','Processing requires an internet connection.'),
  'gpu':('Scanned images are not accepted as document input.','Scanned images are accepted as document input.'),
  'arm':('Every document must be uploaded to an external cloud service.','Document contents always remain on premises and are never uploaded externally.'),
  'linux':('The output PDF contains only images, without searchable text.','The output PDF contains searchable text.'),
  'public':('Running the processor requires purchasing a paid license.','The processor may be used without purchasing a paid license.')}
}

def render(e,phrases):
 if e[0]=='atom':return phrases[e[1]][int(e[2])]
 a=render(e[1],phrases)
 if e[0]=='not':return 'NOT ('+a+')'
 b=render(e[2],phrases)
 if e[0]=='and':return '('+a+') AND ('+b+')'
 if e[0]=='or':return '('+a+') OR ('+b+'), with inclusive OR'
 return 'IF ('+a+') THEN ('+b+'); this implication is satisfied when its IF condition is false'

def tasks():
 result=[]
 for di,(domain,phrases) in enumerate(DOMAINS.items()):
  for i in range(16):
   seed=113000+di*1000+i;t=build(seed,'confirmation');r=random.Random(seed+563)
   t['id']=domain+'-'+str(seed);t['domain']=domain
   for h,bits in t['latent'].items():
    pieces=[phrases[k][int(bits[k])] for k in FEATURES];r.shuffle(pieces);t['hosts'][h]['profile']=' '.join(pieces)
   t['jobs']={j:'The candidate must satisfy the following logical requirement: '+render(e,phrases)+'. No other condition is required.' for j,e in t['expressions'].items()}
   result.append(t)
 return result

def fingerprint():return hashlib.sha256(json.dumps(tasks(),sort_keys=True,ensure_ascii=False).encode()).hexdigest()

if __name__=='__main__':print(json.dumps({'cases':len(tasks()),'hash':fingerprint()},indent=2))
