"""Third-party BBH ordering adapter: typed semantic compilation, exact enumeration.
Parser extracts only document layout/entities, not statement meaning or answers.
"""
from __future__ import annotations
import hashlib,itertools,json,random,re
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
DATA=ROOT/'.local/research/semantic-reliability/data'
REVISION='9ee07bd481feebf959a6b59d61ea57bdcf30964d'


def parse(text):
 body,optiontext=text.split('\nOptions:\n')
 body=body.split('. ',2)[2];intro,remainder=body.split('.',1)
 heading,listing=intro.split(':',1)
 entities=[re.sub(r'^(?:and\s+)?(?:a\s+|an\s+|the\s+)?','',s.strip()) for s in listing.split(',')]
 assert 3<=len(entities)<=7 and len(set(entities))==len(entities)
 # Axis convention is explicit, never inferred from reference answers.
 axis='price' if 'fruit stand' in heading else 'age' if 'car show' in heading else 'rank' if 'golf tournament' in heading else 'horizontal'
 context={'objects':{f'e{i}':name for i,name in enumerate(entities)},'axis':axis,
          'position1':{'price':'cheapest','age':'oldest','rank':'highest finisher','horizontal':'leftmost'}[axis],
          'positionN':{'price':'most expensive','age':'newest','rank':'lowest finisher','horizontal':'rightmost'}[axis]}
 statements=[s.strip() for s in remainder.split('.') if s.strip()]
 options=dict(re.findall(r'^\(([A-G])\) (.+)$',optiontext,re.M))
 assert len(options)==len(entities) and len(statements)<=12
 return context,statements,options


def catalog(context):
 ids=list(context['objects']);n=len(ids);items=[]
 for a,b in itertools.permutations(ids,2):
  x,y=context['objects'][a],context['objects'][b]
  comparison={'horizontal':f'{x} is to the left of {y}','rank':f'{x} finished above {y}','age':f'{x} is older than {y}','price':f'{x} is less expensive than {y}'}[context['axis']]
  items.append((['before',a,b],comparison+' (its canonical position number is smaller).'))
 for a in ids:
  for k in range(1,n+1):
   name=context['objects'][a]
   description=f'{name} is exactly in canonical position {k} counting from {context["position1"]}; equivalently position {n+1-k} counting from {context["positionN"]}.'
   items.append((['at',a,k],description));items.append((['not_at',a,k],'It is NOT the case that '+description))
 return {f'c{i}':{'expression':e,'meaning':s} for i,(e,s) in enumerate(items)}


def specs(context,statements,options):
 choices=catalog(context);criteria={'unsupported':'The sentence cannot be represented by exactly one listed constraint, or its meaning is unclear.',**{k:v['meaning'] for k,v in choices.items()}}
 base='Map the source sentence to ONE exactly equivalent listed ordering constraint. This is translation of that sentence only, not deduction using other statements. Do not substitute a weaker or stronger condition. Use the explicit canonical axis; counts are one-indexed. Choose unsupported rather than invent a rule. '
 qs={}
 for i,sentence in enumerate(statements):qs['rule'+str(i)]={'instructions':base+'CONTEXT: '+json.dumps(context)+'\nSOURCE SENTENCE: '+sentence,'criteria':criteria}
 for key,sentence in options.items():qs['option'+key]={'instructions':base+'CONTEXT: '+json.dumps(context)+'\nSOURCE SENTENCE: '+sentence,'criteria':criteria}
 return qs,choices


def holds(expr,positions):
 if expr[0]=='before':return positions[expr[1]]<positions[expr[2]]
 if expr[0]=='at':return positions[expr[1]]==expr[2]
 if expr[0]=='not_at':return positions[expr[1]]!=expr[2]
 raise ValueError('unknown_constraint')


def solve(context,statements,options,answers):
 qs,choices=specs(context,statements,options)
 if set(answers)!=set(qs) or any(v not in qs[k]['criteria'] for k,v in answers.items()):return {'choice':None,'status':'invalid_schema'}
 # Unsupported clauses are not silently dropped.
 if any(v=='unsupported' for v in answers.values()):return {'choice':None,'status':'unsupported_translation'}
 rules=[choices[answers['rule'+str(i)]]['expression'] for i in range(len(statements))]
 candidates={k:choices[answers['option'+k]]['expression'] for k in options}
 objects=list(context['objects']);worlds=[]
 for ordering in itertools.permutations(objects):
  pos={obj:i+1 for i,obj in enumerate(ordering)}
  if all(holds(e,pos) for e in rules):worlds.append(ordering)
 if not worlds:return {'choice':None,'status':'inconsistent_translation'}
 entailed=[key for key,e in candidates.items() if all(holds(e,{o:i+1 for i,o in enumerate(w)}) for w in worlds)]
 return {'choice':entailed[0] if len(entailed)==1 else None,'status':'conditional_entailment' if len(entailed)==1 else 'ambiguous_translation',
         'possible_orderings':len(worlds),'entailed_options':entailed,'constraints':rules,'query_constraints':candidates,'semantic_proof':False}


def selection():
 rng=random.Random(340171);development=[];confirmation=[];hashes={}
 for word in ['three','five','seven']:
  path=DATA/('logical_deduction_'+word+'_objects.json');raw=json.loads(path.read_text(encoding='utf-8'));hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
  pool=[]
  for i,x in enumerate(raw['examples']):
   context,rules,options=parse(x['input']);qs,choices=specs(context,rules,options)
   assert len(choices)+1<=255 and x['target'][1] in options
   pool.append({'id':word+'-'+str(i),'size':len(context['objects']),'input':x['input'],'target':x['target'][1]})
  rng.shuffle(pool)
  if word in ['three','five']:development+=pool[:6];pool=pool[6:]
  if word in ['five','seven']:confirmation+=pool[:24]
 return {'dataset':'BIG-Bench-Hard logical deduction','repository_revision':REVISION,'seed':340171,'source_sha256':hashes,'development':development,'confirmation':confirmation}

if __name__=='__main__':
 d=selection();p=DATA/'ordering-selection.json'
 if p.exists():assert json.loads(p.read_text(encoding='utf-8'))==d
 else:p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'parsed_cases':750,'development':len(d['development']),'confirmation':len(d['confirmation']),'selection_sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
