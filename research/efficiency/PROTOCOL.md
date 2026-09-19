# Token/speed investigation: replace generation, don't add a critic

User asks to use Jev to decrease tokens and increase speed. Bounded research; app/release/VM unchanged. Existing failures are retained. No new intelligence or general coding claim.

## Existing-trace audit (not new inference)
The previous Flash+Jev allocation loop saved Flash completion tokens versus thinking Flash, but used MORE combined provider-reported tokens:128272 vs30810 across8cases. Jev tool stage median~0.512s, whole loop2.330s: routing/report generation mattered. Agentic helpers were faster than thinking Flash helpers, but adding helpers was slower than omitting them. Tokenizers/classification output accounting differ, so cross-provider token sums are only an accounting proxy, never FLOPs/dollars.

## Hypothesis / minimal optimization
For a bounded semantic decision endpoint whose queries and concrete action catalogue ALREADY exist:
1. replace the Flash decision/JSON-generation call with native Jev choices;
2. put catalogue descriptions into shared state once, not in every question;
3. each Choice uses the allowed IDs with `None` descriptions (supported SDK API), refers explicitly to that catalogue;
4. trusted code validates IDs and renders the structured answer. No Flash call merely to invoke Jev or copy its answer.

This does NOT parse arbitrary user conversations, invent candidates, write code, grant permissions, or execute the selected actions. Unknown/unsupported/error returns are not silently guessed. If building the catalogue/queries requires an LLM, that cost must be counted by an application; it is outside this endpoint test. No token savings claimed for unseen full agent workflows.

## Frozen comparison
4development +12confirmation batches;3authored domains(notification verification, storage checks, data-pipeline checks).8independent queries/batch,12candidate procedures plus NONE. Four real provider arms:
- Flash thinking high, one batched request, same shared visible catalogue/queries, max8192completion tokens.
- Flash nonthinking, same one-request batch, max2048.
- Jev verbose: full descriptions repeated in every question, prior-style representation.
- Jev compact: descriptions once in shared state, identical labels and task semantics.

Plus a zero-provider lexical/character matching control (not dense retrieval). All provider arms receive the SAME candidate IDs/descriptions and questions, never hidden coverage sets/gold. No deliberately sequential-per-question Flash straw baseline. Question/description wording fixed before calls, all arms interleaved by batch. Catalogue order and opaque IDs randomized. No source truncation, cached quality labels, semantic retries or result-based replacement.

Queries ask which single procedure's declared assertions directly cover the ENTIRE requested behavior. Some targets require two distinct properties or an unavailable property; only NONE is correct there. This is a semantic dispatch microbenchmark, not proof the selected test would find every bug or of end-to-end coding success. Source descriptions are authored; same ontology/templates reused. Counts within a batch are correlated.

## Budget / gate
Development<=8Flash+8Jev requests; confirmation<=24Flash+24Jev. Total64requests,0localmodel/VM calls. HTTP90s, two independent batches in flight,180s development /420s confirmation start-call deadline. No model/API retries. Preserve truncations/errors.

Proceed unchanged only if compact has0API/schema errors and does not lose batch-level accuracy to verbose Jev in development. If it fails, STOP compact compression; do not tune on the confirmation sample. No further sample expansion this turn.

Metrics: exact choice accuracy, whole-batch correctness, unavailable-option correctness, invalid outputs, whole endpoint latency including serialization/validation/code rendering, provider input/output/cache/reasoning tokens, total reported-token proxy. Report whether savings hold against THINKING and NONTHINKING Flash separately. Flash reasoning is included in completion counts, not added twice. Require no observed quality regression for any equal-quality efficiency claim; small samples do not establish noninferiority statistically.

Also report actual quality/tokens/latency versus verbose Jev, and zero-provider classical control. Confidence is not correctness; no confidence-only automatic fallback router. No price, energy, FLOP or general app-speedup claims. Reproduction logs private; no keys exported or printed.
