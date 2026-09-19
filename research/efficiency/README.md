# Jev for lower-latency bounded decisions

**Research result:** a compact native Jev endpoint was faster than both thinking and nonthinking Flash on the tested finite-choice service, with equal observed accuracy. Sharing the catalogue cut Jev's own input tokens by52.7%, but Jev still reported MORE total tokens than Flash. This is not a blanket token/cost or full-agent speedup claim.

- [Results and limits](RESULTS.md)
- [Frozen protocol](PROTOCOL.md)
- `fastpath.py`: reusable opt-in selector and deterministic renderer.
- `audit_existing.py`: retrospective accounting, no inference.
- `experiment.py`, `analyze.py`, `preflight.py`: bounded reproduction and checks.

## What to replace

Use this only when an application already has:
1. a small finite catalogue of concrete procedures/answers with their arguments already bound;
2. one or more semantic selection questions;
3. permission and freshness checks outside the neural model.

Instead of Flash generating IDs/JSON or calling Jev and then repeating its result:

**shared catalogue + questions -> one native Jev batch -> validate IDs -> code renders existing data.**

Do NOT add this as an extra critic to an already successful Flash workflow. Prior experiments found that additive helpers often made the entire workflow slower. Do not use it to invent code, arbitrary command arguments, missing candidates or free-form explanations.

## Compact request representation

Verbose form repeats every description in every question's criteria. Compact form declares descriptions once in shared `state`; each `Choice` has the same allowed IDs mapped to `None`, with an explicit instruction to consult the shared catalogue. `Choice(criteria={id: None})` is supported by the installed TypeSafe SDK; this is not raw text truncation or a tokenizer trick.

This is suited to a COMMON option catalogue shared by multiple independent questions. It does not justify removing entity-specific evidence or recreating the identity-binding errors seen in prior planning studies. Source descriptions and query meanings must stay intact.

## Usage

```python
from research.decoding_control.providers import credentials, jev_client
from research.efficiency.fastpath import select

_, key = credentials()  # existing private vault/.env helper
client = jev_client(key)
try:
    row, trace = select(client, catalogue, questions, compact=True)
finally:
    client.close()
```

`catalogue` is an ID-keyed mapping. Every entry has a `description` string and a JSON-compatible `call` value supplied by the caller; `NONE` has a description of the unavailable case and `call=None`. `questions` maps unique question IDs to requested behaviors. In this prototype the selection criterion is **which single procedure's declared assertions exercise the whole requested behavior**. Different semantic tasks need a separately evaluated policy, not an unsupported universal routing claim.

Output contains selected IDs and deep-copied existing calls as DATA. It never executes them. `execution_authorized`, `executed` and `semantic_verification` stay false. Invalid/incomplete responses return no result; no guess, confidence-as-truth rule or automatic semantic retry. Up to30questions/255options; untruncated requests over60000UTF8JSON bytes fail closed.

If an LLM has to construct the catalogue, extract the questions, interpret a NONE result or write a narrative answer, those costs must be added. This study does not measure them. Selecting a valid ID does not authorize an operation, establish source truth or prove the target test will find every bug.

## Reproduce

```sh
python research/efficiency/preflight.py
python research/efficiency/audit_existing.py
# Explicit opt-in to provider requests:
python research/efficiency/experiment.py --phase development --run
python research/efficiency/analyze.py PRIVATE_DEVELOPMENT_DIRECTORY
python research/efficiency/experiment.py --phase confirmation --development PRIVATE_DEVELOPMENT_DIRECTORY --run
python research/efficiency/analyze.py PRIVATE_CONFIRMATION_DIRECTORY
```

No local model, VM, application patch or external dataset download is required. Credentials follow the existing vault-first helper; never print/export them. Private request/response traces remain under ignored `.local/research/efficiency/`. Used confirmation batches are not new heldout evidence on rerun.
