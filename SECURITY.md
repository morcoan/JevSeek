# Security and private data

JevSeek is a **trusted local coding agent, not a sandbox**. File/shell/MCP tools
have your Windows account's privileges. Use trusted workspaces and MCP endpoints,
or isolate the app in a separate OS account/VM for untrusted projects. Do not run
as administrator. Neither router confidence nor context compaction is an
approval/security boundary.

## Credentials

- Use the desktop key form, not chat. Keys are stored with Windows
  `CredWrite/CredRead` (generic credential, **LOCAL_MACHINE** persistence, current
  Windows account). No roaming, keyring plugin discovery, plaintext fallback or
  previous-value shadow copies are used.
- Stored key values are never returned to JavaScript. Password fields start empty
  and are cleared after a save attempt. No key is put in localStorage, a URL,
  settings JSON, logs or the executable.
- Vault keys are passed directly to provider clients, **not exported into the
  environment inherited by shell/MCP subprocesses**. Legacy source `.env`/shell
  keys remain supported and can be inherited; prefer the vault for desktop use.
- Saved app keys take precedence over environment keys. Removing an app key does
  not remove an environment key or revoke it at the provider; the UI discloses
  that fallback. Revoke a compromised key at its provider.
- Changes are rejected while a run is active. Previously used keys remain
  redacted for the rest of that process. Redaction is best-effort, not encryption
  of session history. Unknown secrets in source/tool output can still be saved.
- Windows protection does not defend against malware or another process running
  as the same logged-in account. Account backups/OS recovery can retain data;
  removal is not a forensic secure-erase promise.

## Desktop boundary

The privileged webview loads only bundled local assets. It cannot be pointed at a
remote development URL. Markdown does not execute raw HTML; remote images are
not fetched. A restrictive CSP applies; eval is enabled only because pywebview
constructs its bridge functions dynamically. Release developer tools are disabled.
Artifact viewing accepts only IDs referenced by the selected session and rejects
resolved paths outside that session. External links accept only HTTP(S), without
embedded credentials/control characters.

The standalone app stores writable state under `%LOCALAPPDATA%\JevSeek`, outside
the EXE and source tree. It never imports a neighboring `.env` or `mcp.json`.
Conversations contain private code and should not be uploaded. Stop/close is
cooperative; do not assume a force-killed tool had no effects. Review interrupted
side effects before acknowledging and continuing.

## Network/privacy

Task context goes to Jev and enabled MCP services when a task runs, and to DeepSeek only when cloud generation is selected. Optional [local Bonsai](docs/LOCAL_MODELS.md) replaces DeepSeek, not Jev. Model/runtime downloads are pinned and SHA-256 verified; the owned model server is authenticated and loopback-only.
API providers have their own billing/retention/privacy terms. The bundled Microsoft
WebView2 Runtime can communicate with Microsoft, including Defender SmartScreen
and runtime diagnostics. SmartScreen is enabled; see Microsoft's
[Privacy Statement](https://aka.ms/privacy) and
[Edge Privacy Whitepaper](https://learn.microsoft.com/en-us/microsoft-edge/privacy-whitepaper#smartscreen).
The UI and bundled runtime terms disclose this; JevSeek does **not** claim that
all runtime/OS network traffic is disabled.

## Before publication

Run `python scripts/public_audit.py --history`, inspect the candidate file list,
and use `scripts/export_public.py` instead of zipping the local folder. Ignore
rules cannot undo an earlier commit; a leaked credential must be revoked even if
removed from history. Enable hosting-provider secret scanning/push protection.
Never paste keys, complete private tool traces or credential-vault exports in a
public issue. Report security issues privately to the repository owner through
GitHub's private vulnerability reporting channel if available. Otherwise request
a private contact without posting the vulnerability details or sensitive data.
