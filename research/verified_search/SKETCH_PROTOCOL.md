# Typed semantic sketches — fourth hypothesis, frozen before inference

## Why the interface changes
The3prior attempts are retained. Candidate selection cannot fix an oracle4/12pool. Generic defect labels also did not help the1.7Bmodel revise: every repair arm remained4/12. Jev did identify some real defects, but the generator copied its bad SQL. Hypothesis: the small model needs a POSITIVE executable-level interpretation, not criticism and not a bad answer to anchor on.

## Intervention
From ONLY the original question and actual schema/samples, a typed interpreter selects:
- main entity and a generic relational strategy;
- required tables;
- up to3output fields and their aggregate transforms;
- one main row predicate (field/operator/literal);
- grouping field, counted entity and count threshold/range.

All fields are categorical over names from the schema, values extracted mechanically from the question/sample matches, or a fixed small operator vocabulary. A deterministic resolver turns IDs into a semantic sketch. Jev never writes SQL or arbitrary prose. Independent question outputs may be inconsistent; expose them as advisory rather than secretly repairing with a gold answer. Some complex queries do not fit this sketch; `other/none` leaves remaining reasoning to the generator. Fixed question/operator design is researcher-authored, not claimed dynamically discovered or universally sufficient.

Qwen writes a FRESH SQL query from question+schema+resolved sketch, without seeing its previous incorrect SQL or any original result. This targets the representation/anchoring bottleneck. No attempt to edit internal activations/weights. Not a rerun of the failed critique policy.

## Matched controls
On all12development tasks, same small generator/settings/envelope and original evidence:
1. Fresh plain Qwen SQL.
2. All generic strategy recipes, no interpreter (static-scaffolding control).
3. Qwen's own typed sketch -> Qwen SQL.
4. **Jev typed sketch -> Qwen SQL** (primary).
5. DeepSeek typed sketch -> Qwen SQL (strong-interpreter control; no strong-model SQL generation).

Interpreter questions/criteria/evidence IDENTICAL across the3providers. Downstream Qwen sees resolved fields, not provider identity. JSON-schema for local output. Fresh generation temperature0.7, identical task seed across5arms. Interpretation temperature0for Qwen/DS. Zero retries. Order rotated. No gold, previous gold comparisons, or previous solutions in any inference input. Generationmax1200/interpretermax1000tokens. Invalid interpretation falls back to plain input, recorded; invalid SQL fails. Gold evaluation only after all5arms for a task.

## Gate / stopping / untouched holdout
New exploratory protocol chosen after development failures.28DB-disjoint confirmation questions still never sent to a model. Development<=6Qwen+1Jev+1DS per task=96requests. Gate: Jev exceeds fresh plain AND all-recipes, and is at least as good as self-sketch. Only then run the28confirmation tasks ONCE with unchanged code/prompts. Confirmation<=224requests, total<=320for this configuration. No hyperparameter search or posthoc selection of a secondary arm to claim success.

Report development and confirmation separately with all prior failures. For confirmation, gain over plain alone is insufficient attribution: compare all-recipes/self-sketch on the same cases, strong-interpreter bound, exact pairing, DB clustering and public-benchmark contamination. Primary metric remains originalDB row-multiset agreement, NOT official Spider accuracy or general semantic correctness. Audit changed wins/losses for reference/evaluation artifacts; do not silently edit gold or drop unfavorable tasks.

Latency/tokens include interpretation+fresh generation for all sketch arms, not just Jevclassification. Local runtime/model containment as SMALL_MODEL_PROTOCOL.md; no app/VM/server preference changes. Any positive result supports only this typed semantic compiler interface and tested generator/domain; not general intelligence or universal improvement.
