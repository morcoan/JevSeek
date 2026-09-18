# Windows release and publication checklist

## End-user build

`release/JevSeek.exe` is a **single-file Windows x64 application**. It includes
Python, the agent's Python dependencies, the built React UI/fonts, and Microsoft's
Fixed Version WebView2 Runtime. Python, Node, npm and a separate WebView2 install
are not needed to run it. The executable extracts its bundled components to a
private temporary directory, so first launch takes longer than a normal script.
Allow roughly 1.5 GB of temporary disk space.

Supported target: Windows 10/11 x64 with the normal Windows PowerShell and .NET
Framework 4.8 components. Validation is on Windows 11; a fresh Windows VM and all
Windows editions have not been certified. Project-specific tools (Git, Python for
a Python project, Node for a Node project, Blender/MCP servers, etc.) are **not**
bundled. JevSeek runs with the signed-in user's permissions; do not run as admin.

On first launch, review the Microsoft runtime terms and privacy notice, then add
DeepSeek and TypeSafe/Jev keys in the UI. Save does not contact providers or spend
credits. Pick a workspace and send a task when ready.

Personal state goes to `%LOCALAPPDATA%\JevSeek`:

- `desktop.json`: appearance/workspace/MCP preferences.
- `runtime-terms.json`: the user's explicit runtime-license choice.
- `sessions/`: private conversations, tool output and context artifacts.
- `mcp.json`: user-created MCP configuration (empty/absent in a new install).
- `workspaces/default/`: an initial empty workspace, not the app's resource folder.

Keys use native Windows Credential Manager with local-machine persistence under
`JevSeek`, not plaintext files, browser storage, or the extracted application.
The release never loads an adjacent or working-directory `.env` or `mcp.json`.
`JEVSEEK_DATA_DIR` is an advanced override for personal state; keep it private.
Copying the EXE to another computer does not copy keys or history.

**Unsigned:** no code-signing certificate was supplied. The EXE is not
Authenticode-signed and Windows may warn. Verify `SHA256SUMS.txt`; do not disable
Defender or SmartScreen. Sign a release with a legitimate publisher certificate
before broad distribution. No antivirus certification or false-positive guarantee
is claimed. Never upload private session traces to an issue tracker or scanner.

## Repeatable local build

```powershell
python -m venv .build-venv
.build-venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-desktop.txt -r requirements-build.txt -c requirements.lock -c requirements-desktop.lock
cd frontend
npm ci
npm run build
cd ..
.build-venv\Scripts\python.exe scripts/prepare_webview2.py
.build-venv\Scripts\python.exe scripts/build_windows.py
python scripts/check_windows_release.py
```

The pinned Microsoft CAB is fetched directly from Microsoft, SHA-256 checked and
its main executable's Microsoft Authenticode signature checked. Build staging is
an **allowlist**, not a recursive copy of this checkout. It cannot include `.env`,
local MCP config, `.pi`, `.jevseek`, archives, research traces or developer caches.
PyInstaller analysis runs in an isolated venv with secret-like environment variables
removed. Build artifacts and the runtime cache are ignored by Git.

The Fixed Runtime **does not auto-update**. Maintainers must periodically refresh
`packaging/webview2.json`, verify the official download/signature/new checksum,
review terms, rebuild and test. Do not redistribute the runtime CAB on its own.
`--record-initial-hash` is a maintainer pin-update operation, not a bypass for an
existing checksum mismatch. The package retains Microsoft's component notices;
Python/JS/OFL notices are included in `THIRD_PARTY_NOTICES` and the frontend.

The source code's overall license has not been selected by the owner. Public Git
visibility alone is not an open-source reuse license. Choose an appropriate project
license before inviting reuse/contributions; third-party licenses remain in force.
Microsoft terms/distribution requirements also apply to binary redistribution.
See [THIRD_PARTY.md](THIRD_PARTY.md) for notice provenance and references.

## Before a public Git push

```sh
python scripts/public_audit.py --history
python -m unittest -v test_public_audit.py test_credentials.py test_desktop.py test_backend.py test_mcp_setup.py
python scripts/export_public.py
```

- Review the exact Git candidate/index file list, not the whole folder in Explorer.
- `.gitignore` hides local credentials, agent memory, sessions, logs, generated
  workspaces, environments, build caches and release binaries. It is **not
  encryption** and does not remove already committed files/history.
- `public_audit.py --staged` reads the actual staged blob bytes. `--history` checks
  all reachable historical blobs, including deleted files. Findings never print
  matching secret values. Known local key equality, credential patterns, private
  paths and the current user's home paths are checked; this is not a proof against
  every unknown/obfuscated secret. Review sensitive changes manually too.
- Enable the local hook: `git config core.hooksPath .githooks`.
- Enable GitHub secret scanning and push protection when the repository exists.
- Do not add `release/`, a whole-folder ZIP, screenshots, logs or `.pi` memory.
- `release/public-source/` and `release/JevSeek-source.zip` contain only audited,
  Git-eligible source. Use these if uploading through a browser. They contain no
  `.git` history, executable, private profile or node_modules.
- Build binaries belong in release assets, **not Git history**. Re-scan the final
  EXE after rebuilding/signing and regenerate its checksum.

Local setup and exports do not create a remote, commit, push, GitHub repository,
or public release. Publication remains an explicit owner action.

## Validation boundaries

The EXE validator copies **only the EXE** to an unrelated directory, strips API and
Python settings, restricts PATH to Windows/PowerShell, and plants adjacent config
bait that must not load. It checks native SDK write/read/edit/shell, vault operations,
real bundled WebView2/bridge/rendering, and the windowless bundled MCP helper. It
makes no model calls. Source UI tests cover additional keyboard/a11y/error cases.
A real-provider read-only smoke is opt-in and billable, not a quality benchmark.

This is targeted isolation testing, not a substitute for testing on a fresh Windows
VM, code signing, an independent security review, or maintaining dependency updates.
