# Jev after the Flash comparison: agent-level opportunities, not IQ claims

Status: prioritization / code-and-literature audit only. **No new Jev/DeepSeek inference, benchmark score, app change or VM restart.** The previous live comparison remains [unchanged](flash_integration/RESULTS.md).

## Honest starting point

We have not demonstrated that Jev improves on thinking-enabled V4.1 Flash's capability. Thinking Flash solved all16structured confirmation tasks, and beat Jev on document grounding. Allocation showed a potentially useful latency trade-off; it did not establish broad superiority over a strong Flash agent. Jev also did not uniquely help prior answer selection, partial-decoder selection, generic criticism or dynamic-question studies.

A stronger agent is not necessarily a stronger underlying language model. The remaining hypothesis is **better evidence coverage and control under a practical resource budget**, rather than asking a weaker specialist to answer the same difficult question again.

## Current implementation audit

- `jevseek/memory.py`: extractive SQLite FTS5/BM25 pages, provenance, exact-event paging. Local search is ordinary code, NOT Jev. `recall` is available to Jev's router; there is no always-on semantic reranker.
- `jevseek/context.py`: bounded projections, limited old-effect recall, preserved user intent, source/status separation. Stale-source bookkeeping and context accounting should remain deterministic.
- `jevseek/models.py`: Jev routing already includes a completion review when it chooses done. Adding another vague "is this complete?" judge is not a new mechanism or demonstrated improvement.
- `jevseek/agent.py`: repeated identical failing tool arguments already pause. Semantic no-progress detection would be a different, still unvalidated extension.
- Prior [memory study](context_memory/README.md):12hand-authored questions with a layout-favored candidate union; Jev12/12. No DeepSeek reader/control, embedding control or actual task success. **Not evidence that Jev outperforms Flash on memory.** Do not repeat the same fixture and call it new validation.

## Ranked hypotheses

### 1. Evidence selection for the working context — strongest next candidate

Failure: a relevant old result, dependency, exception or correction does not reach the current model call. A strong reader cannot use evidence it never sees.

Potential Jev role: rank candidate source pages against the current decision, distinguishing topical similarity from evidence that actually changes that decision. Return original text and source IDs, not fabricated summaries or truth certificates. Preserve mandatory constraints, current failures and source authority; retain fallback access to the full archive. Neural ranking must never delete original evidence or turn an old observation into a current one.

Why this differs from the failed grounding experiment: Jev selects what Flash inspects; Flash still interprets it. An incorrect NLI label no longer directly becomes the final claim. But retrieval can still omit necessary evidence, so improvement is not guaranteed.

Ordinary-code alternatives: BM25, dense retrieval, recency/version filtering, dependency graphs. Strong model alternative: the same reranking interface backed by Flash. If these match or beat Jev on completed tasks, use them.

### 2. Requirement-to-evidence coverage — not a second general judge

Failure: the agent fixes the main symptom but misses a requested secondary behavior, or claims completion without relevant current evidence.

Potential Jev role: link explicit requirements to observed edits/tests/results, highlight requirements with no relevant evidence, request inspection or verification. Code supplies actual execution status, source revision and test results. A semantic match is NOT proof that a requirement is satisfied.

Important limits: missing requirements in the initial ledger remain missing; another model cannot assess questions nobody asked. False approval is dangerous. User safety/permission constraints must not be silently retired by a classifier. Generic done review already exists in this app and has not been causally ablated against Flash-only control.

### 3. Semantic no-progress / recovery triggers

Failure: different commands or patches keep reproducing the same underlying obstacle, despite looking different to an exact duplicate detector.

Potential Jev role: group recurrent failure evidence, identify lack of new information, suggest fresh inspection or escalation. Do not directly authorize new effects, kill processes, override user instructions or certify that a strategy is wrong.

Ordinary-code controls: normalized error signatures, unchanged artifacts/tests, repeated calls and explicit budgets. A productive iteration can still show the same error, so premature stopping is a real regression to measure. No access to private in-model thought or arbitrary DeepSeek KV/logit hooks is assumed.

## A defensible next test — not yet launched or frozen

Choose ONE intervention first: evidence selection. Use a thinking-enabled Flash agent throughout. Compare:

1. A competent Flash-only agent with its normal retrieval tools.
2. The same agent with improved code-only retrieval/provenance bookkeeping.
3. The same candidate pool, task/context budget and selection interface with Flash reranking.
4. The same interface with Jev reranking.

Randomize evidence placement; include distractors, multi-record answers, corrections, misleading assistant claims and missing evidence. No gold-aware candidate insertion. Measure candidate recall separately: a reranker cannot recover a missing candidate. Include a full-evidence reference where feasible, so artificial context restriction is visible.

Primary outcome must be independently verified end-task completion and regressions—not relevance labels, tool-call validity or synthetic “intelligence” scores. Record false completion, useful evidence reached, unnecessary actions, all model/tool calls, total latency and provider-specific tokens. Fixed budgets and stopping rules before calls; separate development/confirmation; retain failures. Exact costs must not be inferred from token counts alone.

If Jev does not beat both the code-only and matched Flash-backed alternatives on the useful quality/resource frontier, there is no Jev-specific deployment case. Do not expand experiments until a favorable result appears.

## Research grounding

- [SWE-agent, NeurIPS2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/5a7c947568c1b1328ccc5230172e1e7c-Abstract-Conference.html) and its [ACI documentation](https://swe-agent.com/0.7/background/aci/) show that interface design, concise feedback and deterministic guardrails can improve an agent with the same base model. This is evidence for studying the agent boundary, **not for Jev's contribution**. Its historical scores are not current Flash results.
- [LongMemEval, ICLR2025](https://proceedings.iclr.cc/paper_files/paper/2025/file/d813d324dbf0598bbdc9c8e79740ed01-Paper-Conference.pdf) separates indexing, retrieval and reading, including updates and abstention. Already reviewed in the prior memory study; no claimed benchmark replication.

Bottom line: investigate Jev as a selective attention/evidence-routing component. Do not market it as a smarter brain, an authority layer, a substitute for real tests, or a proven general agent capability upgrade.
