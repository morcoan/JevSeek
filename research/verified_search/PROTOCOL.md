# Verified solution search — preregistered bounded experiment

## Hypothesis and distinction from prior failures
Jev may help an LLM exploit its *existing ability to generate a correct complete solution*, by identifying that solution among alternatives. Earlier experiments judged plans, unfinished prefixes, or generated questions. This experiment judges COMPLETE SQL implementations with actual execution observations. No generated question compiler, no future-prefix value claim, no model-generated code outside constrained SQLite.

A positive result requires more than beating one sample: compare the SAME candidate pool against random selection, deterministic execution voting, and DeepSeek judging. Do not call extra sampling itself a Jev contribution. The broad user goal is higher task success, not solely speed; extra generation costs must remain visible.

## Data and split frozen before requests
Public Spider dev set via `minktn/spider-data`, pinned revision `20060fadce13ab8a88c24d60dc7ad39e3eced695`. Dataset authors: Yu et al., EMNLP2018; mirror declares CC-BY-SA4.0. Files remain private research cache; no dataset redistribution.

Deterministic seed194731. Eligible original questions: SQL SELECT count +2*(HAVING/INTERSECT/EXCEPT/UNION count)>=3; deduplicate identical parsed SQL within a DB; exclude reference execution errors and empty reference outputs. Filters use reference metadata, NEVER generator performance. Entire databases split between development and confirmation. Target12development+28confirmation; exact selected IDs, source hashes and any smaller availability are frozen in `selection.json` before provider calls. Not a random sample of all Spider or an official hard/extra-hard split.

Spider is public and old: training contamination cannot be excluded. Questions may be ambiguous and reference SQL imperfect. Do not silently correct gold or exclude losing cases after looking at results.

## Shared pool and controls
For every task, generate3independent complete SQL queries with deepseek-flash, thinking disabled, temperature0.7, max1200outputtokens, zero retries, identical request/schema/two-sample-rows-per-table. Responses must be JSON with string `sql`. No plans or reasoning requested. First sample is the direct baseline; it receives the same sampling settings/budget as the others.

Execute candidates read-only on disposable memory copies of the original SQLite DB with authorizer, function allowlist, SQL/row/VM-instruction limits. Observations include SQL error or actual column names, row count and first12rows, with explicit truncation. Generator does not see gold query/answer. Judges see only the original user question, schema/samples and these candidate observations—not gold/reference data or evaluator outcomes.

Collapse exact duplicate SQL (not semantic duplicates). Non-executable candidates excluded deterministically if an executable one exists. This cheap safeguard is also a separate baseline. Blind candidate labels and shuffle display order identically for both judges. Both judges answer the same independent pairwise comparisons plus one global best-choice question, in a single request each. No independent-statistical-vote assumption.

Arms, all computed from the same3samples:
1. Direct: first sample.
2. First executable: earliest executable sample, else first.
3. Execution majority: modal column-ordered row multiset among executable samples; ties earliest. Uses no gold, can favor a consistently wrong answer. Duplicate generations contribute votes.
4. Uniform random expectation over the3samples (analytic, no lucky random draw).
5. DeepSeek pairwise judge: left/right/tie per pair, Copeland score (win1,tie0.5), tie chooses earliest original sample. Same semantics/payload as Jev.
6. **Jev pairwise judge (primary):** same tally and fallback.
7. Global-choice outputs from each judge are secondary prespecified diagnostics, NOT replacements for a losing primary arm.
8. Oracle pool ceiling after evaluation, unattainable deployed control.

If only one unique executable candidate, both selectors use it without a judge request. If none execute, retain the first sample. Provider/JSON errors logged; fallback earliest executable, no retry or replacement run. Return means selected query, never synthetic successful task state.

## Phases / limits
Run development once (at most36generation+12DSjudge+12Jevjudge=60requests). Do not tune on confirmation outcomes. Record discovery even if bad. Proceed to confirmation with UNCHANGED policy only if development Jev primary beats direct, is no worse than execution-majority, and captures at least one success unavailable to first-executable. Otherwise record the failed hypothesis and do not spend the confirmation budget on this policy. Any subsequent different policy needs a new declared protocol and must preserve these failures.

Confirmation at most84generation+28DSjudge+28Jevjudge=140requests. Entire attempt bounded by200requests; no automatic retries or further trials. Scripts require explicit --run. Core app, model server, VM and stopped benchmark remain untouched. No arbitrary code/shell tools in this research.

## Evaluation and reporting
Primary: column-ordered row-MULTISET equality against reference SQL on the original DB, duplicate multiplicity retained, aliases ignored, floats rounded7decimals. This can miss sorting mistakes and coincidental equivalence. Record exact row-order agreement separately (ties may have multiple valid orders). NOT official Spider exact-match or test-suite accuracy. Inspect paired changes for obvious metric/reference artifacts without changing primary scores.

Report development and confirmation separately, by task and DB; paired rescues/regressions vs direct/first-executable/voting/self-judge; oracle gap; diversity and judge cycles/disagreements; invalid SQL/transport/format errors; analytic random expectation. No claim40tasks are40independent domains. Compute a paired sign-test descriptively if confirmation runs, with small clustered/multiple-arm limits.

Latency: actual component times, serial total including ALL3generationcalls plus judge, and classifier-only time. Any hypothetical parallel-generation time is not measured end-to-end and must be labeled, not reported as a deployed speedup. Actual input/output/cache tokens by provider, model returned IDs/aliases, no dollar/FLOP/energy claims without measurement. More capability at more compute is distinct from equal-budget intelligence gain. No app integration until an improvement is independently demonstrated and user approves a runtime change.
