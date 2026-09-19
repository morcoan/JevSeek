# Frozen pilot protocol: Jev inside ongoing generation

2026-09-18. Written before quality-study provider calls. Capability probe used a
separate trivial query: three DeepSeek requests verified continuation and returned
logprobs; no Jev selection or quality claim. Not another plan/answer-reranking study.

## Question

Can off-the-shelf Jev improve semantic-constraint adherence by selecting a short
continuation of an ACTUAL unfinished answer before the remaining answer exists?
Focus: duplicates, temporal scope, set equality, missing entities and aggregation.
This tests a one-checkpoint block decoder, not a trained value model, per-token
logit modification, hidden-activation editing, or full adaptive rollback decoder.

## Data and evaluator

Twelve NEW synthetic SQLite task families in tasks.py (different schema, prompts,
data and Python reference functions from decision_selection). Twenty deterministic
databases per task are evaluator-only checks, not 240 independent samples.
Only requirements/schema go to providers. All queries run in fresh in-memory,
query-only SQLite with authorizer/function allowlist, progress/output limits and
no file/extension functions. Reference answers use Python. Numeric results are
compared after rounding real values to eight decimals, preserving row multiplicity.
A failure on any database means task failure. No tests or gold labels go to judges.
No generated shell/Python execution, no user's data, no VM/agent runs.

## Sequence, fixed budgets and controls

All generation uses deepseek-flash with thinking disabled, temperature 0.6, maximum
1000 output tokens per final trajectory. Transport: official beta assistant prefix.
The prefix API re-tokenizes text; it is NOT native KV-cache/token-ID control.

For every task:

1. Generate a direct full query, and separately a common 12-token output prefix.
   Alternate their call order by task to reduce, not eliminate, timing bias.
2. Sample THREE continuations from that exact prefix, each capped at 24 tokens.
   These are actual next SQL tokens, not descriptions of approaches. No injected
   correct/incorrect candidates or regeneration to get a more favorable pool.
3. Shuffle their display order with a fixed seed. Jev and a DeepSeek self-selector
   see identical common prefix and candidate blocks, with no final query, gold
   results, candidate likelihoods, or identities indicating sampling order.
4. Both choose which block is most promising to continue. Evaluate Jev first on
   alternating tasks. DeepSeek outputs JSON with choice c0/c1/c2 or none, temp0,
   cap100. Jev uses Choice plus three narrow Noul questions about whether each
   candidate already conflicts with an explicit requirement. Record all values.
   These Noul outputs are exploratory signals, NOT calibrated probabilities.
5. ONLY AFTER both selectors finish, generate one remaining suffix per candidate
   from common_prefix + block, retaining that text exactly. Remaining token budget
   is 1000 minus actual common-prefix and block output usage. Rotate suffix order.
   Complete candidates require no suffix call. No repairs, answer rewriting or
   test-based selection. Record the minority of early-finished candidates separately.
6. Evaluate all three complete trajectories for retrospective coverage. This extra
   completion work is research-only; a deployed decoder would finish only its
   chosen branch. All selectors reuse exact same suffixes for causal selection
   isolation, not independent new completions for each policy.

Main controls:
- Direct, one uninterrupted generation.
- Pause/resume first branch, NO selector and no alternative-branch requirement.
  This controls the transport, shared-prefix and segmentation effects.
- Uniform random branch expected accuracy, not another sampled run.
- Generator selects the same actual partial continuations (not plans).
- Jev selects the same continuations.
- Retrospective any-branch-pass coverage: an oracle over OBSERVED completions,
  not true prefix value and not an achievable generative policy.
- Preregistered conservative Jev-veto ablation: retain first branch unless its
  Noul conflict score >=0.8, then use Jev's choice. Threshold is a heuristic fixed
  before inference; no claim of calibration. Candidate construction/selection
  is still paid in full. Do not pretend this implementation avoids those costs.

At most 108 DeepSeek +12 Jev requests (120), plus the separate 3-call capability
probe. Both SDKs have retries disabled. Provider errors/invalid outputs count as
failures with no retry/fallback; no model or temperature sweep. Stem that already
finishes bypasses steering (count separately). No quality-driven early stopping.

## Measurements and interpretation

- Exact task pass counts, paired rescues/regressions against BOTH direct and paused
  controls; same-pool comparison to DeepSeek selector.
- Valid pools, exact/whitespace-insensitive duplicate blocks, early completion,
  selected branch changes, incorrect-to-correct and correct-to-incorrect changes.
- Observable prefix potential: how often at least one completed branch passes,
  not an assertion that one rollout estimates a calibrated future value.
- Raw per-provider token/cache usage and request times, including failures. Report
  actual research totals separately from counterfactual deployed policy totals.
- Counterfactual serial latencies sum the actual calls needed by each policy.
  They are NOT separately timed production arms; cache/load/order confounds remain.
  Identical chosen trajectories are reused, avoiding completion-sampling confounds.
- Compare added generation and input processing; do NOT equate API price/tokens
  with FLOPs, model weight, hardware memory or energy. Actual bills unavailable.
- Verify selectors precede suffix generation; verify each suffix's exact input
  prefix; freeze hashes of code/protocol before calls, preserve all raw results.

## Limits and decision rule

Small hand-authored task set, single sample per branch, no held-out task families,
no unseen generator or trained Jev prefix calibration. Only one early checkpoint;
an already-bad common prefix cannot be undone. Twenty databases cannot prove SQL
correctness universally. Familiar query structures may be in provider training.
This narrow experiment cannot establish a general reasoning uplift or compare
against native DeepSeek thinking. Neither a tie nor a failure proves no other
Jev-controller design can help. No claim of free/same-compute improvement.

Do not deploy this policy based on this pilot. A clear positive result would justify
an independently frozen larger replication and a compute-matched generator-only
control; a negative result should identify selection, support/diversity, prefix
commitment, or overhead bottlenecks—not prompt-tune until it wins.
