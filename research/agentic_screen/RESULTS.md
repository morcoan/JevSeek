# Fast all-three agentic screen: no added task capability

**Decision: STOP all three avenues after this pilot. No follow-up expansion, app integration or claim of a Jev capability win.**

The user requested quick tests of evidence selection, requirement/verification coverage and repeated-blocker recovery. We used thinking-enabled DeepSeek V4.1 Flash throughout the main agent and Flash-helper control. Jev did not resolve any task the competent Flash baseline failed: the baseline was already at ceiling.

## Corrected checkpoint-to-completion results

| Avenue | Flash base | Flash + classical code | Flash + Flash helper | Flash + Jev |
|---|---:|---:|---:|---:|
| Evidence selection / memory | 4/4 | 4/4 | 4/4 | 4/4 |
| Requirement-to-probe coverage | 4/4 | 4/4 | 4/4 | 4/4 |
| Repeated-blocker recovery | 4/4 | 4/4 | 4/4 | 4/4 |

Memory full-evidence reference:4/4. All52branches ended with functionally correct artifacts AND relevant passing probes on the current revision. Zero false-completion outcomes after transport correction. Jev rescues over either code-only or Flash-helper: **zero** in every avenue. The preregistered follow-up gate required >=2rescues/4 with0regressions over BOTH controls; none passed.

### Why the memory result is especially limited

All three reference records were already in the base BM25-like top6 on all4memory cases. The word/character-fusion control initially included only1/3; both semantic helpers recovered3/3, but the primary agent recovered the missing information through ordinary inspect tools anyway. Thus a semantic-helper label/retrieval win over this weaker fusion policy was **not a win over the stronger lexical baseline or completed tasks**. No gold-aware candidate insertion was used, and every helper candidate pool contained all3reference records.

This pilot did not reproduce a hard semantic-retrieval failure for the best baseline. It is insufficient to dismiss memory routing at scale, but provides no reason to expand this particular study. No dense embedding baseline was run; word/character similarity is not a dense neural retriever.

Both semantic helpers matched the correct verification probes12/12 across the coverage cases. The main agent already selected/ran the right probes without those associations. Do not advertise these correct helper labels as new capability.

## Timing: reconstructed sum of API-call durations

These include helper calls, original reused agent calls and new continuations. They are **not a fresh contemporaneous end-to-end wall-time experiment**, and do not include all local bookkeeping. Four independent branches were run concurrently.

| Median seconds / avenue | Base | Classical code | Flash helper | Jev |
|---|---:|---:|---:|---:|
| Memory | 4.01 | 5.42 | 14.19 | 4.76 |
| Coverage | 6.03 | 4.98 | 7.75 | 6.30 |
| Loop recovery | 4.79 | 4.93 | 8.03 | 5.71 |

Jev's helper was cheaper in latency than asking thinking Flash to do the helper job, but **the competent no-helper baseline was faster in all three and equally successful**. No billing, energy or FLOP claims.

## A runner defect was retained and corrected—not called a model failure

Initial run:52branches,98requests(86Flash12Jev).37branches stopped because the runner assumed exactly one native call per response. Flash returned batched reads despite requesting parallel_tool_calls=False:17two-read bundles,19three-read bundles,1read+configure bundle. These were interface failures, not evidence of weak reasoning or a Jev win.

The [transport amendment](TRANSPORT_FIX.md) uniformly supports ordered native batches, validates all schemas, limits total actions to4/branch and probes to3/model turn, and refuses actions after finish. All existing helper outputs and compatible model messages were reused. Only missing continuations were generated:54additionalFlash requests,0additionalJev/helper calls. **Same cases, not a new independent quality sample.** Original failed artifacts remain immutable.

Combined actual usage: **152provider requests =140Flash +12Jev**, below the original244cap. No result-based retries or new cases. The concrete engineering correction here was ordinary tool-call handling, not Jev.

## What these tasks were—and were not

-12fresh, seeded, authored resume checkpoints in an owned notification-configuration workflow. They were NOT real recorded customer/production agent failures.
-Memory archive:150records, random placement, project/revision filtering common to every arm. Coverage and loop tasks have three explicit current protocol notes, probe descriptions and stale/repeated/progressive histories.
-The main agent uses actual native inspect/configure_and_check/finish calls. Configuration JSON is written to a branch-local file. Owned probes read that file and simulate actual addressed delivery, repeated-message deduplication and non-ASCII wire encoding/decoding.
-Only fixed named operations and JSON data are accepted. No provider-generated code, shell, real messaging or deployment executes.
-Functional outcomes and current-revision relevant receipts determine success—not helper classifications, claimed confidence or a model's assertion of completion.
-Three explicit requirements, short histories and authored descriptions are easy enough that thinking Flash solved all cases. This is a **ceilinged screening result**, not a comprehensive negative benchmark for long-horizon agents.

## Verification / reproduction

[Protocol](PROTOCOL.md), `tasks.py`, `policies.py`, `runner.py`, `continue_screen.py`, `analyze.py`. Frozen fixtureSHA: `21928bb91149930228c379ee5ad56fa93726792a1278ffd8abb3431ce2c283d8`.

-84offline behavioral/budget/history checks before inference.
-24offline ordered-batch and post-finish/budget checks before continuation.
-All52corrected trajectories independently replayed from initial state; final JSON artifacts, receipt revisions and functional outcomes recomputed.
-Exact provider inputs/source hashes verified; no hidden expected configuration/grade labels passed to helpers or agents. Expected protocol values in ordinary visible documents are task evidence, not answer-label injection.

Private artifacts:
- `.local/research/agentic-screen/1789826483803027400` — original single-call runner, failures retained.
- `.local/research/agentic-screen/corrected-1789826904784495500` — transport-corrected continuation.

`summary.json` contains per-arm token/call accounting, paired outcomes, source coverage and all limitations. No production files or releases changed; VM/model servers were not launched.

**Practical conclusion:** do not add Jev to these agent paths on this evidence. If future work is justified, start from actual independently observed failures of a competent Flash agent, rather than making up harder puzzles until a helper wins. That would be a new study, not planned or running now.
