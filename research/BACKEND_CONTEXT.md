# Production context and session validation

[← Research overview](../RESEARCH.md)

A historical engineering validation record, separate from the controlled research
comparisons. The desktop and packaged app now consume this backend contract.

## Decision

Keep **plain non-thinking DeepSeek Flash 4.1 + Jev JIT**. Native max and synthetic
deliberation remain experiments in `benchmarks/DELIBERATION.md`, not runtime modes.
The next engineering phase was context/session handling, followed by the desktop.

The suggestion that Jev is doing much of the heavy lifting remains a **hypothesis**:
the earlier comparison varied argument generation while all arms used Jev routing.
It did not compare against a DeepSeek-only router. Both plain and native max passed
the same 30 tests once, not a proof of equal general quality or a universal speedup.
This is a factual summary of local tests, not a published general benchmark.
Raw sessions, traces and generated workspaces remain private and are excluded
from the public source export.

## Production promotion

The earlier runtime was still an OpenHands-controlled loop and `jev_agent.py` was
a hardcoded demo. They are now replaced by the real JIT entry point and compatibility
wrapper. Previous versions are preserved in a private local archive; they are
not production entry points or included in the public source export.

Library-backed tools are retained: OpenHands file editor, native terminal and MCP
client/tool definitions. We wrote orchestration, persistence, projections and small
schema adapters, not filesystem/shell/MCP implementations.

Argument generation now uses one forced native function call with parallel calls
disabled. Only Jev can select the tool. Both argument generation and final summaries
explicitly disable Flash thinking. No synthetic gate or model plan precedes routing.

## Context design

- Verbatim user intent/earlier requests, except known credential redaction.
- Current request separated from prior requests and old failures.
- Deterministic factual compaction; generated summaries/drafts never enter routing.
- Full local execution artifacts with explicit excerpt/archive pointers.
- Latest read observations survive rolling archival in a bounded working-file cache;
  writes invalidate matching targets, shell/MCP/uncertain effects invalidate the cache.
- Conservative separate router/model byte budgets; pinned intent overflow fails visibly.
- Append-only versioned event log, single writer, recoverable incomplete tail,
  cancellation and explicit acknowledgement of uncertain interrupted effects.
- UI-facing JSONL events/callbacks, status, usage, progress counts and artifacts.

## Failures found and corrected before UI handoff

1. A missing workspace inventory made a clear create request look uncertain.
   Same route probe: write probability 0.53/confidence 0.44 without inventory;
   probability 0.91/confidence 0.88 with factual empty-directory information.
   Added bounded run-start inventory, not a generated plan.
2. Old shell failures polluted a new request's context. Scoping current execution
   separately increased the same intended edit selection confidence from 0.48 to 0.90.
3. A 0.6 confidence floor caused needless confirmation when several next tools were
   reasonable. Default is now 0.35 (configurable), with explicit `ask` always pausing.
   This is a policy choice, not a calibrated security threshold.
4. Free-text JSON generation sometimes returned wrappers/schema keys instead of tool
   arguments. Native forced function calling, exactly one call, and concise validation
   errors replaced that path. Invalid/incomplete arguments still never execute.
5. The argument generator needed the native PowerShell help, not just a generic bash
   tool name. Passing the platform-specific library description fixed shell syntax.
6. Repeated inspection persisted when context made archived source look unavailable.
   Flattened active intent, simplified routing, and kept factual source snapshots
   available to argument generation. No instructions force a fabricated successful step.
7. OpenHands' OpenAI MCP schema adds an agent-only `summary` property, but the direct
   MCP action adapter rejects it. Use the server's authoritative input schema instead.
8. Natural-language MCP registration produced both Blender/blender entries. Helper
   registration/check/removal now resolves labels case-insensitively. Restored one
   `blender` entry at the original URL.
9. Corrected `typesafe-sdk>=1.0.0` in old requirements: actual tested version is
   **0.6.0**. All current direct dependency pins match the installed environment.
10. The old 400-package global freeze contained an unrelated editable local path,
    so even using it as constraints failed pip validation. Regenerated a project-only
    188-dependency closure with `scripts/lock_dependencies.py`; constrained pip dry-run
    succeeded in the current environment. No packages were changed by that check;
    a fresh install on other platforms has not been verified.

Transient Jev HTTP503 interruptions were preserved and not counted as programming
failures. One streaming argument attempt rejected multiple calls before effects;
explicit single-call guidance plus `parallel_tool_calls=False` resolved it.

## Final evidence

### Offline

- `python -m unittest -v test_backend.py test_mcp_setup.py`: **49/49 passed**.
- Existing deliberation regression tests: **10/10 passed**.
- Python compilation passed.
- Coverage includes bounded context, pinned intent, retained/invalidation-safe source
  reads, archive retrieval through native read, resume/checkpoints, generated-context
  exclusion, lock/torn-tail handling, cancellations/uncertain effects, redaction,
  native argument validation, streaming contracts, and MCP registration/schema shape.

### Live production backend

**Incremental build engine:** the production validation session completed
with **10 tool actions** (read2/edit4/bash4), **three automatic compactions**, and
all **30 independent acceptance tests passed**. A separate evaluator invocation
also passed, exit0. Original specification/public tests and evaluator fixture hashes
were verified unchanged. Largest router state observed: 17,893 UTF-8 bytes (additional
question/schema overhead is reserved separately).

Manual compaction afterward created both router/model checkpoints; resuming the
completed session emitted only a saved `result`, with no tool/model calls replayed.

**Multi-request resume:** a separate session created and tested
triangles.py, resumed after compaction, preserved existing tests, added a negative-input
ValueError self-test and ran the full self-test successfully.

**MCP read-only:** a validation session used configured Blender MCP
through the new JIT entry point and listed Camera/Cube/Light. Two invalid wrapper-slug
attempts returned errors; the later real list_objects call succeeded. No scene-changing
capability was called. This is a compatibility test, not perfect tool-call efficiency.

**MCP installation:** a validation session registered the approved
port9765 endpoint, completed a four-tool handshake check, and accurately directed a
restart. Follow-up helper hardening prevents the capitalization duplicate discovered
in this check.

Evidence: `.jevseek/acceptance-run3.jsonl`, `acceptance-check3.txt`,
`backend-validation.json`, `postcompact-resume.jsonl`, `mcp-runtime2.jsonl`,
`mcp-install-runtime.jsonl`, test logs, and session directories. These are private,
gitignored local artifacts, not packaged fixtures or new benchmark ranking claims.

## Boundary / remaining limitations

This is a trusted local **text/code** backend, not a sandbox, security-reviewed server,
exactly-once remote execution system or multimodal assistant. Source snapshots are
bounded observations; rereading specific ranges may still be necessary. Native tool
truncation still applies. Compaction cannot prove a model understood the requirements.
Confidence is not authorization. User requests cannot be retained verbatim forever in
finite context; an oversized session explicitly asks for a smaller/new one. Archive
storage is not automatically pruned. Provider outages still pause runs.

The current desktop consumes [the backend v1 contract](../docs/BACKEND.md).
These findings motivated implementation choices, not additional reasoning modes.
