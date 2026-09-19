# Corrective semantic guidance — frozen third hypothesis

## Motivation and status
The strong-generator selector showed no gain (DeepSeek11/12=Jev11/12). Qwen1.7B selector also showed no gain (4/12), but its oracle was also4/12: no correct candidates existed for the8failed tasks. This new hypothesis is NOT answer ranking. Jev might identify semantic defects in a concrete implementation and supply targeted corrective guidance so Qwen produces a solution absent from its original pool.

This protocol is fixed after inspecting development failures and before any new inference. Same12development cases are exploratory. The28confirmation cases remain unused by ANY model request. No gold answers, comparisons or test outcomes enter provider payloads; critique uses question/schema and actual query execution only.

## Frozen intervention
Eight predefined semantic facets: relationships, quantifier scope, grouping/aggregation, predicates, projection, ordering/ranking, set combination, NULL/empty cases. The critic labels each `ok`, `fix` or `unclear`. It cannot generate replacement SQL or arbitrary prose. A static per-facet explanation supplies the repair model with the meaning of a flagged issue. The raw request/schema/source/observations remain present; assessments explicitly fallible. No adaptive question generator, self-modifying program, confidence threshold, iterative retry or teacher-written solution.

One Qwen revision per arm, max1200tokens, temperature0.2, same seed per task across arms, JSON-schema envelope, thinking disabled. A non-executing original gets its same SQLite error in every arm. Do not count cheap execution-error feedback as Jev reasoning.

Controls on the SAME first Qwen query:
- original direct Qwen (already recorded for development; freshly generated once on confirmation);
- plain correction from actual evidence, no critique;
- ALL facet hints without a classifier (controls generic scaffolding/checklist benefit);
- Qwen's own facet judgments, then Qwen correction;
- **Jev facet judgments, then Qwen correction** (primary);
- DeepSeek facet judgments, then Qwen correction (strong-critic control, not a new solution generator).

Critic labels share the exact facets, criteria and evidence. Repair chooser is not told which provider supplied judgments. All final queries evaluated only after all arm outputs for a case. Raw failed calls/results retained. A malformed critic response falls back to no critique; malformed/truncated generation fails that arm. No provider retries.

## Gate, confirmation and cost boundary
Development uses all12original first-query states, not only failures. At most6localQwen+1Jev+1DeepSeek requests per task =96new calls. Proceed UNCHANGED to confirmation only if Jev repair beats plain correction and direct, and is no worse than all-hints and self-critic. Otherwise this policy fails its gate; do not tune on or spend confirmation data. A development pass is NOT validated capability improvement.

Confirmation at most7localQwen+1Jev+1DeepSeek per task =252calls. Fresh first-query seeds/settings match SMALL_MODEL_PROTOCOL.md. At most348newcalls for this policy, including unpriced local hardware use, with remote APIs billable. No loops beyond one revision, no extra candidates after seeing outcomes, no publication/runtime changes.

Primary confirmation interpretation: row-multiset agreement on original public SpiderDB (same evaluator/limits, not official Spider score). Report gains vs direct AND vs plain/all-hints/self controls, DS critic result, paired rescues/regressions, DB clustering, all API/SQL errors, changed queries, critic disagreement and entire-system latency/tokens. Independent DB holdout does not remove public-data training contamination or reference imperfections. An increase over baseline but equality with generic hints is not a Jev-specific accuracy gain.

The desired evidence is a corrected implementation the small model failed to produce in its original samples, produced from Jev's typed diagnosis without another model writing its SQL. That demonstrates a narrow system-level capability gain, not changed weights, universal reasoning, or proven general intelligence. Keep scope and compute tradeoff explicit.
