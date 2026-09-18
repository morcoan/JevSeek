# Local Bonsai generation

Windows x64 desktop builds can replace **DeepSeek generation** with either:

- [Prism Ternary Bonsai 2 27B](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf), the recommended official model.
- [Bonsai 2 27B Ternary CRACK](https://huggingface.co/dealignai/Bonsai-2-27B-Ternary-CRACK-GGUF), a separate community variant. Review its model card, behavior and license before choosing it.

**Jev remains an online routing service.** You still need a TypeSafe/Jev key, and task context still goes to Jev and any enabled MCP services. This is not a fully offline agent.

## One-click setup

1. Open **Settings → Generation model** (also linked from first-run key setup).
2. Choose a model, then click **Set up & use Bonsai**.
3. Watch download, integrity-check, installation, loading and compatibility-test progress. Successful setup automatically switches generation to Bonsai. No DeepSeek key is needed afterward.

No terminal, Python, CUDA toolkit or separate model-server installation is needed in the EXE. The GGUF and runtime are downloaded on demand, not embedded in the EXE. Setup makes no paid model requests; running an agent task still bills Jev.

The native PQ2_0 GGUF is about 7.2 GB. Allow **10 GB free disk** for one model and its runtime; each additional model needs another 7.2 GB. At least 16 GB system RAM is recommended, with more needed for comfortable CPU operation and other apps. Compatible NVIDIA GPUs with sufficient free VRAM use CUDA; otherwise setup uses the slower CPU backend. Other GPU vendors are currently CPU-only. Automatic GPU selection is conservative, not an exhaustive hardware optimizer.

Both modes use the same pinned distribution, including its generic CPU backend. The separate optimized CPU archive was rejected after a native PQ2_0 crash in testing. CPU mode was tested on the development machine, not certified across all CPUs or machines without an NVIDIA driver.

Setup uses the **Prism llama.cpp fork** (`prism-b10685-7dffb15`); stock llama.cpp is not substituted for native ternary kernels. Model revisions and runtime SHA-256 digests are pinned in `jevseek/bonsai.py`. CUDA 13.3 requires a recent driver. If GPU startup fails, setup tries CPU rather than silently sending context to DeepSeek.

## Downloads and existing files

- Progress is per file/stage, including bytes and transfer speed.
- Cancel keeps `.part` downloads. Retry resumes when the host supports HTTP byte ranges; an ignored range restarts safely.
- SHA-256 and exact size are checked before a file is used. Invalid downloads are not activated.
- Existing matching GGUFs in a sibling/root `badbonsai` folder are detected and hashed before reuse. They are not moved, deleted or converted. Keep that file available afterward.
- In a packaged app, data lives in `%LOCALAPPDATA%\JevSeek\bonsai`; source runs use `.jevseek/bonsai`. `JEVSEEK_DATA_DIR` follows the desktop launcher's normal rules.
- Setup requires access to Hugging Face, its download CDN and GitHub. Corporate proxy-only networks are not currently supported by the isolated downloader.

A successful local server must pass forced native tool-call and structured-summary checks before the selected provider changes. Compatibility is not a guarantee of answer quality.

## Running and switching

Bonsai is started automatically when a local run needs it. It listens only on a random loopback port, requires a per-process API token, and does not inherit provider keys. JevSeek owns and closes only its own server; unrelated servers such as `badbonsai` on port 8080 are left alone. Closing the app releases its model process; Windows job ownership also handles unexpected app exit.

Choose **Switch to DeepSeek** to release local GPU memory and restore cloud generation. A configured DeepSeek key is required for the next cloud task. Downloads remain cached. Provider switching is blocked during active tasks; failed local startup does not silently fall back to cloud generation.

Local generation uses a 32,768-token server context, a conservative 24,000-byte input budget and up to 4,096 output tokens for arguments. This can compact/pause earlier than DeepSeek. Pinned user requests, schema validation, selected-action enforcement, effect logging and interrupted-call protections remain in place. Large edits may need to be split across tasks.

Local files, installed runtimes and model cards should still be treated as trusted software inputs. Models can make mistakes. Tools retain your account's permissions and are not sandboxed.

## Verification

Offline regressions: `python -m unittest test_bonsai`.

Opt-in integration: `python scripts/check_bonsai_live.py --run --model crack` (or `prism`). This can download gigabytes, use substantial GPU/RAM and incur Jev API charges. It drives actual React setup and a read-only native-tool task without a DeepSeek key, then checks the unchanged fixture and browser accessibility. Private reports stay in ignored `.jevseek`.
