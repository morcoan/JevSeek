# DeepSeek-first pilot: no demonstrated Jev accuracy advantage

**2026-09-18; one frozen run, not a benchmark claim.**
Requested and returned generator ID: `deepseek-flash`, thinking disabled.
Requested and returned selector ID: `jev-1.13.0`. Aliases are not immutable weights.
[Protocol fixed before inference](PROTOCOL.md); [investigation and sources](README.md).

## Design

Twelve hand-authored, constraint-rich SQLite tasks. DeepSeek generates a direct
answer and three short approaches. DeepSeek and Jev choose among exactly the same
approaches before seeing any completed SQL or evaluator results. Each approach
then gets one DeepSeek-generated implementation, shared by both selectors.
Twenty deterministic databases and independent Python calculations check each
query; all twenty must agree. No reference answers/test rows are sent to providers.

These are **12 inference examples, not 240 independent examples**. The 36 completed
plan branches are research-only counterfactuals; a deployed selector would generate
one. No hidden retries, repair passes, post-result prompt edits, or excluded tasks.

## Accuracy

| Arm | Tasks passed | Meaning |
|---|---:|---|
| Direct DeepSeek | 9/12 | One answer, no proposals, no Jev |
| First proposed approach | 10/12 | Proposal stage but no judge |
| DeepSeek selects its own approach | 11/12 | Same candidate set as Jev |
| Jev selects approach | **11/12** | No accuracy gain over self-selection |
| Uniform random selection, expected | 10.33/12 | Average success over all three branches per task, not another API run |
| Retrospective completion-pool oracle | 12/12 | At least one of the three generated implementations passes |

Jev versus direct: **three rescues and one regression**, a net two tasks.
Jev versus first proposed approach: one rescue, no regressions.
Jev versus DeepSeek selection: **zero rescues and zero regressions**.
Selectors chose different approaches on five tasks, but their per-task pass/fail
outcomes were identical. Both succeeded on 11/12 covered tasks; neither abstained.
All twelve proposal pools were valid; no exactly duplicate plan strings. This does
not imply their approaches were semantically independent or equally diverse.

| Task | Direct | First | Self-select | Jev-select |
|---|---|---|---|---|
| NULL-safe exclusion | Pass | Pass | Pass | Pass |
| Latest event before filtering | Pass | Pass | Pass | Pass |
| Second distinct value | Pass | Pass | Pass | Pass |
| Calendar-window sum | Fail | Pass | Pass | Pass |
| Longest day streak | Pass | Pass | Pass | Pass |
| Every account in group qualifies | Pass | Fail | Fail | Fail |
| Half-open interval overlap | Pass | Pass | Pass | Pass |
| Bounded cyclic reachability | Pass | Pass | Pass | Pass |
| Median with duplicates/NULLs | Fail | Fail | Pass | Pass |
| Net totals with empty accounts | Pass | Pass | Pass | Pass |
| Highest two distinct ranks | Fail | Pass | Pass | Pass |
| Latest paid versus latest refund | Pass | Pass | Pass | Pass |

### What actually failed

- **Direct rolling sum:** joining each anchor event to all qualifying events
  duplicated totals when multiple anchor events shared a day. Plan-conditioned
  versions correctly aggregated/distinguished account/day first.
- **Direct median:** aggregate/count expressions inside nested LIMIT/OFFSET
  produced an invalid SQLite query. A window-function implementation passed.
- **Direct dense ranking:** descending ranks were filtered using
  `rank >= maximum_rank - 1`, selecting the bottom rather than highest two ranks.
- **Both selectors' regression:** they chose a reasonable distinct-count approach
  for universal group qualification, but its later implementation referenced
  `e.kind/e.value` without joining `events e`. The unselected anti-join branch passed.
  **Neither judge had seen this SQL. This is implementation failure after selection,
  not evidence Jev knowingly approved the invalid query.** It exposes the weakness
  of using plan quality as a proxy for final answer correctness.

## Latency: selector savings do not erase proposal overhead

| Arm | Median task time, reconstructed serial sum | Sum over 12 tasks |
|---|---:|---:|
| Direct | 1.184 s | 13.856 s |
| First approach | 2.464 s | 30.401 s |
| Self-select | 3.244 s | 39.333 s |
| Jev-select | 2.837 s | 34.407 s |

These are **counterfactual stage sums**, not separately executed production arms
or causal speedup measurements. Provider cache state, network/load, request order
and selected completion length are confounders. Maximum task sums were 1.586 s
for direct, 3.684 s self-select and 3.200 s Jev-select; too few examples for a
credible tail-latency claim.

Median proposal generation: **1.498 s**.
Median DeepSeek selector: **0.736 s**.
Median Jev selector: **0.331 s**.
Jev was the cheaper-latency selection operation observed here, but the whole Jev
branch still had about **2.48x the summed latency of direct generation**. Do not
present this as faster than DeepSeek alone.

## Usage: not roughly the same generation

Reported usage summed over the counterfactual branch for all twelve tasks:

| Arm | DeepSeek input | DeepSeek output | Jev input | Jev output |
|---|---:|---:|---:|---:|
| Direct | 3,203 | 1,514 | 0 | 0 |
| First approach | 7,607 | 2,900 | 0 | 0 |
| Self-select | 13,009 | 2,974 | 0 | 0 |
| Jev-select | 7,610 | 2,876 | 8,760 | 588 |

The Jev branch used **1.90x DeepSeek output tokens**, before counting Jev usage.
Short SQL answers make proposal overhead particularly noticeable. No claim that
cross-provider token counts measure comparable FLOPs. Actual dollar charges were
not retrieved; no dollars, model-memory reduction or energy savings claimed.

The **actual entire research run** made 72 DeepSeek requests and 12 Jev requests:

- DeepSeek: 24,128 input (6,272 cache-hit), 7,155 output tokens.
- Jev: 8,760 input and 588 output tokens.
- All 84 API calls completed without recorded errors or retries.
- Sum of API-call elapsed times: 83.010 seconds (not total experiment wall time).
- Five of 36 plan-conditioned implementations failed the evaluator; three of
  twelve direct implementations failed. Those failures remain in the results.

Counterfactual branches share calls; do not sum branch totals as actual billing.
Raw usage, prompts, choices and queries are retained privately. A credential-free
aggregate is in [summary.json](summary.json).

## Verdict and next step

**Do not add always-on Jev plan selection to the app based on this result.**
There is observed headroom, but the extra generation/self-selection already
explains the same accuracy result. The study does not demonstrate that Jev is
better than DeepSeek at choosing these approaches, nor that either policy has a
reliable population-level improvement from twelve hand-authored examples.

The most useful finding is that a good selected plan can still produce an invalid
answer. A sharper follow-up would judge a **concrete action or requirement-level
violation** using current evidence, rather than promise that abstract plans will
execute correctly. Retain an equal-budget DeepSeek-only control and an exact
verifier for measurement. If correctness can already be checked cheaply in the
real workflow, use that check before adding another model.

Any larger follow-up should freeze an independent task set and budget, repeat
samples, randomize candidate positions, include budget-matched deliberation,
report paired uncertainty and then replicate on another generator. No follow-up
sweep, training, runtime change, commit or publication is part of this run.
