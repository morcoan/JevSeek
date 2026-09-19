# Terminal-Bench 4 — local Bonsai + Jev research

## Publication status: cancelled, VM stopped, no benchmark score

The user stopped the CRACK+Jev sweep and then the VM. Neither was restarted for publication. The66task dataset had33resource-eligible tasks, but the sweep did NOT finish:

| Task | Retained outcome |
|---|---|
|`atrx-vep-crispr`|Verifier reward0; not a success|
|`batched-eval-parity`|No verifier reward;1trial error—not a scored success|
|`bun-sourcemap-leak`|Interrupted by the user; unscored and not replayed|

Two completed controller records do not mean two successfully completed benchmark tasks. See `partial_summary.json` for the sanitized original status and its hash. The separate smoke reward1.0 below validates wiring only, never a Terminal-Bench score. No completed sweep, comparative capability/cost result, or application improvement was demonstrated.

The setup/commands below are **historical provisioning notes**, not a claim that the VM/model server is running now. Starting them requires explicit user intent, your own private assets and credentials. This repository does not ship VM disks, SSH keys, upstream task data, models or raw jobs.

## Historically provisioned on the research machine

- **Terminal-Bench 4.0.0:** 66 tasks, pinned to official commit `452bf305c6daa62fc59061d22133a7cbc7c1572e`.
- **Linux sandbox:** Ubuntu 24.04 in portable QEMU 11.1 with existing Windows Hypervisor Platform acceleration. No Windows reboot, feature activation, boot changes, Docker Desktop install, host firewall changes or host-drive sharing.
- **Docker 29.1.3 / Compose 2.40.3** run inside that VM, not on Windows.
- **Harbor 0.23.0** and the isolated Python research environment are installed inside Linux.
- **DeepSeek is disabled.** Generation requires a loopback Bonsai endpoint; routing uses Jev. There is no cloud generation fallback or cloud sandbox.

A real, separate integration fixture completed through Harbor → Jev → Bonsai → Linux container Bash and received **verifier reward 1.0** with no trial exceptions. Usage contained only `bonsai` and `jev`. This checks integration; **it is not a Terminal-Bench result or score**. This is not a full 66-task benchmark score. Actual sweep progress is recorded separately under `.local/research/sweeps/`.

## Commands

From the project root, in PowerShell:

```powershell
# Check or start the already-provisioned private Linux VM.
python research/tbench4/vm.py status
python research/tbench4/vm.py start

# List all downloaded tasks and resource eligibility; no model requests.
python research/tbench4/run.py --list

# Real end-to-end integration check. Jev calls are billable.
python research/tbench4/run.py --smoke --run

# Run ONE eligible Terminal-Bench task. Replace TASK_NAME with a listed directory.
python research/tbench4/run.py --task TASK_NAME --run

# Run all 33 eligible tasks once, sequentially; require CRACK specifically.
python research/tbench4/sweep.py --run

# Shut down ONLY the research Linux VM, never Windows.
python research/tbench4/vm.py stop
```

The sweep writes an atomic `status.json` with the current task and completed results. Put an empty file named `STOP` in that sweep's directory to stop scheduling **after the current task**. Do not shut down the VM/model server during an active trial. Infrastructure failures pause the scheduler; it does not automatically replay interrupted tasks. Guest/host disk reserves are checked before each new task.

On this machine, a later WHPX guest crash exhibited shadow-stack faults. The VM now direct-boots the matching publisher-verified Ubuntu kernel/initrd with `nousershstk`; this change is confined to QEMU's guest command line and does not modify Windows boot settings. Recovery passed process-creation and Docker checks; long-run health still needs monitoring.

The historical controller used a local `llama-server` on **127.0.0.1:8080**, alias `bonsai`, with the CRACK model. That model server is no longer assumed to be running. The controller checks the reported model file's full SHA-256 against the pinned official/CRACK manifests before running. It does not stop or replace your existing model server. Use `--port PORT` for another local server; authenticated servers require `BONSAI_API_KEY` in your shell. Remote/cloud generation endpoints are not supported.

Jev credentials come from the normal environment, source `.env`, or Windows Credential Manager. They are passed through encrypted SSH stdin into the external agent's memory, not command-line arguments, Docker environments, task files, or Harbor job configuration. The controller never exports the source `.env` into Linux. Jev still receives task context and charges for routing; local Bonsai has no API fee but consumes local compute/electricity.

## Resource limits and honest comparisons

The VM is limited to **4 vCPUs and 6 GB RAM**, with a **100 GB sparse virtual-disk capacity**, to leave room for Windows and Bonsai. One trial runs at a time, one attempt, no automatic trial retries. Official task timeouts are retained; many TB4 tasks permit up to eight hours.

**33 of 66 tasks nominally fit** the current main-container allowance (up to 4 CPUs, 4096 MB task RAM, no GPU and no task MCP). The other tasks are rejected before inference rather than reducing their declared requirements. GPU passthrough is not configured, and the agent's use of the Windows GPU does not provide a GPU to benchmark task containers. Multi-service overhead, image downloads, nested virtualization and every task's full execution have not been validated. The first real task may still need to build/download its environment.

Do not call a selected subset a full TB4 score. Do not compare timing directly with another machine, concurrency level, resource configuration, agent toolset or repetition count. A model claiming completion is not a success: **Harbor's verifier result determines the task reward**. Actual Jev billing is unknown to the SDK; total cost is left unknown, not incorrectly reported as zero. Per-model token counts and raw SDK usage are retained.

## Agent boundary

`agent.py` uses the existing JevSeek `Agent`, deterministic `Context`, session persistence and provider `Models` code, without modifying production runtime files. The research-specific tool adapter offers **container Bash only**, rather than desktop OpenHands file/terminal tools or machine MCP connections. Shell calls are independent; commands must specify `cd` explicitly when needed. This is a distinct benchmark tool configuration and must be identified as such in results.

Jev selects an action from actual history. Non-thinking Bonsai produces a forced native `selected_action` call or a structured summary. Arguments are validated before effects. Tool outputs are archived locally and copied into the task container so compacted observations remain rereadable. Only the task instruction and actual observations enter model context; the adapter does not read host verifier/reference-solution files. Harbor installs/runs its verifier separately. Unknown/interrupted effects are not automatically replayed.

## Isolation and local data

- QEMU runs without elevation, at below-normal Windows process priority, with no shared host filesystem, clipboard, USB/GPU passthrough, Docker socket or physical disk.
- SSH binds only to a random **Windows loopback** port with a dedicated key and pinned local known-hosts file. The model tunnel listens only on **VM loopback** while a run is active.
- Guest-only firewall rules block access to the Windows gateway/private LAN, including the host's model-server port. The external agent reaches Bonsai through the authenticated SSH reverse tunnel; task containers cannot reach that loopback listener.
- Public internet access remains available for task packages/images. This is not an air-gapped environment or a guarantee against all VM/container vulnerabilities.
- No provider key is injected into task containers. No personal Windows directories are mounted in them.
- Harbor telemetry is disabled for runs. No upload/publish option is used.

Private assets live under ignored `.local/research/`: VM disks, SSH key, downloaded upstream repositories, build caches, validation reports and run logs. Each completed controller run collects the raw Harbor job as `runs/<timestamp>/harbor-results.tar.gz`, alongside `manifest.json` and `run.log`. Guest originals are in `~/jevseek-bench/jobs`. Do not commit these artifacts; benchmark logs may contain task code. `installed-research.lock` in the guest records its exact resolved packages.

Dataset deployment uses **raw `git archive` bytes and Unix modes**, not Windows checkout line endings. All 2581 dataset/license blobs in the guest were checked against the pinned Git tree with zero mismatches. Official task scripts and verifiers were not edited. The separately authored smoke fixture is clearly labeled and never included as a TB4 task.

## Validation / maintenance

Offline adapter tests (in the isolated harness environment):

```powershell
.local\research\harness-venv\Scripts\python.exe -m unittest research.tbench4.test_adapter -v
```

Six guards cover loopback-only endpoints, forbidden alternate models, ambient DeepSeek-key immunity, schema validation before effects, container workspace identity and actual core-loop/container transport integration. They passed on Windows and Linux; the real smoke verifier passed separately.

This is a locally provisioned research setup, not a portable installer or a new desktop EXE release. The existing desktop build and user's `badbonsai` server are unchanged. VM/bootstrap scripts and download checksums are retained privately under `.local/research/` for inspection. Reprovisioning another machine requires an explicit setup step; do not assume the private VM files or SSH keys are in the public repository.

Upstream: [Terminal-Bench](https://github.com/harbor-framework/terminal-bench/tree/v4.0.0) · [Harbor custom agents](https://harborframework.com/docs/core-concepts/agents/custom-agents) · [QEMU Windows builds](https://qemu.weilnetz.de/w64/) · [Ubuntu cloud images](https://cloud-images.ubuntu.com/).
