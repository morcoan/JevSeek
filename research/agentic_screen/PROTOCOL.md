# Fast three-avenue agentic screen — frozen before inference

User explicitly requests all three quickly and no prolonged search for wins. This is a **small, authored checkpoint-to-completion screen**, not a full coding benchmark or proof of general agent improvement. No VM, production-app edits, generated-code execution, installs or publishing.

## Questions / cases
12fresh cases,4each: evidence retrieval, requirement-to-verification coverage, and repeated-failure recovery. Fixed seeds731001..731012, no replacement after outcomes. Each is a resumable configuration-maintenance workflow. The agent can inspect original records, apply a JSON configuration and run repository-owned functional probes, or finish. All artifacts are task-local, no shell/arbitrary code tool. Primary success requires correct behavior AND relevant checks on the current revision, not a helpful classifier label. Wrong/early finish counts as false completion.

Memory cases have150randomly placed records; no first-history/gold-aware retrieval tier. Other cases expose requirement/test descriptions or a recent failure trajectory. Same authoritative metadata/current revision rules in ALL arms. No source status, permissions or version validity delegated to a classifier.

## Arms
- **base:** thinking-enabled V4.1 Flash, BM25-like lexical evidence selection, normal inspect/configure/check/finish tools.
- **code:** same Flash and tools, word+character similarity fusion for retrieval/evidence linkage plus exact duplicate/error/progress metadata hints. This is a classical baseline, NOT a dense neural embedding model.
- **self:** same code candidate pool, Flash-thinking semantic association/reranking, then same thinking Flash agent.
- **jev:** same questions/criteria/candidate pool as self, Jev association/reranking, then same thinking Flash agent.
- Memory only: **full-evidence reference**, same agent with all original current records supplied; not budget-matched. Exposes gains attributable merely to a restrictive working set.

Semantic helpers return associations to ORIGINAL text only: memory record usefulness, requirement-to-probe matches, recurrent-blocker evidence. They do not generate facts, certify correctness or modify permissions. Primary agent may ignore them. Helper runs once before the agent; no semantic retries/retuning. Candidates cannot contain gold labels/expected configuration. Selection uses only public goal/text/metadata. Record candidate coverage separately AFTER inference; never insert missing gold records.

Native main-agent tool calls, at most4turns/arm, thinking high/max8192completion tokens per call. Native tool messages preserve returned reasoning fields for continuation. JSON-only configure arguments, max3probe executions/turn; named in-memory routines only. Every actual state change/probe is logged and final artifacts independently replayed. Flash helper uses same question catalog as Jev, thinking enabled,max8192. Jev bounded packaging<=2requests/case. No API retries; token-limited/infrastructure failures reported separately, not semantic wrongness.

## Bounds / stop
52agent branches (12*4 +4full-reference), at most208agentFlash +12helperFlash +24Jev requests =244provider attempts. Expected about120. At most4independent branches in flight,90s request timeout;12minute run deadline prevents starting further calls. Unfinished branches are explicit budget/timeout failures, never silently discarded.

No confirmation expansion this turn. A provisional follow-up candidate must beat BOTH code and self on >=2of4 end tasks with zero regressions vs either, and not exceed2x code median whole-branch latency. Otherwise STOP that avenue. Ceiling results mean insufficient headroom on this pilot, not proof of no possible benefit. Even a passing branch needs fresh independent application validation; no deployment from4cases.

Report task success, false completion, probe failures, helper choices/candidate coverage, all calls/tokens, whole-branch latency, source/input hashes and errors. Do not pool differently sized label sets as independent tasks. Do not call classical TF-IDF a semantic/dense embedding baseline. No price/FLOP/energy claims. Preserve all prior negative studies and frozen sources.
