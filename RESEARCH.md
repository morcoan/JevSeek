# Research notebook

### Why JevSeek decides one action at a time

[← JevSeek](README.md) · [Routing comparison](benchmarks/RESULTS.md) · [Deliberation study](benchmarks/DELIBERATION.md) · [Context validation](research/BACKEND_CONTEXT.md)

JevSeek's design came from a sequence of **local engineering experiments**, not a
large-scale leaderboard evaluation. We tested whether extra planning or
reasoning machinery helped a small tool-using coding agent—and kept the failures
in the record.

> **Bottom line:** for the work tested, selecting a tool from real feedback and
> generating its arguments directly was the most useful observed configuration.
> That is the reason for the current runtime, not proof that planning or reasoning
> is generally unnecessary.

## The research in four steps

| Stage | Question | Outcome |
| :-- | :-- | :-- |
| **01 · Routing inputs** | Should a generated plan influence Jev's decision? | It could bias a clear request toward the wrong tool. |
| **02 · Execution feedback** | Can a fixed tool schedule replace step-by-step routing? | The tested fixed schedules never implemented the task. |
| **03 · Argument generation** | Does extra deliberation improve the already-selected action? | Plain and native-max completed; the tested synthetic variants did not. |
| **04 · Runtime reliability** | Can the simpler loop preserve useful context and resume safely? | A separate production run passed the evaluator through repeated compaction. |

## 01 — Routing from intent, not an invented plan

**Setup.** Small probes compared raw requests against requests augmented with a
one-sentence DeepSeek plan. Jev chose among `read`, `write`, `edit` and `bash`.
These were routing pilots, **not two complete end-to-end agent implementations**.

- Both conditions selected the expected tool on the first **12 clear examples**.
- An injected wrong plan flipped a clear read request toward `write`.
- A helpful injected plan improved one ambiguous request, but it supplied intent
  that was not established by the user's original wording.

**Takeaway.** Fluency is not evidence. A proposed plan can introduce an assumption
before the agent has observed the workspace. The runtime therefore routes from
**user intent + completed actions + actual observations**, not generated plans.
Ambiguity can pause for clarification.

This does not establish perfect routing, or prove every planner is harmful.
[Historical pilot and its scope corrections →](research/ROUTING_PILOT.md)

## 02 — Just-in-time routing versus a frozen schedule

### The task

Implement a dependency-aware incremental build engine from an unfinished starter:

- deterministic graph traversal and dependency validation;
- content hashing and precise cache invalidation;
- missing/tampered output detection;
- failure recovery and atomic manifest updates.

The evaluator contained **30 tests authored before the runs**, outside the agent's
workspace. The untouched starter already passed **1/30**, an immutability check.
The suite was substantial, but not exhaustive.

[Task specification](benchmarks/build_engine/SPEC.md) · [Evaluator](benchmarks/build_engine/acceptance_suite.py) · [Shared runner](benchmarks/compare_routing.py)

### What changed between arms?

**JIT:** Jev chooses the next action after each real result, with a `done` decision.

**Frozen:** Jev estimates the action count and selects the entire linear schedule
before execution. A second frozen run clarified what counts as an action and how
hypothetical earlier actions should affect scheduling.

Both used the same starting files, tool adapters, argument model and evaluator.
This experiment used `deepseek/deepseek-chat`; it is **not the same model setup**
as the later Flash argument-generation study below.

| Configuration | Independent tests | Tool actions | Elapsed |
| :-- | --: | --: | --: |
| **JIT** | **30/30** | **12** | **23.72 s** |
| Frozen linear preplan | 1/30 | 100 | 141.38 s |
| Frozen, clarified scheduling prompt | 1/30 | 3 | 14.01 s |

### What actually happened?

JIT encountered implementation errors, inspected test feedback and selected
repairs/reruns. It eventually passed all tests. Its argument generator also made
an unsuccessful repair—the useful property was **recovery**, not flawless output.

The original frozen plan scheduled **100 reads**. The clarified variant scheduled
**three reads**. Neither changed the implementation, so both stayed at baseline.
The shorter failed run was not a faster solution.

**Decision:** keep execution feedback in the loop. This does **not** rule out
conditional plans, replanning, short planning horizons or better planning prompts;
those were not tested.

### A useful cache lesson

The unsuccessful 100-read arm had a **95.3% DeepSeek cache-hit fraction**, versus
**71.6%** for JIT. Yet it consumed far more total prompt tokens and did no useful
implementation work. High cache-hit percentage is not task success or low total
cost. Jev cache behavior was not measured, and no dollar-cost conclusion was made.

[Full controls, call counts, cache usage and interpretation →](benchmarks/RESULTS.md)

## 03 — Native reasoning versus synthetic deliberation

This study kept **Jev JIT routing in every arm**. It changed only how DeepSeek
produced arguments **after a tool had already been selected**.

| Mode | Mechanism |
| :-- | :-- |
| **Plain** | Non-thinking Flash directly generates the selected tool's arguments. |
| **Native max** | Flash's native thinking is enabled with maximum reasoning effort. |
| **Synthetic** | Non-thinking Flash drafts; a separate Jev gate decides whether to continue drafting or generate arguments. |
| **Synthetic v2** | A revised gate adds structured gap labels, repeated-draft detection and a missing-evidence halt. |

The task/evaluator remained the build engine. All arms used the `deepseek-flash`
API alias. That alias is not an immutable model checkpoint. Per-request output
ceilings were shared, **not total compute budgets**: synthetic modes could make
many extra requests.

### Completed and halted results

| Configuration | Tests at exit | Outcome | Actions | Elapsed |
| :-- | --: | :-- | --: | --: |
| Native max, earlier run | 30/30 | Completed | 8 | 503.25 s |
| **Plain, after service recovery** | **30/30** | **Completed** | **16** | **35.05 s** |
| Synthetic v2, after recovery | 11/30 | Needs-evidence halt | 8 | 114.43 s |

Plain initially produced incorrect invalidation behavior, then repaired it using
actual test feedback. Native max also encountered a rejected argument payload
before completing. Passing does not mean either run was error-free.

### Why the synthetic experiments were not adopted

The first synthetic configuration produced **46 drafts** but executed only three
reads. Its gate kept asking for more deliberation even when drafts said there was
no new evidence. A subsequent Jev HTTP503 ended the run. A contemporaneous plain
attempt also hit HTTP503 before starting; that was **not** evidence of poor coding
quality.

Synthetic v2 improved the failure behavior: repeated drafts or missing evidence
could halt rather than continue indefinitely. But its successful-service retry
still introduced a reference to undefined `_fingerprint_node` and stopped with
**11/30** tests passing. A safer halt is useful engineering, not proof of a better
implementation.

### Usage, without pretending it is a matched-cost contest

| Configuration | Reported DeepSeek completion tokens | Included native reasoning |
| :-- | --: | --: |
| Native max | 126,183 | 117,193 |
| Plain retry | 4,175 | 0 |
| Synthetic v2 retry | 21,784 | 0 |

These are successful-response completion totals, not total input/output billing.
Native ran earlier, only one completed run per successful configuration was
observed, and provider load/cache could differ. **Do not turn these timings into
a universal speedup claim or treat the halted run as a completed-task cost win.**

**Decision:** plain non-thinking arguments in production; synthetic deliberation
remains experimental. No experiment here isolates Jev's contribution against a
DeepSeek-only tool router.

[Full chronology, outage accounting, usage and gate design →](benchmarks/DELIBERATION.md)

## 04 — Turning the result into a reliable runtime

The research runners were not simply renamed into a product. The production loop
adds persistent sessions, validated native calls, factual compaction, cancellation,
source-read retention and explicit handling of uncertain tool effects.

Some of the most useful findings were ordinary engineering failures:

| Failure observed | Runtime response |
| :-- | :-- |
| Missing workspace facts made a clear task look uncertain | Include a bounded factual starting inventory. |
| Earlier failures polluted a new request | Separate active-request execution from older requests. |
| Archived source led to repeated inspection | Retain bounded recent source snapshots; invalidate them after changes. |
| Free-text JSON came back wrapped or malformed | Force one native function call and validate before execution. |
| A high confidence floor caused unnecessary pauses | Use a configurable lower floor; explicit `ask` still pauses. Confidence is not calibrated correctness. |
| Interrupted tools might already have effects | Persist start/finish boundaries and require review, not automatic replay. |

A separate production build-engine validation passed **30/30** independent tests
with **10 actions** and **3 automatic compactions**. Fixture hashes were checked
unchanged. Offline compaction and reopening the completed session did not replay
model/tool calls. Additional checks covered follow-up requests and read-only MCP
integration.

This is **integration evidence**, not another controlled performance comparison.
[Detailed production findings and boundaries →](research/BACKEND_CONTEXT.md)

## What the evidence does—and does not—support

**Supported as a project decision**

- Use actual outcomes to choose the next action.
- Keep speculative drafts separate from factual routing state.
- Validate arguments and judge work with independent tests, not a final summary.
- Prefer the simpler successful configuration observed on this workload.
- Preserve failed/interrupted attempts rather than hiding them in the final story.

**Not established**

- General superiority over other coding agents or planning architectures.
- Equal general coding quality between plain and native reasoning.
- A causal explanation that Jev is responsible for the successful results.
- A universally optimal confidence threshold, cost saving or speedup.
- Safety from untrusted code, prompt injection or arbitrary tool side effects.

Useful future work would include a broader task set, repeated runs, matched
budgets, a Jev-vs-model-router ablation, and conditional/replanning baselines.
**Those experiments have not been run.**

## Reproduce the experiments

Install the core dependencies and configure your own environment keys as described
in the [source guide](docs/USAGE.md). Run from the repository root:

```sh
# Offline regression tests — no provider calls
python -m unittest discover -s benchmarks -p test_deliberation.py -v

# Billable live experiments
python benchmarks/compare_routing.py jit
python benchmarks/compare_routing.py pre
python benchmarks/compare_routing.py pre_explicit

python benchmarks/compare_deliberation.py plain
python benchmarks/compare_deliberation.py native
python benchmarks/compare_deliberation.py synthetic
python benchmarks/compare_deliberation.py synthetic_v2
```

> **Costs and limits:** live runs spend API credits. These experimental runners
> have no arbitrary tool-turn/deliberation-round cap; stalled runs can continue
> billing. Interrupt manually if necessary. An interruption is not a completed
> success. The native-max run above alone took over eight minutes.

New runs write timestamped results/workspaces under ignored benchmark directories.
Keep those private: traces contain prompts, generated code and tool output.
Public source includes the runners, specification and evaluator—not historical
personal sessions or the archived original pilot scripts. Reproduction may yield
different results as API aliases and provider behavior change.
