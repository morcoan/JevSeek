# Fresh placement confirmation — frozen before inference

The posthoc12case diagnostic selected focused (both known failures fixed, no task regressions). Dual also fixed them but added unknowns/overhead and was not selected. Those results are development, not independent evidence.

48fresh seeded problems:16deployment,16test-runner selection,16document-processor selection. Same Boolean/task generator and exact matching objective as prior work, but new seeds113000..113015/114000..114015/115000..115015 and new capability descriptions; two vocabularies introduce different concepts. This is transfer across vocabularies, NOT48independent domains or real deployments. These tasks remain synthetic; do not describe them as an external benchmark. No hidden facts/AST/optima in any provider payload.

Three Jev arms (one request per arm/task, <=144requests total, no retries):
1. **legacy:** original whole-board classification instructions/criteria and state, unchanged.
2. **revised_global:** same new generic four-way instructions/claim/criteria as focused, but question points to a host ID among all six host descriptions. This separates some wording/criteria effects from scoping, though serialization/order also differ.
3. **focused (primary):** selected policy, host evidence directly embedded in each question, unrelated alternatives removed.

Same exact solver and visible input data; rotate arm order. Cache/provenance validated; unknown/conflict edges unavailable. Gold evaluation only after all judgments for each task. Report source hashes, paired optimal/feasible assignments, per-domain scores, pair FP/FN/unknowns, assessment risk and coverage, requests/tokens/timing. No confidence thresholds or statistical independence assumption for questions sharing a task. Gains must be described with paired counts and small/family-correlated limits. Never silently drop failures.

Separate uncertainty/contradiction unit tests and third-party benchmark evaluation are needed for broader applicability; success here alone does not establish it. Frozen old source and application unchanged; no VM/model launch required.
