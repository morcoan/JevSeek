# Preregistered decision-selection pilot

Written before the first provider call. Scope: model-agnostic text-level intervention;
first generator DeepSeek Flash, non-thinking; selector Jev 1.13.0. No runtime change,
VM, Terminal-Bench, user-session content, arbitrary Python or shell execution.

## Hypothesis and decision rule

One Jev choice over three short generator-created approaches might improve final
correctness relative to the generator choosing among exactly the same approaches.
It must also justify its overhead relative to direct generation. No positive result
is assumed. A ceiling result or no recovery is grounds NOT to deploy this policy.
This 12-item hand-authored SQL pilot is an instrument/feasibility study, not a
statistically powered benchmark or evidence of general intelligence improvement.

## Frozen protocol

- Twelve task families in tasks.py, twenty deterministic evaluator-only databases
  per task, independent Python reference calculations. Report pass only if all
  twenty agree, preserving output multiplicity. These are not 240 independent tasks.
- Same schema and task requirements, no actual database contents, reference
  functions, test seeds, verifier outputs, or ground-truth answers sent to models.
- A: DeepSeek directly generates one new SQL query.
- DeepSeek then proposes three distinct short approaches, at most forty words each,
  in one JSON completion. They are model-written, not supplied correct answers.
- B: Choose the generator's first proposed approach (no judge).
- C: DeepSeek selects among the three approaches.
- D: Jev selects among those exact same approaches, in the same seeded shuffled
  display order as C. Neither judge sees a final query or test outcome. Candidate
  author identities and rankings not provided. Both may abstain via `none`.
- E: Uniform selection expected accuracy = number of passing plan completions / 3.
- F: Retrospective completion-pool oracle = any of the three plan-conditioned
  completions passes. This is NOT a proof a plan is correct or an achievable oracle:
  a good plan may be implemented badly, and implementation may repair a bad plan.
- Generate one final query for EACH plan, using the same final prompt/cap/settings.
  B/C/D reuse those exact completions to isolate selection instead of generating
  different answers per arm. Offline oracle work produces three answers; a deployed
  arm would produce only its chosen answer. Report actual research bill separately.
- Direct/candidate/self-selector/final calls have temperature .3/.7/0/.3 respectively;
  max output tokens 1000/600/200/1000. Thinking explicitly disabled for DeepSeek.
  Invalid, truncated, unavailable and errored outputs count as failures; no repair,
  hidden retries, cloud fallback or selective dropping. Max 72 DeepSeek +12 Jev
  calls. Provider SDK retries explicitly disabled for both providers (Jev defaults to
  two retries, overridden with RetryPolicy(max_retries=0)).
- Selectors run before any final completion/verifier evaluation. Selectors alternate
  call order across tasks; final completion order rotates independently by task.
  Cache/queue timing not randomized enough for a hardware or causal latency claim.
- Save prompts, candidates, selectors, final queries, exact requested/returned model
  IDs, raw reported usage and elapsed times privately; never credential material.
- SELECT/WITH queries execute only in fresh in-memory SQLite with query_only,
  restrictive authorizer, no extensions/file functions and instruction/output limits.

## Metrics

All-task pass counts; completion-pool coverage; judge selection accuracy conditional
on coverage; paired rescues/regressions; first-choice and expected random-selection
controls; selected-none count; candidate duplicates; total failure counts; observed
stage elapsed times and usage. Counterfactual serial arm latency sums common pool,
selector and selected final call times; it is NOT a directly measured production
wall-clock speedup. Include direct-generation cost, not only the final answer cost.
Unknown provider FLOPs, memory, energy and prices remain unknown. Token counts from
different providers are not a shared compute unit. Do not infer model weight from
API price or remotely hosted DeepSeek behavior.

## Limits and next study

Small synthetic set; hand-authored task selection; no held-out task-family generality;
no repeated generation seeds; test coverage incomplete; all three plans produced
in a single call may be near duplicates; a strong base model may reach ceiling.
No synthetic wrong options inserted after seeing outputs. Report negative results.
If there is headroom, next freeze a larger independent task set and generation
budget before running. Add a budget-matched DeepSeek-only deliberation arm and
position permutations, report paired confidence intervals, and replicate on a
second generator before claiming model-agnostic effectiveness. The interface can
be model-agnostic even when evidence is not.
