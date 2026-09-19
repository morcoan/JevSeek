# Results: semantic constraints + exact solver

## Frozen confirmation result

24new synthetic cases with host descriptions using a withheld paraphrase family. Same code/prompts as the8case development run. Every problem has5services,6hosts, complete natural-language host facts, Boolean requirements and a minimum-cost objective. Metric requires **both actual feasibility and actual optimal cost** under hidden facts. Any optimal assignment is accepted.

|Method|Valid minimum-cost plans|Feasible plans|Median model-call + solver time|
|---|---:|---:|---:|
|Direct Qwen3-1.7B|0/24|0/24|0.444s|
|Qwen pair judgments + exact solver|0/24|0/24|2.820s|
|**Jev pair judgments + same solver**|**22/24**|**22/24**|**0.184s**|
|DeepSeek pair judgments + same solver|10/24|11/24|1.305s|
|Exact solver allowing every pair|0/24|0/24|0.00055s|
|Hidden-truth oracle + solver (not deployed)|24/24|24/24|not a model arm|

The Jev relation supplied something essential beyond the exact solver alone. It also outperformed this Qwen and this DeepSeek **one-request batched matrix interface** on the same problem data. This is not evidence that Jev is generally smarter than DeepSeek.30independent DeepSeek requests, reasoning-enabled models, alternative prompts, a parser for this controlled grammar, or another domain might behave differently; they were not measured.

### Pair-level evidence

|Semantic interpreter|Correct judgments|False positives|False negatives|
|---|---:|---:|---:|
|Qwen|297/720 (41.25%)|420|3|
|Jev|703/720 (97.64%)|13|4|
|DeepSeek|631/720 (87.64%)|80|9|

No unknowns, provider failures or malformed outputs occurred. Qwen's matrix output largely degenerated into marking everything eligible. Its low score is an observed limitation of this checkpoint/prompt/nonthinking structured-output setup, not a claim that every small LLM fails the task. The direct baseline additionally had to maintain uniqueness and global cost constraints without the exact solver.

Errors compound: a single false-positive eligibility edge can make an optimizer select an invalid assignment.17Jev edge errors did not mean17failed tasks; only two chosen assignments used invalid edges. Conversely, a solver cannot repair semantic mistakes merely by optimizing more accurately.

### The two failures are real

- `confirmation-97004`: Jev permitted a host with blocked egress where the service required egress **not** to be blocked; another chosen pair violated an implication relating private listeners to blocked egress.
- `confirmation-97009`: Jev permitted a publicly reachable host for a service requiring private-only listeners.

These remained failures throughout analysis and LLM tool replay. The system is **not safe to treat as a proof of real-world compliance or as permission to deploy automatically**. The optimizer's proof is conditional on its model-derived relation.

## Development and confirmation were separate

|Method|Development8|Confirmation24|
|---|---:|---:|
|Direct Qwen|0|0|
|Qwen + solver|0|0|
|Jev + solver|5|22|
|DeepSeek + solver|1|10|
|Solver without semantic filtering|0|0|

Development had6feasible Jev plans but only5optimal. The gate was fixed before inference. No template, prompt, solver, model setting or policy changed before confirmation. The heldout cases use new seeds and a withheld host-phrasing family—not new domains or a genuinely independent external dataset.

Paired confirmation: Jev rescued22direct failures with no regressions; against the DS-matrix solver it rescued12with no regressions. Descriptive two-sided sign-test values are4.77e-7and0.000488respectively. Treat these cautiously: the cases share a tiny capability ontology, logic templates and researcher-designed workflow; multiple research avenues were explored. These statistics are not a general-intelligence significance claim.

## Costs and timing

Confirmation actual requests:48local Qwen,24DeepSeek,24Jev, zero retries. Tokens:

- Qwen:59,134input /8,404output across direct+matrix controls.
- DeepSeek:38,316input /5,488output.
- Jev:191,374input /29,700output as returned by its SDK.

**Not equal-token compute.** Jev's per-question structured specifications carry more input overhead than the DS matrix prompt; its output-usage accounting is not an autoregressive prose trace. No dollar, energy or FLOP savings asserted. Local API cost is not free electricity/hardware.

Reported time includes the matrix call and exact solver; model download/startup, UI and an agent's final narration are excluded. Calls were synchronous with rotating arm order; caches/network/hardware effects remain. On this machine, Jev+solver median0.184s versus DS-matrix+solver1.305s (~7.1×), but this is not a best-possible parallel30-request DS comparison.

## Native LLM tool replay

After confirmation, Qwen used the native `semantic_assignment` tool across all24tasks. It selected the validated request ID24/24and preserved the returned proposed assignment24/24, yielding22optimal final answers.48new local requests, zero new remote requests, zero transport/format errors. All cases were replayed, including the two failing plans.

**The semantic labels were cached from the original real Jev confirmation run.** This proves tool wiring and consumption, not another24independent samples or another inference-quality gain. Its latency is not the0.184sclassification/solver figure above. The system instructs the LLM to use the tool; autonomous tool discovery is not tested.

## Integrity / boundary checks

- Source and full fixture hashes frozen before each phase; confirmation uses identical source hashes.
-960latent pair labels across32tasks. AND/OR/NOT/implication checked on exhaustive hand truth tables.
- Provider payloads contain only the goal, natural-language profiles/requirements and costs. No latent Boolean facts, expression trees, oracle assignments or gold costs.
- Independent reference enumeration checks minimum cost without using the solver's minimization routine.
-40development+120confirmation predicted assignments re-evaluate unchanged. Stored pair labels reconstruct every predicted solver result.
- Model-generated Python/shell/SQL is never executed in this study. All optimization runs fixed trusted code.
- Own loopback model processes exited. Application, public repo, stopped VM and old model-server configuration unchanged.

## What can honestly be concluded?

**A small LLM can gain a concrete capability by calling a Jev-powered semantic-constraint tool connected to exact computation.** In this constructed domain, that tool produces verified outcomes the direct small model and its own semantic-matrix tool could not produce reliably.

This is system-level augmentation, not improved base-model weights, unrestricted reasoning or proven coding-agent gains. A deterministic parser specialized to our tiny controlled language could also solve the tasks. The evidence supports the semantic-coprocessor boundary and a practical prototype; broader natural-language/domain validation is still needed.
