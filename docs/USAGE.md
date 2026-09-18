# Source and CLI guide

[← Back to JevSeek](../README.md)



Running from source requires Python **3.12+**, a DeepSeek key, and a TypeSafe/Jev key. On Windows,
PowerShell must be available. Agents run on your computer; DeepSeek/Jev requests
still send selected context to their respective APIs. No OpenHands Cloud account
or hosted agent server is needed.

```sh
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt -c requirements.lock
```

For the CLI/environment-key route, copy `.env.example` to `.env` **only if you don't already have one**.
The Windows desktop instead supports secure in-app setup; it does not require an `.env`:

```sh
# Windows: Copy-Item .env.example .env
# macOS/Linux: cp .env.example .env
```

Set `DS_KEY` and `JEV_KET` (or `TYPESAFE_API_KEY`). Default model:
`deepseek-flash`, explicitly `thinking=disabled` and `reasoning_effort=none`.
If an older `.env` contains `LLM_MODEL=deepseek/deepseek-chat`, replace it with
`LLM_MODEL=deepseek-flash`. Defaults do not silently enable thinking.

`requirements.txt` pins direct dependencies to tested versions. Always upgrade
`openhands-sdk` and `openhands-tools` **together at the same version**.
`requirements.lock` records the project's **188-package dependency closure** from
the tested Windows/Python 3.12 environment, excluding unrelated local/editable
projects. It is platform-specific, not a universal resolver lock. On a different
platform, resolve from `requirements.txt` if a constraint is incompatible, then
run the tests. After deliberate dependency upgrades in a clean development venv,
run `python scripts/lock_dependencies.py` to record the tested closure again.

## Desktop from source

A **pywebview + React/CSS** workspace with chat, inspectable tool activity,
local session artifacts, and light/dark/system appearance. Uses the same backend
and saved sessions as the CLI.

After core setup:

```sh
python -m pip install -r requirements-desktop.txt -c requirements-desktop.lock
cd frontend
npm ci
npm run build
cd ..
python desktop.py
```

Source mode requires Microsoft Edge **WebView2 Runtime**. The standalone EXE
bundles it. Node is only needed for the source frontend build. See [docs/DESKTOP.md](DESKTOP.md) for controls, architecture, platform
requirements, and UI validation. Browser `npm run dev` is a clearly labeled
interface preview; only the desktop app can run the agent.

## CLI use

```sh
python main.py "Implement the requested change and run the tests"
python main.py --workspace /path/to/repo "Fix the failing tests"
python main.py --list
python main.py --session SESSION_ID "Now add coverage for the edge case"
python main.py --session SESSION_ID
python main.py --session SESSION_ID --compact
```

Each new task invocation without `--session` starts a new session. The session
ID is printed at the end. Resume with a new prompt for follow-ups. Resuming a
completed session without a prompt returns its saved final answer, **not a rerun**.
Blocked runs can resume after the problem is resolved. `--compact` without a new
prompt performs only local compaction, with no model/tool calls.

Ctrl+C cancels and saves the session. If a tool was interrupted, its side effects
may already have happened: inspect the session artifacts/files first, then use
`--session ID --ack-interrupted` to acknowledge uncertainty. Effects are never
replayed automatically. Shell variables, working-directory changes, running
commands and editor undo state are **not restored across process restarts**.

## Context handling

- Current user intent and earlier user requests stay verbatim (except credential
  redaction). Oversized pinned requests fail visibly rather than losing constraints.
- Recent actual results stay in context; older history becomes factual index rows.
- Latest source-read snapshots survive rolling compaction. Writes invalidate the
  affected snapshot; any shell/MCP action invalidates the read cache conservatively.
- Large outputs get labeled excerpts and references to full local artifacts. The
  agent can reread those files or request a specific source line range.
- **No generated summaries, drafts or plans are fed into Jev's routing state.**
- Default context budgets: Jev 24,000 UTF-8 bytes, Flash 96,000 bytes, including
  reserved instruction/schema overhead. These are conservative size limits, not
  provider billing-token counts. See `.env.example` to configure them.

Sessions, archives, checkpoints, events and usage are in `.jevseek/sessions/`
(gitignored). Keep these private: redaction is best-effort and files can contain
sensitive source code/tool output. Compaction keeps archives, so disk usage grows;
remove old sessions manually when no longer needed.

## MCP: install by prompting

```sh
python main.py "Install Blender MCP at http://127.0.0.1:9765/mcp, check it, and tell me how to restart"
```

The agent uses `mcp_setup.py` to merge `mcp.json`, check the handshake, and tell
you to **exit and rerun the agent**. Existing sessions do not gain newly configured
tools. HTTP/streamable HTTP, SSE and stdio are supported. Stdio commands must
already be installed/trusted; registration is not an arbitrary package downloader.

```sh
python mcp_setup.py add-http blender http://127.0.0.1:9765/mcp
python mcp_setup.py add-stdio myserver python /absolute/path/server.py
python mcp_setup.py check blender
python mcp_setup.py list
python mcp_setup.py remove blender
python main.py --no-mcp "Repair the MCP configuration"
```

Labels are case-insensitive for updates/checks/removal, so Blender/blender does
not create duplicate entries. See `mcp.example.json`. Machine-local `mcp.json`
is ignored by git; use `${ENV_NAME}` in headers/env instead of storing real keys.
Set `enabled: false` to disable a server. Automatic OAuth setup is not implemented.

**Security:** local shell, editor and MCP tools run with your account's privileges.
This is **not a sandbox**. Use trusted repositories/servers or an isolated OS/container.
Neither Jev confidence nor context compaction is an authorization boundary.

## Development / UI integration

```sh
python -m unittest -v test_desktop.py test_backend.py test_mcp_setup.py
python -m unittest discover -s benchmarks -p test_deliberation.py -v
python main.py --json --no-mcp "Your task"
```

`--json` emits versioned JSONL on stdout; diagnostics go to stderr. Backend
`Agent.run()` accepts an event callback through `Session`, so a UI can show
routing, tool execution, generation progress, compaction, usage and final answers
without changing agent behavior. Final status is `completed`, `needs_input`,
`blocked` or `cancelled`; it is not a substitute for independent tests.

See [docs/BACKEND.md](BACKEND.md) for the frozen UI-facing contract and
limits. The desktop adapter consumes this contract without changing the agent's
routing or context policy. See [docs/DESKTOP.md](DESKTOP.md) for UI development.

