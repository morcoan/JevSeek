# Dynamic questions as agent scaffolding

**Research only. No JevSeek runtime change.** The question is whether a generator can decide what matters now, outsource narrow judgments to Jev, and improve actual action outcomes or total cost/latency. This is neither token-decoding intervention nor another plan-selection study.

See [results](RESULTS.md), [initial frozen protocol](PROTOCOL.md), [exploratory follow-up protocol](FOLLOWUP_PROTOCOL.md), [initial aggregates](summary.json) and [follow-up aggregates](followup_summary.json).

## What was measured

1. **Compile once, execute twice:** a generated declarative policy asked questions, chose a file read, then selected a replacement against the new evidence. DeepSeek and Jev ran the same generated policy. The initial compiler/DSL failed badly; those results are retained, not silently discarded.
2. **Isolate the proposed scaffolding:** on the same actual read evidence, generate task-specific questions, answer them with DeepSeek or Jev, and let the generator choose the replacement. A questions-without-answers arm distinguishes the value of question generation from the value of Jev's answers.

16 hand-authored Python repair-selection tasks, 71 hidden assertions. Actual prewritten replacement functions are executed and tested; provider-generated code is never executed. This is a **closed-world patch-selection microbenchmark**, not unrestricted coding. No small/1B generator, repeated long-running program, novel repository task, arbitrary tool use, or autonomous graph rewriting is validated.

## One actual cycle: obsolete login completion

This example occurred in the follow-up, not an invented success story.

1. Goal: overlapping login attempts sometimes display an obsolete completion.
2. Visible bug: `return x[0][-1][1] if x[0] else None` returns the last completion regardless of attempt generation.
3. The original direct arm selected `attempt_lifecycle.md`. Its actual observation specified: select events matching the current generation, preserve arrival order, use the last match, and do not skip a failed `None` result. That exact observation was shared with all follow-up arms.
4. The generator produced four questions. Three useful distinctions were: does the current code omit generation filtering; does last mean arrival order rather than maximum generation; must a last matching `None` result be preserved?
5. Both Jev and DeepSeek answered those three **yes**. Both answered **unknown** to the fourth question about an empty-input guarantee.
6. The generator selected and the harness applied this owned candidate:

   ```python
   def solve(x):
       return next((v for g, v in reversed(x[0]) if g == x[1]), None)
   ```

7. Five hidden cases passed, including stale completion after a newer attempt, no matching generation, last matching result being `None`, multiple matching arrivals and empty input.

**Crucial control:** direct and questions-only also selected this patch and passed. This demonstrates a working loop, not a gain. The fourth generated question even overlooked the original function's existing empty-list guard in its purpose text—question generation itself can introduce errors. Raw evidence must remain visible to the chooser.

## Concrete question schema

The measured follow-up uses this intentionally small structure (example abridged from an actual generated question):

```json
{
  "id": "q3",
  "question": "Can None be the correct result of the last eligible event, rather than something to skip?",
  "purpose": "Distinguish preserving the last matching result from skipping None and returning an older result.",
  "yes": "The observed contract says failed results may be None and must not be skipped.",
  "no": "The observed contract requires skipping None results."
}
```

The evaluator returns `yes | no | unknown`. Unknown is a real outcome, not a no or a low-confidence yes. All questions at that checkpoint see the same raw state and are evaluated independently in one provider request. No unsupported multiplication of correlated marginal scores; no confidence-as-correctness threshold.

For a **future** reusable agent implementation, the host should add non-model authority metadata:

```json
{
  "program_version": 1,
  "question_id": "q3",
  "evidence_versions": {
    "attempt_lifecycle.md": "content-sha256",
    "implementation.py": "content-sha256"
  },
  "phase": "patch_review",
  "depends_on": [],
  "on_unknown": "acquire_missing_evidence",
  "invalidated_by": ["watched_file_changed", "goal_changed"],
  "max_evaluations": 3
}
```

This wrapper is a design proposal, **not a shipped feature or measured improvement**. Expiry should be checked against actual file/state versions, not left as a prose request to the LLM. Dependencies define scheduling, not statistical independence. A compiler must validate IDs, effects, acyclicity and budgets before activation. Tool permissions and actual tests remain outside the generated policy's authority.

## What the literature does—and does not—establish

- [TypeSafe's introduction](https://typesafe.ai/blog/introducing-system-one-models-and-jev): describes narrow independent probabilistic questions composed in code, parallel sampling and workflow advantages. Its stated workflow reference is the **average predictions of external large models**, not independent coding correctness. Workflows were made by its capabilities team. It does **not** demonstrate an LLM inventing useful workflows on demand. Schema/type guarantees do not imply semantically correct judgments.
- [PAL, ICML 2023](https://proceedings.mlr.press/v202/gao23f.html): generates programs and offloads their execution to an interpreter. Relevant precedent for generating an executable intermediate representation, but its arithmetic/symbolic runtime is not a fallible semantic classifier.
- [ViperGPT, ICCV 2023](https://viper.cs.columbia.edu/): generates programs that compose vision/language modules. This is particularly close to "generator designs the program; learned modules execute fuzzy parts." Its visual-task results are not evidence for Jev or coding agents.
- [LLMCompiler, ICML 2024](https://github.com/SqueezeAILab/LLMCompiler): constructs and schedules dependent/parallel function calls. Relevant to graph scheduling, not proof of dynamically generated semantic question quality.

Consequently, "LLM invents a program and learned modules execute parts" is **not itself a new architecture**. The worthwhile research question is whether Jev-specific execution, evidence-aware lifetimes and limited recompilation produce a better quality/cost frontier in this setting. Novelty would require a wider prior-art review and a specific demonstrated mechanism, not a metaphor.

## Reproduce

Requires the existing project provider dependencies and local credentials. These commands are **billable and opt-in**; results are private under `.local/research/dynamic-questions/`.

```powershell
# Offline owned-fixture checks only
python research/dynamic_questions/experiment.py

# Original one-shot graph study: at most112 requests
python research/dynamic_questions/experiment.py --run
python research/dynamic_questions/analyze.py PATH_TO_INITIAL_RUN

# Exploratory shared-evidence follow-up: at most96 further requests
python research/dynamic_questions/followup.py PATH_TO_INITIAL_RUN --run
python research/dynamic_questions/analyze_followup.py PATH_TO_FOLLOWUP PATH_TO_INITIAL_RUN
```

Provider credentials are loaded in memory using the existing research provider helper; no keys appear in manifests or results. No automatic retries, no test-feedback regeneration, no cherry-picked best run. The shared helper is in `research/decoding_control/providers.py`; research directories are currently local, not yet published as a complete source package.
