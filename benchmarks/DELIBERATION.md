# Flash 4.1 native max versus Jev-gated deliberation

[← Research overview](../RESEARCH.md)

> **Reading this record:** sections retain the experiment's chronological state,
> including outages and later retries. “Defaults unchanged” below refers to the
> time of those experiments; today's runtime uses plain non-thinking Flash + Jev.
> Named trace files/directories are historical private evidence, not files shipped
> in this repository. Public runners and evaluator fixtures support fresh runs.

## Subsequent runtime decision

User selected plain non-thinking Flash + Jev JIT for the production backend. The
migration/context work is documented separately in [../research/BACKEND_CONTEXT.md](../research/BACKEND_CONTEXT.md).
Statements below about unchanged defaults describe the experiment's historical
state; the original measurements/traces are preserved. Jev doing most of the
heavy lifting remains an untested attribution, since all three arms used Jev.

## Latest finding

Successful service-recovery retries are recorded at the end of this report. On this task, plain non-thinking Flash + Jev JIT completed all 30 tests in 35.05s; native max previously completed in 503.25s; synthetic_v2 halted for missing evidence with 11/30 tests in 114.43s. Prefer the plain argument-generation path for now; no production defaults were changed. Historical outage results below are preserved, not overwritten.

## Experiment contract

Same `deepseek-flash` alias in every arm (official docs identify it as DeepSeek V4.1 Flash). This is an API alias, not a pinned immutable checkpoint. Record response model/system fingerprint on every call.

The independent variable is how arguments are produced for an ALREADY selected tool. All arms use the same Jev JIT router, executor, user intent, initial files and 30 independent build-engine tests from the earlier experiment. This is NOT a comparison against an entirely DeepSeek-controlled agent.

1. **native**: `thinking.type=enabled`, `reasoning_effort=max`; generates JSON arguments directly. Native reasoning remains internal to that call.
2. **synthetic**: `thinking.type=disabled`, `reasoning_effort=none`; DeepSeek generates a working analysis/argument sketch. Jev sees user intent, actual turns, chosen tool and accumulated drafts and chooses `continue` or `enough`. Repeat on continue. On enough, non-thinking DeepSeek generates final JSON arguments with those drafts as advisory context.
3. **plain control**: disabled thinking, no draft/gate; directly generates JSON arguments. This tests whether the extra mechanism adds anything over non-thinking alone.

The argument generator cannot select a different tool. The tool router gets ONLY user intent plus completed tool arguments/observations. Drafts/gate answers never enter its state. Drafts are reset for each selected tool and are not executed. This preserves the no-model-plans-in-tool-routing decision. The deliberation gate is a separate role and CAN be misled by confident wrong drafts; readiness is not correctness. Acceptance tests remain the success criterion.

All arms receive a 131,072 output-token ceiling per DeepSeek request, including native reasoning. This is NOT a matched total compute budget: synthetic may make multiple calls. No turn or deliberation-round limit; HTTP client timeout is 240 seconds (a socket/inactivity timeout, not a strict total generation deadline; server keep-alives can make calls last longer), per-test process timeout 120 seconds. Unexpected native reasoning in the non-thinking arms or truncated responses fail the run instead of silently falling back. Native mode does not necessarily reason on every easy read request.

Final summaries use non-thinking Flash identically across arms, based only on actual execution and test output. They are included in total calls/usage. No MCP connections or scene operations are involved.

## Verification and reproduction

`flash-probe.json`: explicit none/max API smoke test; same correct answer, none returned zero reasoning characters, max returned native reasoning and reported reasoning-token usage.

```sh
python -m unittest discover -s benchmarks -p test_deliberation.py -v
python benchmarks/compare_deliberation.py native
python benchmarks/compare_deliberation.py synthetic
python benchmarks/compare_deliberation.py plain
```

API keys are loaded from .env (DS_KEY and JEV_KET/TYPESAFE_API_KEY); never included in logs. Six unit tests cover mode flags, same model/ceiling, gate-controlled repetition, and draft/router separation. OpenAI SDK is a tracked direct dependency. Production runtime defaults are unchanged.

Each fresh run writes `deliberation_results/<mode>-<timestamp>-<id>/` with request prompts/options, responses (excluding native reasoning text), Jev answers, full tool traces, token/cache usage, model fingerprints, independent evaluator output and result.json. A failed/interrupted run must not be treated as a completed success even if its partial artifact passes tests.

Official references checked:
- https://api-docs.deepseek.com/api/create-chat-completion (supports `reasoning_effort=max/none` and thinking toggle)
- https://api-docs.deepseek.com/quick_start/pricing (Flash 4.1 alias)
- The older thinking-mode guide still shows legacy model names; use the current API schema and verified endpoint rather than assuming deepseek-chat means non-thinking.

## Results: first live attempt

| Arm | Execution status | Independent tests at exit | Tool actions | Successful Jev calls | DeepSeek calls | Elapsed |
|---|---|---:|---:|---:|---:|---:|
| Native max | Completed | 30/30 | 8 | 9 router | 9 including summary | 503.25 s |
| Synthetic | Stalled; then interrupted by Jev HTTP 503 | 1/30 (unchanged starter) | 3 reads | 4 router + 45 gate | 46 drafts + 3 arguments | 131.36 s |
| Plain control | Jev HTTP 503 before any action | 1/30 (unchanged starter) | 0 | 0 | 0 | 2.29 s |

**No valid completed three-way performance ranking yet.** Native completed successfully. Synthetic displayed a genuine non-progress loop before the infrastructure error. Plain did not run, so nothing about non-thinking-alone quality can be inferred. Both interrupted artifacts remain the starter, not failed generated implementations. The synthetic/plain exit was automatic on SDK exceptions, NOT a manual cancellation or imposed round cap. A subsequent minimal Jev health request also returned HTTP 503.

### What happened

Native tool sequence: `read/read/read/read/edit/edit/bash/bash/done`. The first substantive max-effort response took 270.70 seconds, using 69,328 output tokens (64,977 reasoning). It returned write-style `{path,content}` for the selected edit tool, which requires `{path,old,new}`; the harness rejected it rather than silently converting it. The next edit took 219.46 seconds and succeeded. Public and independent tests then passed.

Synthetic read preparation needed one, one and three draft passes. For the first edit, the gate repeatedly requested more deliberation. DeepSeek initially elaborated the solution, then repeatedly replied `Declined. No new evidence; draft unchanged.` The gate continued even on those identical drafts; its final successful decisions had roughly 0.49–0.51 confidence. In total there were 46 drafts across tool turns, 45 successfully completed gate calls, and no executed edit. The next gate request failed with HTTP 503 after SDK retries. The subsequent control failed on the same service error before it could start.

This separates two issues: **gate liveness/stagnation** (observed before outage) and **service availability** (prevented completion). The binary gate emits no actionable explanation of what needs improvement. More requests alone do not guarantee progress. Low gate confidence also needs an explicit policy; the initial experiment followed the winning label without a confidence override.

### Token usage (successful reported responses only)

| Arm | DS prompt | DS cache hits | DS completion, including native reasoning | Reported native reasoning | Jev input |
|---|---:|---:|---:|---:|---:|
| Native | 85,975 | 39,040 | 126,183 | 117,193 | 85,345 |
| Synthetic, incomplete | 594,178 | 577,536 | 15,460 | 0 | 598,217 |
| Plain, not started | 0 | 0 | 0 | 0 | 0 |

The synthetic loop cached well but did not implement anything. Its partial elapsed time/token use MUST NOT be presented as a completed-task speed/cost win. Failed requests and SDK retries are not included in successful-call totals. No dollar-cost conclusion is drawn. Per-call usage, options and full draft/tool traces are preserved.

### Next experiment / deployment conditions

- Retry the plain control after Jev recovers, preserving this failed attempt.
- Keep the original synthetic run as evidence. Test any improved gate as a separately labeled variant, not a retroactive replacement.
- Add a deterministic no-progress detector that halts/asks for intervention on identical repeated drafts; this is not an arbitrary turn cap and should NOT count as Jev saying enough.
- Evaluate readiness to produce arguments, not endless speculative completeness. Consider structured gap checks so the next draft knows what to fix. Use actual test feedback rather than pretending more prose can reveal unseen results.
- Do not adopt synthetic deliberation as the default based on this attempt. Production defaults remain unchanged.

Evidence directories:
- `deliberation_results/native-20260917-125528-85aca0/`
- `deliberation_results/synthetic-20260917-130356-ce1961/`
- `deliberation_results/plain-20260917-130612-eb947a/`

Cache and latency are descriptive, not isolated causal measurements. One task does not establish a general capability ranking. Confidence should not be interpreted as an independently calibrated measure of draft correctness.

## Follow-up: separately labeled synthetic_v2

Implemented after the first attempt, without replacing the original `synthetic` arm:

- Gate examines only the latest draft, not stale accumulated drafts, alongside intent, actual turns and selected-tool schema.
- Outcomes: `enough`, `schema_gap`, `design_gap`, `contradiction`, `needs_evidence`. The three gap labels request another pass and supply the corresponding category as feedback; they are not generated explanations.
- Readiness means sufficient to GENERATE arguments next. Drafts need not already contain a complete module or exact final JSON. Unrun tests are not evidence that more deliberation is needed.
- Missing essential external evidence halts with `DeliberationNeedsEvidence` rather than fabricating context.
- Repeated/cycling drafts, hashed after whitespace normalization, halt with `DeliberationStalled`. This never forces `enough` or executes a tool. It detects exact normalized repetition, not paraphrases; whitespace-only changes in code can conservatively trigger it.
- Only the latest approved draft is passed to final argument generation. All drafts remain excluded from tool-router history.
- No arbitrary turn/round limit. Model-based readiness remains fallible; these guards do not prove convergence on changing/paraphrased drafts.
- Results now distinguish `artifact_pass` from completed `pass`; interruptions and summary failures cannot be labeled completed success.

### Validation

10/10 unit tests pass, including cycle/repeat halt, missing-evidence halt, no argument-generation call after a halt, latest-only advisory context, and unchanged router isolation.

Offline replay of the recorded stalled trace: the guard would halt at **edit draft 16 / total draft 21**, after the same three reads, versus 46 total drafts in the original run. This is deterministic replay of saved outputs, NOT evidence that the revised Jev gate solves the task. Details: `deliberation-repeat-replay.json`.

### Live retries blocked

A small health request briefly returned HTTP200. However, both full retries failed before any tool or DeepSeek call:

- `deliberation_results/plain-20260917-131221-8755fa/`: HTTP503, zero actions.
- `deliberation_results/synthetic_v2-20260917-131228-dc49d3/`: HTTP503, zero actions.

A fresh unique small request and the exact router request then both returned:
`{"detail":{"error_type":"model_unavailable","message":"The model is unavailable. If this issue persists, please contact support."}}`

Saved in `jev-health-v2.json` without credentials. This is an infrastructure blocker, not a quality result for v2 or the control. No background runs remain. Production defaults are unchanged. Next: check availability with the real router request, then rerun the control and v2 without overwriting these failed attempts:

```sh
python benchmarks/compare_deliberation.py plain
python benchmarks/compare_deliberation.py synthetic_v2
```

## Retry after recovery: usable comparison

The exact initial router request returned HTTP200 (`jev-retry-health-20260917-132132.json`). Ran plain, then synthetic_v2 sequentially with unchanged parameters, task and evaluator. Neither run encountered a service outage. The older native-max result remains the reference; it was not rerun.

| Arm | Tests | Status | Actions | Successful Jev calls | DS calls | Elapsed |
|---|---:|---|---:|---:|---:|---:|
| Native max (earlier run) | 30/30 | Complete | 8 | 9 | 9 | 503.25s |
| Plain nonthinking retry | **30/30** | **Complete** | 16 | 17 | 17 | **35.05s** |
| Synthetic_v2 retry | 11/30 | Needs-evidence halt | 8 | 21 | 20 | 114.43s |

Plain used 9 reads, 3 edits and 4 bash actions. It initially mishandled incremental dependency ordering, failing output-tampering and missing-output tests. JIT allowed a correction using actual test results; it reran the public and independent suites successfully. The final DeepSeek summary accurately described the fixes and verification.

Synthetic_v2 used 4 reads, 2 edits and 2 bash attempts, with 12 drafts/12 gate calls and 8 final argument-generation calls. One bash payload attempted to chain both test commands and was rejected by the shared command allowlist. A subsequent public test exposed a cache invalidation bug. Its next patch introduced a call to undefined `_fingerprint_node`. Before another tool executed, the gate progressed through contradiction labels and then chose `needs_evidence`. The run halted with `DeliberationNeedsEvidence` as designed, not a service error or forced `enough`. Independent evaluation afterward reported 19 errors and 11 passing tests. The failed run intentionally has no final DeepSeek summary. A gate request for more evidence is not proof that the information was truly unavailable; the result is only that this configured workflow did not finish.

### Usage for the new runs

| Arm | DS prompt | DS cache-hit | DS completion | Jev input |
|---|---:|---:|---:|---:|
| Plain retry | 253,084 | 198,144 | 4,175 | 249,538 |
| Synthetic_v2 retry | 240,263 | 183,808 | 21,784 | 263,728 |

Both new runs returned zero native reasoning characters. Source fixture/evaluator hashes match their recorded startup hashes, and workspace specification/public tests are byte-identical to fixtures. Native-max usage remains in the earlier table: 126,183 completion tokens including 117,193 reasoning tokens.

### Interpretation

Plain nonthinking + Jev JIT is the best observed configuration here: complete verified artifact, substantially less elapsed time than native max despite more tool actions. Synthetic_v2's safe halt improves liveness behavior over the original endless loop, but **does not establish better programming quality**. Its advisory drafts did not prevent an invalid command or a broken patch.

Do not adopt this deliberation gate by default on this evidence. Preserve it as experimental. If iterated further, a needs-evidence event should be handled as a separate recovery design, without feeding speculative drafts into the tool router; that recovery was not part of this run.

Caveats: one programming task, one completed run per configuration, native measured earlier, provider aliases/cache/load can vary, and synthetic_v2 was halted before task completion. The measured times are not a controlled universal speed ratio. The experiment does not measure model-controlled tool selection; all arms use Jev JIT. Runtime defaults remain unchanged.

New evidence:
- `deliberation_results/plain-20260917-132142-90755f/`
- `deliberation_results/synthetic_v2-20260917-132233-77aaf4/`
- `plain-retry2-console.txt`, `synthetic-v2-retry-console.txt`

