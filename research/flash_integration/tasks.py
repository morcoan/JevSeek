from __future__ import annotations
import hashlib,itertools,json,random
from pathlib import Path
from research.semantic_constraints.tasks import build,FEATURES,visible as allocation_visible,evaluate as allocation_evaluate
from research.semantic_reliability.fresh_tasks import DOMAINS,render
from research.semantic_reliability.ordering import DATA,selection as old_ordering,parse
from research.semantic_reliability.transport import select_new as old_transport
from research.semantic_reliability.nli import selected as old_nli


def fixtures():
 tasks=[];domains=list(DOMAINS)
 for i in range(10):
  seed=621000+i;domain=domains[i%3];phrases=DOMAINS[domain];t=build(seed,'confirmation');rng=random.Random(seed+563)
  t['id']='allocation-'+str(seed);t['domain']=domain
  for h,bits in t['latent'].items():
   pieces=[phrases[k][int(bits[k])] for k in FEATURES];rng.shuffle(pieces);t['hosts'][h]['profile']=' '.join(pieces)
  t['jobs']={j:'The candidate must satisfy the following logical requirement: '+render(e,phrases)+'. No other condition is required.' for j,e in t['expressions'].items()}
  tasks.append({'id':t['id'],'kind':'allocation','phase':'development' if i<2 else 'confirmation','visible':allocation_visible(t),'hidden':t})
 old=old_ordering();exclude={x['id'] for part in ['development','confirmation'] for x in old[part]}|{x['id'] for x in old_transport()}
 raw=json.loads((DATA/'logical_deduction_seven_objects.json').read_text(encoding='utf-8'))['examples'];pool=[(i,r) for i,r in enumerate(raw) if 'seven-'+str(i) not in exclude];random.Random(621811).shuffle(pool)
 for k,(i,r) in enumerate(pool[:10]):
  tasks.append({'id':'ordering-seven-'+str(i),'kind':'ordering','phase':'development' if k<2 else 'confirmation','visible':{'problem':r['input']},'hidden':{'gold':r['target'][1]}})
 old_docs,_=old_nli();exclude={t['id'] for t in old_docs};data=json.loads((DATA/'contract-test.json').read_text(encoding='utf-8'));pool=[d for d in data['documents'] if 1000<=len(d['text'])<=18000 and 'test-'+str(d['id']) not in exclude];random.Random(622033).shuffle(pool)
 hypotheses={k:v['hypothesis'] for k,v in data['labels'].items()}
 for i,d in enumerate(pool[:10]):
  tasks.append({'id':'document-test-'+str(d['id']),'kind':'grounding','phase':'development' if i<2 else 'confirmation','visible':{'document':d['text'],'hypotheses':hypotheses},
                'hidden':{'gold':{k:v['choice'] for k,v in d['annotation_sets'][0]['annotations'].items()}}})
 return tasks


def evaluate(t,answer):
 if not isinstance(answer,dict):answer={}
 if t['kind']=='allocation':
  a=answer.get('assignment');result=allocation_evaluate(t['hidden'],a);return {**result,'correct':result['optimal'],'answered':a is not None}
 if t['kind']=='ordering':
  choice=answer.get('choice');return {'correct':choice==t['hidden']['gold'],'answered':choice is not None}
 gold=t['hidden']['gold'];pred=answer.get('answers');pred=pred if isinstance(pred,dict) else {};correct=sum(pred.get(k)==v for k,v in gold.items())
 return {'correct':correct==len(gold),'correct_labels':correct,'total_labels':len(gold),'answered_labels':sum(pred.get(k) in {'Entailment','Contradiction','NotMentioned'} for k in gold),
         'false_entailments':sum(pred.get(k)=='Entailment' and v!='Entailment' for k,v in gold.items())}


def check():
 tasks=fixtures();assert len(tasks)==30 and len({t['id'] for t in tasks})==30
 for t in tasks:
  if t['kind']=='allocation':
   h=t['hidden'];costs=[sum(h['hosts'][x]['cost'] for x in p) for p in itertools.permutations(h['hosts'],5) if all(h['truth_matrix'][j+'_'+x] for j,x in zip(h['jobs'],p))]
   assert min(costs)==h['oracle']['cost'];assert evaluate(t,{'assignment':h['oracle']['assignment']})['correct']
  elif t['kind']=='ordering':assert len(parse(t['visible']['problem'])[0]['objects'])==7
  else:assert len(t['hidden']['gold'])==17 and set(t['hidden']['gold'])==set(t['visible']['hypotheses'])
 return {'tasks':30,'development':6,'confirmation':24,'allocation_optima_verified':10,'fixture_sha256':hashlib.sha256(json.dumps(tasks,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
