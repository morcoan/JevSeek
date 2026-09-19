# Intelligence-augmentation search: SQL attempts and why they were insufficient

These results are retained as failures/limited leads, not overwritten by the later [semantic-constraint result](../semantic_constraints/RESULTS.md). No application code changed.

## 1. Complete-solution selection, strong generator

Unlike earlier plan/prefix experiments, judges saw complete SQL and actual execution observations.12compositional Spider development questions,3DeepSeek generation requests per question, same pool for all selectors.

|Arm|Original-DB execution agreement|
|---|---:|
|First DeepSeek sample|11/12|
|First executable / execution majority|11/12|
|DeepSeek pairwise judge|11/12|
|Jev pairwise judge (primary)|11/12|
|DeepSeek global choice (secondary)|12/12|
|Jev global choice (secondary)|11/12|
|Pool oracle|12/12|

44DeepSeek+8Jev requests, no errors. Jev missed the only recoverable first-sample failure. Its classifier was faster, but the full3-generation search was slower than direct. Gate failed; no confirmation run of this policy.

## 2. Complete-solution selection, genuinely small generator

Downloaded the official pinned Qwen3-1.7B Q8_0 model and used a private owned local server, without thinking. Same12development questions and selector controls.

**Every arm scored4/12, including the pool oracle.** The model produced no correct alternative for any of its8failed cases.39Qwen+3DeepSeek+3Jev requests, no API errors; only3/36candidate queries failed to execute—the rest of the errors were semantic. A better judge cannot select an answer that does not exist. Gate failed; no confirmation run.

## 3. Generic semantic criticism and one revision

Eight typed facets (relationships, quantifiers, aggregation, predicates, projection, ranking, set combination, NULL/empty semantics). Same original query and actual execution evidence; compare plain revision, all hints, Qwen self-critique, Jev critique and DeepSeek critique.

**All arms remained4/12.**72Qwen+12DeepSeek+12Jev requests, no provider errors. Jev sometimes recognized a real problem (for example, no-cat being implemented as no-pets), but the small generator repeated its wrong SQL, including a known nonexistent column. The recognition-to-implementation boundary was the bottleneck. Gate failed.

## 4. Positive typed semantic sketches, without the bad draft

Interpret original question/schema into categorical root entity, needed tables, relational strategy, output fields/transforms, row condition and group-count condition. Resolve IDs into a positive sketch; Qwen writes fresh SQL, with no prior wrong answer in context. Controls use no sketch, all generic recipes, Qwen self-sketch and the same sketch interface supplied by DeepSeek.

|Arm|Development12|DB-disjoint confirmation28|
|---|---:|---:|
|Fresh plain Qwen|3|5|
|All generic recipes|5|6|
|Qwen self-sketch|3|1|
|Jev sketch|8|8|
|DeepSeek sketch|7|8|

The baseline prompt here differs from the original first-sample prompt; do not silently mix3/12and4/12. All within-study arms use the same generator instructions and seed, with only the added sketch/recipes differing.

Development gate passed. Confirmation code/prompts were unchanged and all28questions were previously unused by model inference. Jev versus plain had6rescues/3regressions, versus recipes3/1. The observed original-DB metric increased, but the paired plain comparison was small and inconclusive (descriptive sign-test p≈0.508, shared database clusters).

**More importantly, manual semantic inspection found spurious successes and reference issues:**

- Development63: the Jev-conditioned query used a scalar `PetID = (SELECT ... WHERE PetType='cat')`. It matched this DB but does not correctly handle multiple cat IDs.
- Confirmation700: the winning query ignored one of the requested contestants and added an unrequested NY restriction. It accidentally matched the original DB result.
- Confirmation942: the question asks for two **types** of treatment; reference SQL counts rows, while the plain model used `COUNT(DISTINCT treatment_type_code)`. The metric penalizes the more natural interpretation of that requirement.
- Confirmation241: “at least10” in the question versus `>10` in reference SQL. The Jev query used `>=10`; the original data did not distinguish them.

Therefore **8/28 is not evidence of8semantically correct implementations or a robust intelligence gain**. Primary scores are retained unchanged rather than fixing gold after seeing outputs. Genuine-looking local rescues include477(correct country/player aggregation),173(proper anti-existence),243(correct airline join/count), but these do not erase the failures or artifacts.

Confirmation224requests (168Qwen,28DeepSeek,28Jev),0provider/schema errors. Median reconstructed interpretation+generation: plain0.693s, all-recipes0.728s, self3.285s, Jev0.831s, DS1.776s. Jev interpreter0.330s versus DS1.166s. This remained a speed advantage for a useful representation, not a universal accuracy result.

## Evaluation / data caveats

Spider dev mirror `minktn/spider-data`, revision20060fadce13ab8a88c24d60dc7ad39e3eced695. Dataset: Yu et al., EMNLP2018; mirror declares CC-BY-SA4.0. Local cache only, not redistributed. Selection code chooses73eligible compositional, unique-parsed-SQL, nonempty-reference cases; fixed seed selects12development+28confirmation across disjoint DB groups. The filter is not the official Spider difficulty split. Public-data training contamination cannot be excluded.

Metric: column-ordered row-multiset agreement on the ORIGINAL database, aliases ignored, duplicates retained, float rounding7digits. It can miss sorting errors and coincidental equivalence. Exact row order recorded separately. NOT official Spider exact-match/test-suite accuracy. No model receives gold SQL or expected result; those are used only after all decisions for a task.

Generated SQL runs on disposable memory copies, with write/ATTACH/extensions/file reads denied, function allowlist, SQL/row/VM-instruction limits.40gold-query checks and7security/resource guards passed before inference. All selected query results re-evaluate unchanged, and frozen hashes/decision payloads are retained. Offline analysis explicitly decodes UTF-8; no provider-output reruns were used to repair reporting issues.

## Files

- [Original protocol](PROTOCOL.md), `experiment.py`, `data.py`, `analyze.py`, `preflight.py`.
- [Small-model protocol](SMALL_MODEL_PROTOCOL.md), `small_model.py`, `local_model.py`.
- [Corrective-guidance protocol](REPAIR_PROTOCOL.md), `repair.py`, `analyze_repair.py`.
- [Sketch protocol](SKETCH_PROTOCOL.md), `sketch.py`, `analyze_sketch.py`.
- Aggregate JSON: `development_summary.json`, `small_development_summary.json`, `repair_development_summary.json`, `sketch_development_summary.json`, `sketch_confirmation_summary.json`.

The subsequent experiment replaces unconstrained SQL implementation with exact constraint execution and uses independent hidden Boolean truth, precisely to avoid treating these fragile SQL metric gains as a solved problem.
