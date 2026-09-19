# Semantic constraints + exact reasoning — frozen before model calls

## Hypothesis
Jev can act as a semantic front end to exact computation: translate natural-language compatibility requirements into a typed Boolean relation, then let deterministic code solve the global constraint problem. This bypasses the observed small-generator bottleneck of recognizing a rule but still writing incorrect SQL. It is tool/system augmentation, NOT a change to LLM weights or a claim of new general intelligence. Exact solver contribution MUST be distinguished from Jev's semantic contribution.

## Fresh data / independent correctness
32new synthetic deployment-placement problems, generated before calls:8development seeds87000..87007 and24confirmation seeds97000..97023. Confirmation host descriptions use a third, withheld paraphrase family. This is a small constructed domain with6researcher-defined binary capabilities, not32independent real-world domains. Latent profiles and Boolean requirement ASTs are NEVER sent to providers. Providers receive only complete natural-language descriptions, natural-language conditions, host costs and the requested action constraints.

Each problem has6hosts and5services. A host can run at most1service. Every service must be placed on a host satisfying ALL of its requirement expression; minimize total used-host cost. Expressions include conjunction, inclusive disjunction, negation and material implication. Every case has multiple feasible assignments with different costs. Any optimum assignment is accepted. Test truth comes from an independent Python Boolean interpreter and exhaustive720permutations, not a model judge or single-example answer equivalence. No model-generated code executes.

## Arms / attribution
- **Direct Qwen3-1.7B:** choose an assignment in one nonthinking structured-output call.
- **Qwen semantics + exact solver:** same model classifies all30service-host pairs as eligible/ineligible/unknown; exact solver uses eligible edges.
- **Jev semantics + exact solver (primary):** SAME30questions/evidence, one parallel typed request, same solver. Unknown is conservatively ineligible. No probability thresholds or confidence-as-correctness assumptions.
- **DeepSeek semantics + exact solver:** strong-model control with same questions/evidence/solver.
- **Solver without semantics:** allow every edge, compute cheapest assignment; demonstrates what the optimizer alone provides.
- **Latent-truth oracle + solver:** undeployable upper bound / test control, never used in inference.

Model outputs are not posthoc repaired. A malformed response becomes failure/no predicted assignment; API errors logged, no retries. All arm decisions precede hidden evaluation. Qwen temperature0,top_p0.8,max1500tokens,thinkingoff, same official1.7B_Q8file/runtime as verified_search. Direct output schema enforces allowed IDs, NOT uniqueness/eligibility/optimality. Matrix schema enforces allowed labels, NOT correct semantics. Local server owned/authenticated loopback, provider keys stripped, closed afterward. No app/VM/publishing changes.

## Gate / budgets
Development at most16Qwen+8Jev+8DeepSeek=32calls. Gate requires Jev+solver optimal success strictly greater than direct and no-semantics solver, and no worse than Qwen+solver. Only if gate passes, run24confirmation cases once with unchanged code/prompts. Confirmation at most48Qwen+24Jev+24DeepSeek=96calls. Total128calls maximum, no further adaptive trials under this protocol.

A Jev-specific accuracy benefit requires beating Qwen+solver, not merely beating direct (which adds a solver). If accuracy matches self/strong semantics, report only measured efficiency differences at matched success, not unique intelligence. If all matrix models work, the gain is decomposition/exact computation, with Jev a potentially faster implementation. No use of development results to alter confirmation templates/prompts.

## Metrics
Primary: percentage of assignments that are BOTH truly feasible AND minimum cost under hidden Boolean truth. Secondary: feasible regardless of cost; edge classification accuracy/false positives/false negatives/unknown; global pairwise rescues/regressions; exact solver runtime; actual model latency and input/output tokens; model IDs and aliases; complete-system call+solver sums, not classifier-only marketing. No monetary/energy estimates without measurement. Descriptive sign tests only with tiny synthetic/family-correlated samples and multiple arms.

Validity checks: freeze task/source hashes; independently enumerate reference assignments; check all4Boolean operators on hand cases; assert provider payloads contain only visible goal/hosts/services; check heldout phrasing split; recompute ALL predicted assignments and edge judgments after run; retain failures and all prior verified_search negative/fragile results. Manual review template semantics before claims. No benchmark/public-repo upload without authorization.
