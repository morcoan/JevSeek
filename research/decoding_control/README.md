# Jev inside decoding: what works technically, and what did not improve quality

**2026-09-18 — DeepSeek-first, model-agnostic control interface.**
This investigates intervention in the actual autoregressive output, not plans,
tool routing or review of completed answers. No application, EXE, VM or benchmark
sweep was changed. Sources and aggregates remain local/unpublished.

## Conclusion

**The mechanism is feasible; a reliable Jev-specific performance gain is NOT yet
established.** Generic selection of early prefixes made performance worse. A
narrower, exploratory constraint-recognition signal rescued one cached trajectory
when given more lookahead, but a simple no-model heuristic matched it.

The defensible research direction is **constraint-aware decoding**: maintain
explicit obligations while generating, use an external decision model to recognize
observable semantic commitments at useful boundaries, and preserve the generator
when the signal is weak. It is not 'ask Jev which arbitrary next token is smart.'

See [frozen live protocol](PROTOCOL.md), [results](RESULTS.md),
[separately frozen exploratory protocol](GAP_PROTOCOL.md), and
[machine-readable aggregate](summary.json).

## 1. The foundational opportunity

A generator models `P(next token | task, prefix)`. This is not identical to
`P(eventual task success | task, prefix + next token)`. The latter is a value
function depending on both the objective AND how the generator will continue.
An external signal can steer the former, for example:

`q(token | prefix) proportional to p(token | prefix) * exp(lambda * V(prefix + token))`.

Changing the committed token changes subsequent context and computation. It does
not directly edit weights or hidden activations. A separate text-scoring API does
not gain access to private hidden reasoning by reading emitted text.

Three distinct ways to implement the signal:

1. **Future-value prediction:** estimate eventual reward from unfinished prefixes.
   Powerful in principle; hard because the critic must predict missing future work.
   Jev was not shown to be trained/calibrated for this role.
2. **Constraint/progress recognition:** identify whether a visible semantic
   requirement is satisfied, still open, or contradicted. More local/observable;
   being unresolved is NOT an error. Can bias the next continuation without
   claiming to know the entire future answer.
3. **Learned decoder adapter:** train a compact local value/classifier module
   from independently checked rollouts and use it to adjust logits. This can avoid
   a network round trip per token, but training and rollout costs are real.
   Jev might supply auxiliary semantic labels; its preferences are not gold labels.

A controller can be model-agnostic as an interface while needing new calibration
for each generator. A continuation a strong generator can repair may be fatal to
a weaker one. Text-prefix APIs also differ; exact token-ID/KV-cache control is not
part of a universal chat API.

## 2. Closest primary research

| Work | Mechanism relevant here | Limits for using Jev |
|---|---|---|
| [Controlled Decoding, ICML 2024](https://proceedings.mlr.press/v235/mudgal24a.html) | A TRAINED prefix value scorer guides a frozen generator tokenwise or blockwise. Formal connection to a KL-regularized objective; limited empirical transfer to another base model. | Its mathematical result assumes an appropriate value function. Replacing it with arbitrary off-the-shelf Jev scores does not inherit the guarantee. |
| [FUDGE](https://arxiv.org/abs/2104.05218) | Learns a predictor of a future attribute from partial text and reweights next-token probabilities. | Task-specific attribute training, not proof of general reasoning improvement. |
| [CARDS](https://openreview.net/pdf?id=UAA2nWUtVl) | Generates and accepts/rejects short semantic segments using reward scores, with uncertainty-based boundaries. | The paper explicitly describes prefix reward approximating future value as an empirical observation, not a mathematical fact. Higher reward/preference is not automatically factual or executable correctness. |
| [DIRECTOR, AACL 2022](https://aclanthology.org/2022.aacl-main.39/) | A shared generator and per-token classifier head can steer away from repetition, contradictions and undesirable content with low decoding overhead. | Needs supervision and shared-model training. The paper's frozen-core variant was weaker; a cheap head on frozen features is not guaranteed sufficient. Remote Jev cannot simply be plugged into this head. |
| [Tuning Language Models by Proxy](https://arxiv.org/html/2401.08565v4) | Adds a small tuned-minus-untuned model's logit difference to a larger model; also studies a black-box/top-five-logprob case. | The correction is a TRAINED expert/anti-expert difference, not a generic classifier confidence. Vocabulary/transport alignment and multiple model computations matter. Reported task-specific gap closure does not transfer automatically to Jev. |

These establish that an external learned signal can improve a frozen model's
behavior during decoding. They do not establish that Jev is already the correct
signal, that a remote call per token is fast, or that no additional computation is
needed. The [earlier plan pilot](../decision_selection/README.md) tested a different
mechanism and is not evidence against all decoder-control methods.

## 3. Actual DeepSeek capability verified

[Official DeepSeek prefix API](https://api-docs.deepseek.com/guides/chat_prefix_completion)
allows a final assistant message with `prefix: true` on the beta endpoint.
Three real non-thinking DeepSeek calls verified:

- stopping an unfinished raw SQL response at a twelve-token cap;
- receiving top-five token logprobs whose bytes reconstruct that response;
- resuming the generated prefix, and separately a forced incomplete prefix;
- correct resulting queries on a separate trivial capability fixture.

This establishes text continuation, not a server-side sampler callback. It may
re-tokenize text and does not expose native branchable KV snapshots. We did NOT
implement exact token-level logit reweighting or access internal reasoning.

## 4. What we actually tested inside generation

```
Generate first 12 actual SQL tokens
    -> fork three 24-token continuations from that same assistant prefix
    -> Jev chooses BEFORE any remainder exists
    -> resume chosen text verbatim to finish the query
    -> independent evaluator checks the eventual result
```

The candidates were newly generated SQL text, never proposed plans or hand-made
correct answers. All36 short candidates were unfinished. A same-pool DeepSeek
selector and unsteered paused continuation control isolate selection and transport
from simply using a different prompt. Completing all branches was offline oracle
measurement, not the proposed deployed cost. All choices preceded their suffixes;
exact prefix retention and source hashes were verified afterward.

Generic Jev selection passed **6/12**, versus **9/12** for both direct DeepSeek and
first paused branch. See RESULTS.md for failures, costs and duplicate-prefix
confounding. This does NOT justify deploying an always-on prefix judge.

## 5. The specific gap and the diagnostic

A recurring task requirement was to output only people that actually exist in a
`people` table. Checking `person_id IS NOT NULL` is insufficient because an ID can
be non-NULL but orphaned. This is **constraint preservation**, not missing world
knowledge or an inability to generate fluent code.

One real continuation fork was:

```
committed: WITH days AS (SELECT person_id, day FROM orders
branch A:  WHERE person_id IS NOT NULL ...
branch B:  WHERE person_id IN (SELECT id FROM people) ...
```

Jev selected B in the main pilot, and its eventual query passed while A's sampled
completion failed. That is a concrete example of steering unfinished generation
in a useful direction. But Jev missed an analogous constraint in another task and
introduced other regressions, so it is NOT a reliable general capability result.

In the post-hoc diagnostic, we narrowed the question to 'does this visible prefix
already establish the actual-person domain?' rather than asking for whole-answer
quality. We kept an unresolved obligation distinct from an irreversible error and
retained the first branch unless a score difference was substantial. At a longer
lookahead horizon it changed one cached selection, taking **9/12 to10/12** with no
regressions. **A literal word-matching baseline also got10/12.** Therefore:

- there is a plausible gap a constraint-aware decoder can address;
- more informative local context matters;
- this is NOT an independent live performance improvement or unique Jev advantage;
- if a deterministic check handles a constraint, use it instead of a model.

## 6. A design worth testing next—not a validated feature

Use Jev only where recognizing a requirement in arbitrary text genuinely needs
semantic interpretation, e.g. evidence attribution, preserving a negation across
paraphrase, or entity/role consistency. Those examples are hypotheses; this study
did not measure them.

An improved controller would:

1. Keep an explicit small constraint state: **satisfied / open / contradicted**.
   Do not conflate 'not shown yet' with 'cannot finish correctly.'
2. Wait for a meaningful, distinguishable semantic fork. Skip identical candidate
   prefixes and reuse common KV/prefix work where the backend really supports it.
3. Evaluate specific obligations from actual available evidence, not generic
   confidence in an unfinished answer. Do not hardcode 'NULL means valid' or other
   surface shortcuts as universal semantic proofs.
4. Apply a bounded bias toward a promising continuation, retaining the base model
   if uncertain. Reserve stopping for an actual unresolvable condition—not merely
   several equally acceptable next tokens. Roll back only uncommitted text.
5. Measure complete-task correctness, regressions, total generation/input processing
   and latency against an uninterrupted model AND matched paused/budget controls.
   Validate on new task families, including natural-language paraphrases where a
   literal rule would fail. Do not optimize thresholds on this pilot.
6. If the semantic signal proves reliable, investigate learning a local prefix
   scorer from independent outcome labels plus Jev annotations. General reasoning
   value requires future-outcome supervision, not only local preference scores.

This is more defensible than trying to make Jev a universal second brain. The
present evidence supports doing further targeted research, NOT shipping a quality
or speed claim. No training or extra follow-up runs are automatically scheduled.

## Reproduction

Uses existing project dependencies (`openai`, `typesafe-sdk`, `python-dotenv`) and
Python's SQLite. Provider keys are read privately from existing environment/.env
or Windows credential store; never exported or placed in prompts. Commands without
`--run` make no inference calls. The paid bounds are explicit:

```sh
python research/decoding_control/probe.py --run
# At most108 DeepSeek +12 Jev calls; no retries:
python research/decoding_control/experiment.py --run
# Post-hoc diagnostic, at most24 Jev calls, NO new generation:
python research/decoding_control/gap_diagnostic.py PRIVATE_PILOT_DIR --run
# Local-only reproduction of recorded metrics:
python research/decoding_control/analyze.py PRIVATE_PILOT_DIR PRIVATE_GAP_DIR
```

The algorithm accepts a `generate(system, task, prefix, limit, temperature, ...)`
interface, not Bonsai-specific machinery. Only DeepSeek's adapter was exercised;
another generator requires its own validated prefix-continuation transport.
Raw records stay in ignored `.local/research/decoding-control/`. No app policy,
source release, GitHub push, model server or stopped benchmark was changed.
