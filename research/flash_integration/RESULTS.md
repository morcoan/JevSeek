# Results: does Jev improve DeepSeek V4.1 Flash?

**Yes on the tested nonthinking structured-planning configuration; not universally. The best current fit is scoped eligibility judgments plus exact optimization. General document grounding regressed.** This is a small research study, not production validation or a broad coding result.

## What actually ran

Official `deepseek-flash` alias (V4.1 Flash), returned model `deepseek-flash`; Jev returned `jev-1.13.0`. Real native `tool_choice=auto` calls, validated request IDs, LIVE backend assessments, actual tool messages and final Flash responses. No cached quality labels, simulated agent adoption or generated-code execution.

6development +24fresh confirmation cases;8confirmation per avenue. Four arms:

- **Plain Flash:** nonthinking, direct final answer.
- **Flash + self-tool:** Flash specialist reads the SAME scoped questions/evidence/criteria used by Jev. Same deterministic solver where relevant, same native orchestration.
- **Flash + Jev-tool:** backend swapped for Jev; tool name/schema/prompt identical and backend identity hidden from Flash.
- **Thinking Flash:** direct, high reasoning;8192tokens for structured tasks,32768for documents after the pre-confirmation [budget amendment](CONFIRMATION_AMENDMENT.md).

All60native tool loops across both phases were invoked and returned. Confirmation:168Flash+24Jev requests,0APIerrors,0thinking truncations. Entire study:210Flash+30Jev requests; two development document-thinking calls truncated at the originally declared8192cap and remain recorded. No other inference planned.

## Primary confirmation: strict final JSON scoring

| Avenue | Plain Flash | Flash + self-tool | Flash + Jev-tool | Thinking Flash |
|---|---:|---:|---:|---:|
| Feasible, minimum-cost allocation | 2/8 | 6/8 | 7/8 | 8/8 |
| Ordering deductions | 5/8 | 6/8 | 7/8 | 8/8 |
| Grounded document claims | 107/136 | 107/136 | 102/136 | 114/136 |

Allocation feasibility alone was3/8,7/8,7/8,8/8 respectively. Every optimal result was independently verified against the true latent requirements and minimum cost; no accidental single-database SQL matching.

The strong self-tool control matters: **much of the planning gain comes from scoping and deterministic computation, not Jev alone.** Jev adds one strict final-task win over self-tool in each structured avenue here. With8cases/avenue, this is not statistically established broad superiority. Paired planning rescues/regressions: Jev vsplain5/0(descriptive sign p=.0625), vs self1/0(p=1). Ordering:2/0vsplain,1/0vsself. Thinking Flash solved all16structured cases.

### A real integration defect, separately corrected

The Jev allocation tool itself produced **8/8 truly feasible optimal plans**. Flash's final response for `allocation-621007` agreed with the correct plan but wrapped its JSON in prose despite requesting JSON mode. The strict parser rejected it. A similar format failure occurred in development. This was a delivery-format failure, not a wrong plan or a model rejection of the plan.

Added `answer_codec.py` and public wrapper `agent.py`. The codec accepts strict schema-valid JSON or a **single schema-valid trailing JSON object**; it rejects ambiguous multiple answers, incomplete/error responses and unknown IDs, strips untrusted extra metadata, and enforces parse budgets. It never reads gold labels or selects an answer by solver agreement/correctness.

**Uniform offline replay of ALL four arms' same stored responses:** Jev allocation becomes8/8; plain2, self6, thinking8 remain unchanged. Ordering and grounding correctness totals are unchanged. This is explicitly a posthoc formatting correction, **not a new independent model-quality sample**. Primary strict scores above are retained. A fresh deployment-format replication remains desirable.

## Whole-system latency (median seconds)

Includes native routing, specialist/backend calls, deterministic processing and final Flash response—not just Jev inference.

| Avenue | Plain | Self-tool | Jev-tool | Thinking |
|---|---:|---:|---:|---:|
| Allocation | 0.954 | 3.532 | 2.330 | 10.602 |
| Ordering | 0.927 | 2.753 | 2.154 | 2.248 |
| Grounded claims | 1.227 | 3.411 | 2.637 | 51.398 |

Interpretation:
- Allocation offers a promising accuracy/latency trade-off: slower than weak plain answers, faster than self-tool and thinking. Formatting-corrected recorded plans match thinking's8/8, but the small sample and posthoc parser caveat remain.
- Ordering Jev improves plain nonthinking Flash, but **thinking Flash is more accurate at nearly the same median latency**. Do not force this through Jev by default.
- Document grounding is **both less accurate and slower than plain Flash** with Jev. Do not enable this as a generic factual/legal approval mechanism.

Remote/warm-call observations, not controlled GPU/FLOP or cold-start comparisons. No dollar/energy claim.

## Grounded-decision risks

8unseen ContractNLI documents,17claims each. Full unannotated text, no gold evidence spans. Exact human-label agreement, not legal truth or advice.

| Metric | Plain | Self-tool | Jev-tool | Thinking |
|---|---:|---:|---:|---:|
| Accuracy | 78.7% | 78.7% | 75.0% | 83.8% |
| MacroF1 | .720 | .739 | .705 | .797 |
| False Entailment predictions | 9 | 8 | 13 | 4 |

Jev lost5net labels vsplain/self and12vs thinking. Relative to plain it improved2documents and worsened4; vs self improved2/worsened5. Treat labels as clustered by document and repeated hypothesis family, not136independent trials. This is why stronger claims about generally reliable reading or autonomous decisions would be premature.

## Usage transparency: confirmation input/output tokens

Each cell is provider-reported totals. Jev output usage is not equivalent to autoregressively generated reasoning text; these are not comparable FLOP/dollar units. Flash completion counts already INCLUDE reasoning; do not add reasoning again.

| Avenue / arm | Flash input / output | Jev input / output |
|---|---:|---:|
| Allocation plain | 7241 /287 | — |
| Allocation thinking | 7441 /23369 | — |
| Allocation self-tool | 105890 /2910 | — |
| Allocation Jev-tool | 20014 /2187 | 94953 /11118 |
| Ordering plain | 2135 /40 | — |
| Ordering thinking | 2335 /3180 | — |
| Ordering self-tool | 11552 /440 | — |
| Ordering Jev-tool | 8470 /376 | 4873 /528 |
| Grounding plain | 15868 /1176 | — |
| Grounding thinking | 16068 /101664 | — |
| Grounding self-tool | 68424 /2655 | — |
| Grounding Jev-tool | 37379 /1501 | 36890 /6064 |

## Engineering / audit

-819offline checks:30visible-input/tool stub roundtrips and source/solver checks, plus729unknown-edge relation completions for cost-bound soundness.
-10public entrypoint checks plus10format-codec checks; no remote calls in unit tests. The regressing Jev document-grounding path is blocked unless explicitly opted into as experimental.
-All120final outcomes across both phases recomputed;60tool results recomputed; source hashes and exact visible-only payloads verified.
-Agent interface takes only `id`, `kind`, `visible`, rejects hidden fields, performs no real actions. No app runtime/release/publication changes; VM remains off.

Private artifacts under `.local/research/flash-integration/`:
- `development-1789821714807467400`
- `confirmation-1789822037006606000`

Each has immutable manifests, visible/hidden fixtures separated in provider serialization, native request/response traces, evaluations and summaries. Public aggregate summaries live alongside this report. No provider keys are included in public files.

## Recommendation

1. **Keep an opt-in Jev allocation/planning specialist:** grounded, scoped constraints followed by exact code; expose uncertainty and conditional guarantees.
2. **Keep ordinary code-only and Flash-backed paths:** structured data should not need neural interpretation; a win over unstructured prompting is not automatically Jev-specific.
3. **Prefer thinking Flash for this ordering sample** when that mode is acceptable; Jev remains an optional nonthinking improvement, not a demonstrated best overall choice.
4. **Do not enable generic long-document Jev grounding by default:** the measured regression and higher false-entailment count outweigh a speculative benefit.
5. Validate on larger independently collected application workloads before production/default activation. No untested automatic tool dispatcher is claimed.

Limits: small8case-per-avenue confirmation; synthetic allocation shares the prior generator; public BBH/ContractNLI may be in training data; short-document eligibility filter; source schemas/domain adapters are authored code; model aliases are mutable; semantic judgments and final model reports remain fallible. Exact computation never proves that the semantic interpretation was correct.
