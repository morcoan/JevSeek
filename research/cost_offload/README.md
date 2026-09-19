# Correct objective: offload expensive generation, preserve task performance

User correction: **minimize paid Flash work and the total bill, not the sum of Jev and Flash token counts.** More Jev tokens are acceptable if they replace more expensive Flash work without reducing task success.

The earlier raw-token comparison was not the right economic conclusion. Jev output is FREE at the verified public rate. The existing compact endpoint already removes all12Flash calls for its12batches:8531Flash tokens versus nonthinking Flash, or18295versus thinking Flash, become0Flash tokens. The replacement has25985paid Jev input tokens, not a charge for its16416reported output tokens.

## Repriced existing confirmation, no new inference

Official rates checked2026-09-19:
- [Jev 1.13](https://docs.typesafe.ai/models.md): **$0.042/M input; output free**.
- [DeepSeek V4.1 Flash](https://api-docs.deepseek.com/quick_start/pricing): off-peak **$0.15/M uncached input, $0.003/M cached input, $0.60/M output**. Peak prices are double. Peak hours are weekdays01–04and06–10UTC; all other times off-peak.

| Same96decision queries /12batches | Correct | Median endpoint | Estimated total API cost, off-peak |
|---|---:|---:|---:|
| Flash nonthinking | 96/96 | 1.162s | $0.00164730 |
| Flash thinking | 96/96 | 3.583s | $0.00737070 |
| **Compact Jev + code rendering** | **96/96** | **0.225s** | **$0.00109137** |

**Estimated savings:33.75% versus nonthinking Flash,85.19% versus thinking Flash**, while5.17x/15.95x faster on this endpoint. At peak Flash rates the estimates are66.87%/92.60%. Jev cost is52.68% below verbose Jev's $0.002306598: sharing the catalogue matters economically because it cuts PAID INPUT, not because it cuts free output.

These are reproducible **list-price estimates from recorded usage, not invoice measurements or a new quality trial**. Raw Flash records explicitly report0cached input here. Reasoning is already included in completion counts and is not charged twice. The samples repeat24semantic patterns across3authored catalogues with ID/order changes; this does not establish universal quality preservation or savings on a full coding agent. Catalogue/query creation, downstream generation, probe execution and narration were outside this endpoint. NONE correctly answers a selection question; fulfilling the unavailable work may still require a charged fallback.

`python research/cost_offload/accounting.py` replays48saved provider outcomes/renderings, verifies frozen source hashes and raw usage, checks cache accounting and recomputes Decimal costs.7offline arithmetic/error checks;0new provider requests. `summary.json` retains both price scenarios and raw-call hashes. Prior frozen files/results are unchanged.

## Allocation of work

1. **Code first** for deterministic arithmetic, schema checks, permission/freshness enforcement, exact copying, caching and formatting. Do not pay either model for those tasks.
2. **Jev** for tested categorical work: selecting tools/procedures, selecting already-available records/spans, closed-set argument choices, and semantic constraints consumed by owned solvers. Return values directly to code instead of having Flash invoke Jev and repeat the answer.
3. **Flash only for the remaining generative work**: new code/patch text, truly unconstrained arguments, explanations/synthesis and unresolved reasoning. A structurally valid Jev decision is not proof of semantic correctness.

### Concrete next integration target found in this repository

`jevseek/models.py:Models.arguments` calls Flash for EVERY selected tool, even if an adapter could already supply all arguments. Routing itself is already Jev and is not a new saving. Removing the argument-generation call is the next useful target:
- A selected zero-argument/uniquely bound call can be supplied directly by code.
- Enum/boolean slots and verbatim values from an existing, provenance-checked candidate set can be supplied by a tested Jev argument adapter.
- If any required value cannot be represented, retain the original Flash path. Never silently drop an unsupported requested argument or keep its default merely because Jev cannot express it.
- A tool result that fully answers an explicitly structured request can be rendered by code. General user explanations still require synthesis; do not remove them indiscriminately.

The official [closed-set function-calling cookbook](https://docs.typesafe.ai/cookbooks/function_calling.md) and [verbatim span selection cookbook](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md) support these interface designs, NOT a claim that a new adapter is already validated. In particular we will not copy default-dropping of unsupported parameters or treat confidence as a correctness guarantee.

**No new general argument adapter or automatic router has been enabled in the app in this clarification turn.** The existing tested `research/efficiency/fastpath.py` remains an opt-in complete-call selector for its stated selection policy. Extending to arbitrary argument schemas requires its own quality check, not a declaration that the96queries prove it.

## Acceptance rule for expanding offload

The objective is **minimum total paid API cost per successfully completed task, subject to no observed task-quality regression and acceptable latency**. Track:
- Flash requests, input/cache/output tokens and estimated dollars avoided;
- Jev input dollars added;
- EVERY fallback, retry, error, validation-model and report-generation call;
- completed tasks, regressions/false completion, and end-to-end time.

Only expand a path after a matched comparison checks actual outputs/task completion on fresh examples, including unavailable values, changed state and compound requests. A small test is not a universal no-regression guarantee. Unsupported-schema detection should happen in code BEFORE paying Jev; a confident wrong interpretation cannot be ruled out by a threshold.

Economics also require selective offloading: under the measured average costs, a Jev-first cascade followed by full nonthinking Flash fallback on more than~33.75%of equally priced requests would erase this off-peak saving. This is an economic bound, NOT a fallback confidence threshold. Heavy Flash prompt caching can change the comparison: around49.03%input cache hits would equalize these off-peak endpoint costs, all else held constant. Real requests have unequal costs, so sum actual charges rather than applying a universal percentage.

**Direction:** keep expanding tested replacement paths, not additive critics. Preserve generation where needed. Optimize the bill at fixed success—not Jev token counts or a blanket claim to eliminate the LLM.
