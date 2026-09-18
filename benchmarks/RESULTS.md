# Jev JIT versus frozen preplanning — measured comparison

[← Research overview](../RESEARCH.md)

## Verdict
For this single programming task, JIT completed the work and both frozen-preplan variants failed. Prefer JIT for JevSeek. This is evidence on one task, not a general benchmark ranking or proof that all preplanning fails.

## Task and controls
Implement a dependency-aware incremental build engine from an unfinished starter. Contract in `build_engine/SPEC.md`: deterministic graph traversal, closure-wide validation, content hashing, precise invalidation, output-integrity checking, failure recovery and atomic manifest commits. No external dependencies.

Thirty evaluator-owned unittest tests live outside the agent workspace. Both modes start with identical implementation, specification, smoke test and an acceptance launcher. Unfinished starter passes 1/30 tests (the immutability test), with 1 failure and 28 errors. Tests were authored before either run. Test suite is substantial but not exhaustive (e.g. symlink escape is specified but not directly tested on this Windows host).

Shared runner: `compare_routing.py`.
- Jev pinned to `jev-1.13.0`; DeepSeek uses `deepseek/deepseek-chat`, temperature 0.
- No DeepSeek planning call. Jev chooses tool; DeepSeek supplies JSON arguments for that tool only.
- Four action choices: read/write/edit/bash. JIT additionally has a non-executing `done` decision.
- OpenHands FileEditorExecutor implements read/write/edit adapters. Bash uses subprocess and is restricted to the same two test commands for both arms. This is an experimental harness, not replacement production tools or a full OS sandbox.
- Full completed tool arguments and observations retained. No 300-character history truncation. Console previews are truncated, not model context.
- No tool-turn/call cap on JIT. Frozen plan ends at its predicted count. Per-process test timeout is 120 seconds, not a task/call budget.
- DeepSeek produces a final summary based on actual turns and independent evaluation. Summary text never executes.
- Independent evaluator runs again at the end of each arm; `done` or exhausted plan is not accepted as proof of success.

## Results

| Arm | Independent tests | Tool actions | Jev calls | DeepSeek calls, including summary | Wall time |
|---|---:|---:|---:|---:|---:|
| JIT | **30/30** | 12 | 13 | 13 | 23.72 s |
| Frozen preplan | 1/30 | 100 | 106 | 101 | 141.38 s |
| Frozen preplan, explicit scheduling wording | 1/30 | 3 | 10 | 4 | 14.01 s |

JIT sequence:
`read → read → read → edit → bash → edit → bash → edit → bash → edit → bash → bash → done`

It encountered real implementation failures (`KeyError: 'a'`, then `AttributeError` on a string used as a Path). Jev selected repairs/reruns based on observations. Public smoke and all acceptance tests eventually passed. DeepSeek's payload generation also made a failed repair; full observed feedback allowed another attempt.

Original frozen preplan:
- Narrowed 0–100 into the estimate **100** using six Jev calls.
- Scheduled all 100 tools before any execution; every choice was `read`.
- Execution was genuinely allowed to finish, not stopped early or patched to succeed.
- No implementation changes; tests remain at baseline.

Prompt-sensitivity check (separate run, same task/executor/tests):
- Added explicit clarification: count tool invocations, not requirements/tests/lines; one edit can implement a whole module.
- Added explicit offline scheduling semantics: assume earlier scheduled actions succeed; advance rather than repeating first action because no execution has happened yet.
- Estimate became **3**, but sequence remained `read/read/read`.
- Still no implementation changes. This addresses one obvious wording confound but is not an exhaustive search over planning prompts.
- Its final DeepSeek response failed the summary instruction and emitted proposed implementation/tool-call-like text instead. No tool call occurred; evaluation remained failure. A production summary should have no tools and should be checked for faithful reporting.

## Cache observations (DeepSeek API-reported usage)

| Arm | Prompt tokens summed over calls | Cache-hit tokens | Cache-hit fraction | Completion tokens |
|---|---:|---:|---:|---:|
| JIT | 172,345 | 123,392 | 71.6% | 2,750 |
| Frozen preplan | 1,815,814 | 1,729,792 | 95.3% | 3,429 |
| Explicit preplan | 21,441 | 3,072 | 14.3% | 2,925 |

High cache-hit percentage is not success or low total cost: the useless 100-read loop cached extremely well. JIT still had fewer total prompt tokens and completed the task. No pricing-based cost estimate is made here. Jev cache-hit fields were not measured. Original two arms recorded Jev model/confidence/timing but inadvertently omitted usage; the explicit variant captures the full raw response. Do not infer a Jev-cache benefit from DeepSeek cache numbers. Arms ran concurrently and shared a provider account; latency/cache results are descriptive, not an isolated causal performance study.

## Interpretation
- JIT decisions use **user intent + executed tool arguments + actual observations**, not another model's proposed plan. Previous-turn facts are necessary to repair errors.
- A frozen sequence must speculate about outcomes before seeing them. Estimating an exact count is especially brittle; TypeSafe also documents numerical reasoning and multi-hop indirection as Jev weaknesses.
- The tested preplan was a linear sequence, **not** a conditional decision tree. We did not test trees with branches, replanning, chunked planning or a richer symbolic state machine.
- Jev controls tool type, not arguments. It cannot alone ensure DeepSeek executes the right command/patch. Validate arguments and use real tests.
- Confidence is not authorization or proof. `done` should be checked against verification evidence.

Recommendation: intent → Jev next-tool/done → DeepSeek arguments → validated native tool → append actual result → repeat → DeepSeek factual summary. Keep the original intent and stable instructions at the front for cache reuse. Never invent planning context for Jev.

## Evidence and reproduction

- `results/jit-20260917-123541/`
- `results/pre-20260917-123541/`
- `results/pre_explicit-20260917-123724/`

These are historical evidence identifiers, not downloadable repository directories.
Raw outputs are retained in a private local archive and excluded from Git. Each
original directory contained `events.jsonl` (complete tool trace), `workspace/`,
independent `acceptance.txt`, and `result.json` (timings, metrics, summary). The
public runner/evaluator can generate new results with your own provider keys.

From project root, with dependencies installed and DS_KEY/JEV_KET in .env:

```sh
python benchmarks/compare_routing.py jit
python benchmarks/compare_routing.py pre
python benchmarks/compare_routing.py pre_explicit
```

API charges apply. No turn cap: interrupt manually if necessary; an interrupted run is incomplete, not a pass. Runs use new timestamped workspaces. Old `jev_jit.py` / `jev_pre.py` are historical flawed pilot scripts, not this experiment.
