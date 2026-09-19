# Results: generic prefix selection regressed; narrow constraint signal remains exploratory

2026-09-18. Real `deepseek-flash` non-thinking and `jev-1.13.0` calls. Model IDs
are provider aliases, not immutable checkpoints. No application changes.
[Protocol](PROTOCOL.md) · [Investigation](README.md) · [Aggregate](summary.json).

## A. Transport feasibility

Three separate capability calls verified twelve-token truncation, top-five
logprobs with reconstructible output bytes, exact text-prefix resumption, and
correct resulting SQL. Sum of request times3.108s. Not a quality benchmark or
proof of native token-ID/KV-cache control.

## B. Frozen one-checkpoint decoder pilot

12 new hand-authored SQL task families,20 private-to-evaluator databases per task.
108 DeepSeek +12 Jev requests,0 recorded API errors/retries. Every common prefix
and every one of36 proposed blocks was unfinished. No planned approaches or final
queries were shown to selectors. All decisions occurred before suffix generation.

| Policy | Passes | Interpretation |
|---|---:|---|
| Direct uninterrupted DeepSeek |9/12| No Jev, no pauses |
| First paused/resumed continuation |9/12| Controls segmentation/transport |
| DeepSeek selects among partial continuations |8/12| Same prefix pool as Jev |
| Jev selects among partial continuations |6/12| Regresses against both controls |
| Conservative Jev veto |9/12| Zero veto triggers; identical to first-branch control |
| Uniform random candidate, expected |9.67/12| No additional sampled run |
| Any observed branch passes |11/12| Retrospective pool coverage, not an achievable oracle |

Jev versus paused:2 rescues,5 regressions. Versus direct:1 rescue,4 regressions.
Jev versus self-selector:1 rescue,3 regressions. The paused control and direct
have equal totals but DIFFERENT task failures:2 rescues/2 regressions between them.
This matters: a changed prefix API trajectory is not itself a Jev effect.

### What went wrong

1. **Early text often provided no meaningful decision.** Nine pools contained
   whitespace-equivalent duplicates; five had all three blocks exactly identical.
   Across36 proposed blocks there were22 unique exact within-task prefixes.
2. **Jev abstained five times.** Four were pools where every sampled completion
   later passed. Its instructions said `none` meant all continuations unusable,
   not 'several choices look equivalent.' Those abstentions count as failures,
   not speed wins. The DeepSeek selector abstained twice.
3. **Missing future information:** a visible prefix that has not established a
   constraint may still add a valid join/filter later. Generic future-quality
   judgment was unreliable. The conservative conflict gate never crossed0.8;
   it therefore made no changes and added overhead without improving quality.
4. **No correct continuation support in one case:** all three `ordered_sequence`
   completions omitted the actual-person restriction and failed. Picking among
   that particular pool cannot rescue it; it does not prove the generator could
   never write the correct solution on another attempt.
5. **The narrow promising fork was inconsistent:** for `running_net`, Jev chose
   an actual-people membership filter over mere `IS NOT NULL`, and that continuation
   passed. For `cohort_retention`, it chose a prefix lacking that same restriction
   and the completion failed. Direct cohort SQL also contained an invalid alias.

### Duplicate-prefix confound, disclosed rather than hidden

The frozen protocol generated one suffix per candidate INDEX. Two identical
prefixes can therefore receive different stochastic suffixes. In one case
(`exact_categories`), duplicate prefixes led to different pass/fail outcomes.
A selector cannot predict which invisible independent sample it will receive from
identical text; treating that as semantic selection ability would be misleading.

A local-only diagnostic canonicalized duplicate visible prefixes to the lowest
candidate index's completion. Self-selection changes8/12->7/12; Jev remains6/12
and veto9/12. Original scores remain above, not overwritten. The separate follow-up
below deduplicates before scoring. This still uses one rollout per unique prefix,
not a calibrated estimate of future correctness.

### Observed per-task scores

| Task | Direct | Paused first | Self | Jev |
|---|---|---|---|---|
| Fanout-safe totals |Pass|Pass|Pass|Fail|
| Every individual order funded |Pass|Pass|Pass|Pass|
| Exact required category set |Pass|Fail|Pass|Pass|
| Cumulative net by actual person/day |Pass|Fail|Fail|Pass|
| First threshold-crossing day |Pass|Pass|Pass|Pass|
| Status as of each order |Pass|Pass|Pass|Fail|
| First eligible payment day's total |Pass|Pass|Pass|Fail|
| Person/team fractional share |Pass|Pass|Pass|Pass|
| Largest payment day with tie rule |Pass|Pass|Fail|Fail|
| Red then blue without intervening green |Fail|Fail|Fail|Fail|
| Rolling distinct categories |Fail|Pass|Pass|Pass|
| Cohort retention |Fail|Pass|Fail|Fail|

Many errors concerned orphan IDs. These fixtures intentionally exercise the
explicit no-foreign-key schema and edge cases; they do not represent average
production database distributions. Other data/task families may behave differently.

### Latency and usage

Counterfactual serial sums of recorded calls, NOT separately timed production
arms. They include proposal blocks and selection, not only the eventual suffix.
Cache state, call order, network/load and different suffix lengths are confounders.

| Policy | Median seconds | Sum over12tasks | DeepSeek input/output | Jev input/output |
|---|---:|---:|---:|---:|
| Direct |1.178|14.002|4,020 /1,584|0 /0|
| Paused first |2.615|31.472|12,636 /1,677|0 /0|
| Self-select |4.872|57.346|26,860 /2,240|0 /0|
| Jev-select |4.187|49.231|19,102 /1,696|12,787 /1,291|
| Jev veto |4.563|54.779|20,964 /2,253|12,787 /1,291|

**Jev-select does not finish five tasks**, so its low-ish output-token count is not
evidence of equivalent completed work. Veto finishes all branches but achieves
no score gain, using1.42x DeepSeek output tokens plus Jev usage and much more input
processing. Even pausing without Jev raises summed latency by about2.25x here.
API serialization matters before adding any purported intelligence benefit.

Actual WHOLE pilot, including every counterfactual suffix:

- DeepSeek40,534 input (13,824 cache-hit),6,419 output tokens.
- Jev12,787 input,1,291 output tokens.
- Sum of all120 request times100.955s, not total research wall time.
-29/36 generated branch completions pass all20fixtures.

Do not sum the policy rows as actual billing: they reuse shared calls. Provider
bills/FLOPs/memory/energy were not measured. Different provider tokens are not
interchangeable compute units. No speed or memory improvement demonstrated.

## C. Post-hoc constraint-recognition diagnostic

This was designed AFTER seeing B and fixed before its own provider calls. It
cannot independently confirm a newly discovered hypothesis. The focus was a
specific already-stated obligation: restrict output-person rows to actual people.
It did NOT send evaluator results or complete unseen suffixes to Jev.

Reuse saved generator trajectories; no new DeepSeek calls. Compare original short
prefixes with an additional128characters of lookahead from their saved suffixes.
Exact duplicate visible prefixes are canonicalized. Jev supplies a Noul score for
explicit membership-anchor evidence, NOT whole-answer correctness. Keep the first
branch unless an alternative scores>=0.75 and exceeds it by>=0.20. Unresolved is
not equivalent to wrong. See [GAP_PROTOCOL.md](GAP_PROTOCOL.md).

| Visibility | First | Jev constraint selector | Literal `people` baseline | Pool coverage |
|---|---:|---:|---:|---:|
| Original short prefixes |9/12|9/12|10/12|11/12|
| +128characters lookahead |9/12|10/12|10/12|11/12|

The longer-view Jev policy changed exactly one choice: `running_net`, with a
correct explicit membership prefix scoring0.76 versus0.05 for alternatives. With
less context its score was0.54 and the conservative policy did not switch.
One rescue, no regressions among these cached completions. **The simple literal
baseline matches or exceeds Jev, so the signal is not uniquely neural.** That
literal rule is not a general correctness checker and can fail on irrelevant
mentions, aliases, unused CTEs or more complex domain constraints.

17 real Jev calls (single-unique pools bypassed),0 errors;16,906 input/824 output
tokens;2.976s summed and0.165s median request time. Three of36 longer candidate
views were already complete;33 remained unfinished. None of the short views was
complete. The observed rescue used unfinished text.

**These are selections over cached rollouts, NOT a new9->10 live accuracy win.**
The criterion was selected after inspecting errors, thresholds are uncalibrated,
and lookup of cached longer prefixes is not free lookahead in deployment. A real
decoder must generate those tokens and handle its own subsequent trajectory.
No claim of general reasoning improvement, small-model uplift or native-thinking
speedup follows from this diagnostic.

## Verification and boundaries

- Python reference functions checked against12 hand-calculated fixtures before
  inference;240 seeded reference evaluations, valid/invalid SQL examples, and
  five execution guards checked locally. No whole-app test suite run.
-48 actual generated queries re-evaluated from saved records with unchanged
  results. Protocol/source hashes match their frozen manifests. Both selectors
  preceded suffixes, and every continuation preserved the committed prefix exactly.
- A first launcher attempt hit a Python parameter-name collision BEFORE any
  provider request. Its manifest/log are preserved. Only the wrapper name was
  fixed before the successful frozen run; no quality results were retried.
- Main pilot + capability probe + follow-up:111 DeepSeek and29 Jev requests in all.
  No further inference, prompt tuning, threshold search, training or agent task run.
- Raw evidence is private/ignored; aggregate and reproducible source are local.
  No source push, app build, VM restart, benchmark restart or model-server changes.

**Decision: do not deploy generic Jev prefix ranking.** Further investigation, if
requested, should test observable semantic-constraint state at meaningful forks,
with preserved base behavior and independently chosen tasks where a literal check
is inadequate. A learned prefix-value scorer remains a different, training-based
research path—not a capability established for off-the-shelf Jev here.
