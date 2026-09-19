"""Posthoc same-response format replay. NOT a new independent quality run."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.decoding_control.providers import save
from research.flash_integration.tasks import fixtures,evaluate
from research.flash_integration.answer_codec import recover_response,preflight
from research.flash_integration.analyze import ARMS


def analyze(path):
 preflight();d=json.loads((path/'results.json').read_text(encoding='utf-8'));calls=json.loads((path/'calls.json').read_text(encoding='utf-8'));ts={t['id']:t for t in fixtures()};scores={};changes=[]
 for r in d['results']:
  t=ts[r['task']];bucket=scores.setdefault(t['kind'],{a:0 for a in ARMS})
  for arm,v in r['arms'].items():
   last=next(calls[i] for i in reversed(v['calls']) if calls[i]['stage'] in {'report','route','direct'})
   answer,reason=recover_response(t,last);ev=evaluate(t,answer);bucket[arm]+=ev.get('correct_labels',ev['correct'])
   if answer!=v['answer']:changes.append({'task':t['id'],'arm':arm,'reason':reason,'old':v['evaluation'],'new':ev})
 out={'kind':'posthoc_format_replay_NOT_new_inference','phase':d['manifest']['phase'],'scores':scores,'changes':changes,'codec_tests':preflight(),'new_provider_calls':0}
 save(path/'format_replay.json',out);save(Path(__file__).parent/(d['manifest']['phase']+'_format_summary.json'),out);return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args();print(json.dumps(analyze(a.path),indent=2))
