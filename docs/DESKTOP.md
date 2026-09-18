# JevSeek desktop

A native **pywebview + React/TypeScript + CSS** workspace following
[the style directive](../DeepSeek_TypeSafe_Style_Directive.md): original pink
identity, bundled DM Sans / IBM Plex Mono, neutral reading surfaces and compact
retro activity windows. Light, dark and system appearance are supported.

## Standalone Windows app

Open `release/JevSeek.exe`. It includes Python, the frontend/fonts and Microsoft
WebView2; no Python, Node or separate WebView2 installation is needed. First
launch extracts the embedded runtime and may take a little time. This build is
unsigned. See [RELEASE.md](RELEASE.md) for platform limits, checksums, building and
publication checks. Release binaries are built separately from this source repository.

1. Review and agree to the included Microsoft runtime terms/privacy notice.
2. Paste your **DeepSeek** and **TypeSafe / Jev** API keys in the first-run dialog.
   “Get a key” opens the corresponding provider's website.
3. Save securely, choose a workspace, and send a task.

Keys are stored using native **Windows Credential Manager**, scoped to this
Windows account with local-machine persistence. They are never saved in project
files or browser storage, returned to the frontend, or exported into shell/MCP
environments. Password fields start empty and clear after a save attempt. Blank
fields retain existing keys; removal is a separate confirmed action. Changes are
blocked during a run. Saved keys take effect on the next run, without restarting.
“Configured” means present, not API-validated; saving makes no provider request.

You can revisit **Settings → Manage API keys** at any time. Environment keys are
still supported for development, but saved vault keys take precedence. Removing
a vault key does not erase or revoke an environment key; the UI shows that
fallback. Windows protection is not a defense against other software running as
your account. Never paste keys into chat. See [SECURITY.md](../SECURITY.md).

The EXE stores preferences/sessions/MCP config under `%LOCALAPPDATA%\JevSeek` and
never imports a neighboring `.env` or `mcp.json`. Moving the EXE does not move your
credentials/history. A first install has no preloaded credentials, conversations,
MCP servers or developer workspace. The initial workspace is an empty folder in
that personal data directory, not the extracted app resources.

## Run from source

Python 3.12+ and Node20.19+/22.12+ are needed for development (Node24 tested).
Windows requires PowerShell and an installed WebView2 Runtime when running from
source. The standalone EXE bundles WebView2 instead.

```sh
python -m pip install -r requirements.txt -c requirements.lock
python -m pip install -r requirements-desktop.txt -c requirements-desktop.lock
cd frontend
npm ci
npm run build
cd ..
python desktop.py
```

On Windows, source mode also supports the secure UI key form. An existing project
`.env` is loaded for CLI compatibility, **never overwritten**. Source preferences
and sessions default to `.jevseek/`; source MCP config is `mcp.json`. Keep them
ignored/private. No plaintext fallback is used if secure UI storage is unavailable;
source-mode macOS/Linux users can configure environment keys manually. Native
macOS/Linux packaging has not been validated.

Optional flags: `--workspace DIR`, `--sessions-dir DIR`, `--debug` (source only).
Saved workspace preferences take precedence over the initial `--workspace`.
`JEVSEEK_DATA_DIR` is an advanced private-state override. Developer tools are
blocked in the release EXE. Node is only needed to build, not to run built assets.

## Screens and controls

- **Conversation:** new tasks, follow-ups, offline history, Markdown/code, copy,
  factual progress and expandable tool previews. Starters fill the draft; they
  never execute automatically. Drafts persist **in memory** while navigating and
  are lost when the app closes.
- **Activity:** actual conversations, tools, errors and compaction events. A tool's
  success is not proof the requested task is correct; inspect and verify results.
- **Files:** read-only **session artifacts**, not an arbitrary filesystem browser.
  Select a conversation and inspect saved inputs/results/output/checkpoints.
  Previews are capped at64KB with a visible truncation notice.
- **Settings:** appearance, default workspace, MCP for the next run, secure key
  management, permission explanations and Microsoft runtime terms/privacy.

`Ctrl/⌘ N`: new conversation. `Ctrl/⌘ K`: history search. `Ctrl/⌘ ,`: Settings.
Enter sends; Shift+Enter adds a line. IME composition does not send accidentally.
Dialogs/drawer contain keyboard focus and support Escape. Navigation collapses
below720px; zoom/text selection/reduced motion are supported. The conversation's
menu compacts factual history **locally** without invoking providers or tools.

## Stop, close and interrupted tools

One run per window; other conversations remain inspectable. Stop requests
cooperative cancellation. **Native calls may take time to return.** Closing an
active window requests the same safe stop rather than killing uncertain effects;
close again once the run stops. Force-killing can leave side effects uncertain.

Interrupted/soft-timeout tools are marked for review. Inspect the workspace and
activity, write a follow-up, and explicitly acknowledge uncertainty in the review
dialog. Acknowledgement neither undoes effects nor declares success. Opening a
finished conversation works offline and never resumes it automatically.

## Architecture and boundaries

`desktop.py` loads only `frontend/dist`, never an arbitrary remote URL or dev
server. `jevseek/desktop.py` adapts the synchronous backend with a worker and
cursor-based event polling. `credentials.py` handles native OS storage; `paths.py`
separates immutable resources and private writable state. Routing, model choices,
compaction policy and session semantics remain the [backend v1](BACKEND.md) design;
provider keys may now be supplied directly instead of through the environment.

The native API is not a browser HTTP agent service. Artifacts are scoped to IDs
and resolved paths within the selected session. Read-only snapshots do not repair
logs. Markdown disallows raw HTML; remote images are not loaded; links open only
HTTP(S) in the external browser. Built assets have a restrictive CSP; eval is
allowed for pywebview's bridge generation, not inline scripts. The app and tools
are **not sandboxed**. Selected task context goes to providers/enabled MCP services.
History can contain private source/output despite best-effort credential redaction.
Microsoft's runtime/SmartScreen has its own disclosed network/privacy behavior.

## Development and validation

```sh
cd frontend
npm run dev       # disclosed browser preview; no native bridge or agent execution
npm run test
npm run build
cd ..
python -m unittest -v test_credentials.py test_public_audit.py test_desktop.py test_backend.py test_mcp_setup.py
python scripts/check_desktop_ui.py
python scripts/check_keys_ui.py
python scripts/check_native_desktop.py
python scripts/check_windows_release.py
```

Browser checks require Playwright1.61 (`pip install playwright==1.61.0`, then
`python -m playwright install chromium`). They use real DesktopAPI methods with
explicit test-only fixtures/vaults, not production demo data. Native/release checks
use real WebView2 and actual SDK tools. Offline checks make no model requests.
Screenshots/logs stay in ignored `.jevseek/`. Automated accessibility tests are not
human screen-reader certification or a complete security review.

`python scripts/check_desktop_live.py --run` explicitly permits a billable,
read-only real-provider task through React. For the EXE, `--self-test REPORT
--live-check` is an explicit developer-only billable read-only check using supplied
environment keys, which are removed before spawning shell tools. Neither path
is run automatically. Integration checks are not agent-quality benchmarks.

Fonts and third-party license notices are bundled. The source dev server relaxes
CSP for Vite's refresh preamble; the privileged desktop never loads that server.
