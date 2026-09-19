# Backend contract v1 — UI handoff

## Scope

Backend for a trusted local, single-agent coding assistant. Plain non-thinking
Flash 4.1 + Jev JIT; OpenHands provides native tool implementations. No hosted
server dependency beyond the model APIs and user-configured MCP endpoints.
The backend was frozen before the UI phase. The separate
[desktop app](DESKTOP.md) now consumes this interface. Avoid changing
routing/context policy just to implement a screen.

## Entry points

### Process boundary (recommended initially)

```
python main.py --json [--workspace PATH] [--no-mcp] "task"
python main.py --json --session ID "follow-up"
python main.py --json --session ID
python main.py --json --session ID --compact
python main.py --json --list
```

`--sessions-dir PATH` selects storage; default PROJECT/.jevseek/sessions.
Workspace is bound to a session. A conflicting `--workspace` is rejected.
No prompt on a completed session replays the saved answer, not tool effects.
No prompt on a blocked session retries inference from persisted facts. A new
user message scopes current verification separately from historical errors.
`--compact` without a prompt is local-only. No default demonstration task runs.
Exit 0 = completed/compacted/list; exit 2 = needs_input/blocked/cancelled or error.

### Python boundary

- `Session.create(home, workspace, on_event=callback)` or `Session.open(home, id, ...)`
- `Models(session, Settings.environment())`
- `Tools(workspace, session.directory/'terminal', load_servers())`
- `Agent(session, models, tools, policy=ContextPolicy(), instructions=..., cancel=threading.Event())`
- `agent.run(prompt=None, compact=False, acknowledge_pending=False)` returns
  `{session_id, status, summary, session_dir}`.
- `agent.close()` in a finally block.

Use the installation guidance from `main.instructions()` if constructing in
Python. Construct/close resources per run as the CLI does. Agent.run is
synchronous: a UI should use a worker thread/process, not block its event loop.
The session holds a single-writer lock for the run; concurrent writes are rejected.

## Events

Persisted event envelope:

```json
{"version":1,"session_id":"<32 hex>","seq":12,"time":1789670000.0,"kind":"tool_finished","data":{}}
```

`seq` is monotonically increasing inside a session, suitable for dedup/replay.
Transient `model_progress` events have `seq:null`; only character counts are
streamed, not unvalidated tool arguments or partial secrets. Final result/list
messages from the CLI also have `seq:null` and may omit `time`. Ignore unknown
optional fields and future event kinds. Reject incompatible `version` values.

| Kind | Important data |
|---|---|
| session | workspace, session_id |
| user | text (verbatim except redaction) |
| run_started | model, thinking, run-start workspace listing |
| route | choice, confidence, context_bytes |
| model_started / model_progress | stage, model / character count |
| usage | provider, stage, model, seconds, provider-reported usage |
| argument_offload | backend=code, tool, policy, generation_call_skipped, generator, flash_call_skipped |
| tool_started | call_id, tool, target, full request artifact |
| tool_finished | call_id, tool, status, exit_code, text preview, arguments preview, artifact, full_output |
| tool_uncertain | call_id, tool, explicit acknowledgement note |
| compaction | audience, through (event watermark), checkpoint, method |
| final | status, summary |
| error | stage, error class, redacted message |
| cleanup_warning | error class (transient) |
| result | CLI result dictionary |
| sessions | CLI list of session id/workspace pairs |

`tool_finished.status=ok` means the native tool/command did not report an error,
not that every business requirement was proven. `exit_code=-1` means an unfinished
shell command, not success. MCP applications can encode their own errors inside
successful transport responses. Preserve visible output for users to inspect.

The authoritative final answer is `final`/`result`, not a `model_progress` event.
A failed model/service request emits an error and saves state; it never invokes
a tool with partial arguments. A subscriber exception cannot prevent persistence.

## Persistence and interruptions

`.jevseek/sessions/ID/events.jsonl` is the append-only redacted event log.
`artifacts/` stores complete redacted requests/results and plain text outputs;
`context-*.json` stores deterministic compaction checkpoints. `terminal/` is
reserved for native OpenHands output files. These local artifacts are private,
not suitable for public upload. Do not expose arbitrary filesystem paths through
a future web UI; constrain artifact serving to the selected session directory.

`tool_started` is flushed before invoking side effects. If the process stops
before `tool_finished`, exact outcome is unknown. An unfinished last shell wait
is also uncertain across restarts. Resume is blocked pending inspection and
`--ack-interrupted`. Acknowledgement does not declare success or blindly rerun
anything; it records that uncertainty for the next JIT decision. This is not an
exactly-once transactional guarantee for remote/shell side effects.

Ctrl+C is handled. For Python integrations, set the supplied cancellation Event.
Cancellation is checked between calls and during streamed DeepSeek responses;
Jev/tool calls may wait for their SDK timeout/soft timeout. Hard process kill can
leave effects uncertain. Shell variables, subprocesses, cwd and editor undo are
not persisted/reconstructed. Files, requests, observations and checkpoints are.

Incomplete final JSONL records are archived and removed under the lock; malformed
complete/interior records fail visibly. Models are retried by their SDKs, but
execution itself is not wrapped in a retry function. Repeated identical tool
errors pause for intervention rather than loop or claim success. No turn cap.

## Context policy

No LLM-written compaction summary. Current intent and earlier user requests are
pinned verbatim; only known credentials are redacted. Since v0.2.1, the previous
assistant response is also retained verbatim in a separately labeled conversational
field, so follow-ups such as “proceed” can refer to an offered action. It is **not**
execution evidence, verified research, or a higher-priority instruction. Drafts
and earlier router guesses remain excluded. Old tool records become
factual rows with status/target/exit-code/archive pointers. Recent records retain
larger excerpts. Latest read snapshots (up to six distinct file/range pairs)
survive rolling archival within the active request; any shell/MCP/uncertain action
invalidates them, and a write/edit invalidates its target. A new user request
starts a new working-file cache. Outside edits can still make an observation
stale; native exact-match editing and verification remain necessary.

The router gets a smaller projection than the argument generator, explicitly
labeled so it doesn't repeatedly inspect already-available source just because
its own excerpt is short. Full outputs remain local and can be reread via native
read/view_range. Source snapshots are observations, not promises that entire
files were read; native tool truncation/line ranges still apply.

Budgets are conservative UTF-8 byte estimates, not provider tokenizer/billing
counts. Defaults: 24k for Jev and 96k for Flash, with instructions/questions and
schemas reserved. Jev budget cannot exceed 28k bytes under its 32k per-question
limit. At 85% pressure, archive older output in chunks retaining the latest four
execution records, then project oversized individual results with explicit
omission markers until within the budget. Paths/status/errors remain inspectable.
Pinned intent that cannot safely fit raises ContextOverflow; never silently trim
requirements. Archives grow on disk; no automatic retention deletion is provided.

Stable instructions and pinned intent appear first to help prefix caching;
compaction replaces an old-context prefix and necessarily disrupts some cache.
No cache-efficiency improvement is claimed from implementation alone. Jev's
reported confidence is a distribution statistic, not a correctness probability.
The configurable 0.35 routing floor pauses near-flat decisions; explicit ask
always pauses. This avoids treating every split among valid next tools as an
ambiguous user request. It is a policy choice, not a calibrated safety threshold.

### Completion hotfix (v0.2.1)

A proposed `done` now receives a separate Jev completion review against the
current request and actual execution records. If work remains, Jev selects a
relevant tool with `done` excluded for that selection. Genuine blockers still
pause; conversational answers can still finish without tools. This is semantic
routing, not keyword matching or a rule forcing every message to execute a tool.
Review calls have their own `completion_review` usage/activity stage, add API
latency/cost, and are not an independent verifier or a guarantee of correctness.
The response generator must not infer that tools are unavailable merely because
none ran. This changes the earlier frozen routing policy; historical benchmark
results describe the older policy, not this hotfix.

### Archive retrieval and accounting (v0.2.2)

Every context field, including archive counts, is sized **before** fitting. Optional
history/source duplicates can leave the working set without deleting their saved
originals. Latest execution and verification status remain protected.

A session-local SQLite FTS5 cache indexes original user/final/tool records and full
saved outputs in overlapping pages. Up to two intent-relevant older effect pages
can join the working set if space permits. Jev can choose the read-only `recall`
tool to search or page an exact event sequence; no extra provider is used by the
index. Typed provenance distinguishes user instructions, assistant conversation
and historical effects. Old source is not assumed current. An unavailable optional
index does not stop ordinary context construction; explicit recall errors are
reported normally. `memory.sqlite3` is private, disposable cache data.

This does not remove model limits or discard old user constraints. Oversized
mandatory intent/metadata can still pause safely. See the
[intent-memory investigation](../research/context_memory/README.md) for the exact
failure, measured retrieval study, limitations and reproduction commands.

## Tools and MCP

`read/write/edit` are schema slices of OpenHands FileEditorAction executed by
FileEditorExecutor. `bash` is TerminalAction/TerminalExecutor (PowerShell on
Windows). No hand-written file-edit/shell implementations. When generation is
needed, Flash is given exactly one native function, forced to `selected_action`
with parallel calls disabled; Jev alone selects the tool. Arguments are validated
before execution.

### Schema-determined argument bypass (source publication)

`JEV_ARGUMENT_OFFLOAD=deterministic` is the source default; `off` restores the
original always-generate behavior. After tool selection, a conservative local
schema checker can supply the ENTIRE argument object when every value is fixed:
closed empty objects, required constants/singleton enums/nulls, and closed required
nested objects. It does not infer defaults, omit optional fields or resolve remote
references. Any unsupported/free/optional field keeps the original generator and
original context. This also avoids unnecessary local Bonsai generation without
adding a paid Jev request.

The code path emits `argument_offload`, not fabricated provider usage. Existing
cancellation, native validation, `tool_started` persistence and execution remain
unchanged.28offline tests cover the schema subset, mutation isolation, unchanged
fallback, zero-versus-one generation calls for identical fixed arguments, and
actual agent persist-before-effect/completed-session no-replay behavior.
Whole-agent savings/coverage were not measured. This change is in source, not the
existing v0.2.2EXE.

The general Jev enum/span argument adapter is **not enabled**: its live quality and
cost comparison was never completed. Its39offline contracts and proposed protocol
are retained in [research](../research/argument_offload/README.md). `bounded` is not
a production setting; it fails explicitly rather than silently enabling an
unvalidated semantic decision path.

MCP tools use OpenHands create_mcp_tools and the server's authoritative input
schema, NOT SDK-injected OpenAI agent metadata. Names are prefixed `mcp.` to avoid
collisions. Configuration is read once at startup. More than 250 advertised tools (including built-in archive recall)
is rejected explicitly; use a smaller configuration or progressive MCP gateway.
Config URLs, credentials and trust remain the user's responsibility. No sandbox,
OAuth installer, transactional rollback, multi-agent orchestration or silent
model fallback is included.

## Regression commands

```
python -m unittest -v test_backend.py test_mcp_setup.py
python -m unittest discover -s benchmarks -p test_deliberation.py -v
```

Local live validation results are in research/BACKEND_CONTEXT.md. Research is not
a runtime dependency and old demo scripts are not UI entry points.
