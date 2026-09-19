# Evidence-scoping diagnostic — frozen before calls

New user goal: generalize the semantic coprocessor and investigate/fix misunderstandings. No app release changes.

## Hypothesis
The old whole-board query requires binding a host ID and a service ID amid irrelevant alternatives while interpreting nested negation. A classifier should instead see a directly scoped evidence packet and an explicit claim. A second opposite-polarity judgment may detect inconsistent assessments; disagreement must become unknown, NOT a majority-confidence assertion.

Primary-source motivation: Logic-LM (EMNLP2023) separates formalization and exact inference; Logic-LM++ (ACL2024 workshop) shows syntax repair can retain or introduce semantic errors. We are NOT repeating generic criticism or claiming solver syntax validation proves translation correctness. The change isolates source scope, uncertainty and the interface to deterministic execution.

## Known-case diagnostic, not confirmation
Use original confirmation cases97000..97011, including BOTH known failures97004/97009 and ten successes. Use cached original Jev answers as the historical baseline. This is explicitly posthoc development; no new independent quality claim is possible on these cases.

Two new policies, same visible data:
- **focused:** each typed question embeds only that host's full description and that service's full requirement. No costs/other hosts/other services in that question. Code does not supply hidden features, Boolean AST or labels.
- **dual:** same question plus its logical negation in one batch; supported/refuted opposite judgments must agree. Inconsistency -> unknown; reported contradictory evidence -> conflict. Unknown/conflict edges are unavailable. This is a consistency check, NOT independent evidence or guaranteed error detection.

Runtime supports arbitrary claims/evidence, no hardcoded host features. Four values: supported/refuted/unknown/conflict. Exact Boolean evaluator preserves unknown (does not equate missing with false), enumerates completions for up to12atoms, propagates referenced source conflict, validates references/operators/depth/node budgets. Cache key includes policy/model/mode/claim, ordered source IDs/revisions/content hashes; returned records do not expose mutable cache internals. No autonomous actions.

## Evaluation / selection
At most24newJevrequests, no other inference or retries. Record all judgments and failures. Recompute complete assignments with the original exact solver and independent hidden evaluation, plus pair accuracy/FP/FN/unknown and timing/tokens.

Select focused for fresh validation if it fixes both known task failures without losing an originally optimal task. Otherwise select dual only if it meets that condition. If neither does, stop and analyze—do not silently relabel it successful. Prefer focused when both pass to avoid unnecessary calls/output overhead. Fresh-case and external-task protocols must be frozen independently before inference. Do not train/tune on the original24and later call them unseen.

All prior files/protocols remain immutable. Research code lives in semantic_reliability; app, stopped VM and original model-server settings unchanged. Paid calls opt-in via --run.
