# Efficiency result: faster bounded decisions, not fewer total tokens than Flash

## Bottom line

**Working speed optimization:** when questions and a concrete action/answer catalogue already exist, let native Jev choose IDs and let code return the corresponding structured result. No Flash call is needed simply to generate/copy those IDs.

**Working Jev prompt optimization:** share option descriptions once across questions instead of repeating them. This reduced Jev input tokens52.7% and combined reported Jev input/output40.6%, with unchanged observed answers on this test.

**Not demonstrated:** fewer total reported tokens than an efficiently batched Flash call, cheaper monetary cost, a complete-agent speedup, or faster general code/prose generation. Do not hide Jev's token usage behind “zero LLM tokens.”

## Fresh confirmation (12batches,96query decisions)

| Method | Correct choices | Entire batches correct | Median complete endpoint latency | Input tokens | Output tokens | Reported total |
|---|---:|---:|---:|---:|---:|---:|
| Flash thinking | 96/96 | 12/12 | 3.583s | 8014 | 10281 | 18295 |
| Flash nonthinking | 96/96 | 12/12 | 1.162s | 7714 | 817 | 8531 |
| Jev verbose | 96/96 | 12/12 | 0.361s | 54919 | 16416 | 71335 |
| **Jev compact** | **96/96** | **12/12** | **0.225s** | **25985** | **16416** | **42401** |
| Lexical code control | 72/96 | 0/12 | ~0.0004s | 0 | 0 | 0 |

Compact Jev was **5.17x faster than nonthinking Flash**, **15.95x faster than thinking Flash**, and **1.61x faster than verbose Jev** by the ratio of these endpoint medians. Two independent batches were in flight; arms rotated within each batch. Latency includes request construction, provider call, answer validation and deterministic rendering. It excludes upstream catalogue/question construction, actual probe execution, downstream narration and unrelated agent work. Network/provider scheduling and connection warm-up are not fully controlled; these are observed API latencies, not hardware throughput guarantees.

The token caveat is substantial:
- Compact Jev still reports **4.97x** the total of nonthinking Flash and **2.32x** the total of thinking Flash.
- Flash thinking completion counts include its reasoning; do not add reasoning tokens twice.
- Jev's reported classification output usage is not equivalent to autoregressive prose generation. Cross-provider totals are an accounting proxy, not FLOPs, energy or price.
- The fast endpoint itself uses0Flash requests/tokens, but it still uses Jev. That is offloading, not eliminating model work.

## What was tested

Three authored catalogues: notification verification, storage checks and data-pipeline checks. Each has12candidate procedures plus NONE. Each batch asks8queries: six single-property needs, one compound need no single candidate covers, and one unavailable capability. No candidate is invented from a gold answer. IDs and catalogue/query order are randomized; confirmation uses a different query paraphrase family from development.

**Important dependence limit:** the12confirmation batches are four ID/order randomizations of each of three catalogues, not12independent application domains. There are24semantic query patterns repeated with different IDs/order. Equal96/96 observed correctness is not statistical proof of noninferiority or reliability on new language/domains.

Correctness here means matching the procedure's DECLARED assertion coverage. No claim that these descriptions prove actual real-world software behavior. The endpoint returns concrete calls as data, but never executes them or grants permissions. The zero-provider baseline is a fixed lexical TF-IDF-like matcher, not a hand-built perfect parser or dense neural reranker; beating it does not prove Jev is necessary wherever ordinary code can resolve the input.

## Controlled representation change

Verbose Jev repeats the catalogue descriptions and selection policy inside every question. Compact Jev puts descriptions and policy in shared state and passes allowed IDs with `None` descriptions to each native Choice. Question meaning and all original descriptions remain available. The renderer only validates IDs and deep-copies the caller's existing call data; no model-generated arguments or answer repair are selected by correctness.

Flash controls use an already efficient SINGLE batched call with catalogue/queries supplied once. They are not a slow one-Flash-call-per-question straw baseline. Flash thinking uses high/max8192; plain uses disabled reasoning/max2048. All confirmation calls completed without truncation/API/schema errors. No confidence threshold or accuracy-dependent retry was used.

Development:4batches/32queries. Compact Jev32, verbose32, plain32, thinking31; no compact regression, so the frozen confirmation proceeded unchanged. Both phases total **64provider requests:32Flash+32Jev**. No further inference or sample expansion planned.

## Why this differs from the prior failed agentic helpers

The earlier helpers were ADDED to an agent that already solved every task. Here Jev REPLACES an already-required semantic selection/JSON-generation endpoint. The caller does not ask Flash to invoke Jev and then spend another Flash call copying its answer.

The retrospective audit `existing_trace_audit.json` also shows:
- Prior allocation hybrid:2.330s versus10.602s thinking Flash, but128272combined reported tokens versus30810; not a total-token saving.
- Prior Jev helper stages were fast, yet complete no-helper agents were faster at equal task success.
- Removing routing/reporting stages may be appropriate for a typed endpoint, but those stages cannot be declared free or unnecessary for general conversation. The old full-agent traces were not rerun as a new optimized-agent quality trial.

## Practical recommendation

Use compact native Jev **selectively for latency-sensitive finite-choice services**: procedure/tool selection when arguments are already bound, classification/routing, or selecting existing records from a common catalogue. Preserve source evidence and use code for rendering, schema validation, permissions, freshness and ordinary caching.

For lowest raw reported token volume on this test, **nonthinking Flash won**. Do not adopt Jev on the claim that it universally reduces total tokens. If cost is the real objective, compare actual billing/rates and quality—not cross-provider token counts alone. No such price claim is made here.

Keep Flash for free-form generation, new code, unconstrained arguments and tasks not represented by the catalogue. A NONE result may require more evidence or a generative fallback; those downstream costs were not measured. The production app is unchanged; this is an opt-in research module, not an automatic task router.

## Evidence / verification

- Frozen [protocol](PROTOCOL.md), `tasks.py`, `fastpath.py`, `experiment.py`.
-96offline checks before inference: schema/source preservation, exact oracle rendering, no action execution/authorization, copy isolation and invalid-output rejection.
-All80arm/batch outputs across both phases can be recomputed from saved labels; source hashes and exact visible-only provider inputs checked.
-Private runs: `.local/research/efficiency/development-1789831625888379800` and `confirmation-1789831826798837800`.
-Provider identities retained: official `deepseek-flash` V4.1 alias and `jev-1.13.0`; aliases are not model-weight hashes.
-No app/release changes, model-server/VM launches, generated-code execution or publication.
