# Can a separate decision model improve a generator?

**Investigation: 2026-09-18. Model-agnostic architecture; DeepSeek first.**
No application policy, EXE, benchmark VM or running Bonsai server was changed.
This folder contains a literature investigation and a separate, bounded pilot,
not a new default for JevSeek. See [protocol](PROTOCOL.md) and [measured results](RESULTS.md).

## Bottom line

The research supports **recovering some capability through better selection**.
It does not establish that any structured decision API can reliably verify hard
reasoning, or that this costs roughly the same as direct generation. Those are
empirical hypotheses. Token guidance, plan selection, verification, retrieval,
and distillation are different mechanisms and should not be conflated.

The portable unit is **a consequential text-level decision**, not a tokenizer token:

```
task + available evidence
  -> generator proposes a few short candidate approaches/actions
  -> selector chooses one (or abstains)
  -> generator produces one final answer
  -> independent outcome measurement
```

The generator and selector have separate interfaces. No shared tokenizer, weights,
Bonsai runtime or logits required. The pilot uses DeepSeek Flash with thinking off
and Jev 1.13.0. An OpenAI-compatible JSON generator can be substituted; other API
families need a thin transport adapter. Portability of this interface is NOT proof
that the quality gains transfer across models.

## 1. What the cited research actually demonstrates

| Work | Supported conclusion | Important boundary |
|---|---|---|
| [FUDGE, Yang & Klein, 2021](https://arxiv.org/abs/2104.05218) | A predictor trained on unfinished sequences can reweight a frozen generator's next-token probabilities toward an attribute. | Poetry, topic control and translation formality, not general reasoning. Requires probability access and repeated decoding control. Training used 10 million generated examples; not an untrained generic judge. |
| [IPA, Lu et al., 2023](https://arxiv.org/abs/2305.15065) | A trained policy adapter can steer a frozen model through a product of next-token distributions. | Five task settings including toxicity, lexical constraints and grounded dialogue. The GPT-2-over-GPT-3 statement is task-specific. Requires compatible output vocabulary, adapter training and probability access. |
| [Reward-Guided Speculative Decoding, 2025](https://arxiv.org/abs/2501.19324) | A process reward model gates small-model steps and invokes a stronger generator when needed; reported up to 4.4x fewer FLOPs than target-only generation. | Their Table 2 includes 1.5B/7B verifiers and 7B/72B targets. Not Jev, not an ordinary HTTP chat wrapper, not a 4.4x memory or wall-clock guarantee. Some fixed-threshold settings regress. |
| [Speculative Decoding, Leviathan et al.](https://arxiv.org/abs/2211.17192) | Exact speculative sampling can accelerate target-model sampling while preserving its distribution under the algorithm's assumptions. | Replacing target-distribution verification with a semantic judge changes the algorithm and loses that guarantee. Preserving a distribution does not make it more correct. |
| [Distilling Step-by-Step, Hsieh et al., 2023](https://arxiv.org/abs/2305.02301) | Teacher rationales plus labels can train compact task-specific models with less data. | Four NLP benchmarks. The 770M-versus-540B comparison is a trained specialist against a prompted generalist, not universal dominance or evidence for blindly learning Jev preferences. |

FUDGE's key factorization is
`P(next_token | prefix, attribute) proportional to P(attribute | extended_prefix) * P(next_token | prefix)`.
The first term predicts a **future outcome**, not whether the prefix merely sounds
good. That distinction matters: rating an unfinished proof as plausible is not the
same as estimating whether its eventual completion will be correct.

## 2. Additional evidence and counterevidence

- [Training Verifiers to Solve Math Word Problems, Cobbe et al., 2021](https://arxiv.org/abs/2110.14168): direct evidence that learned verification can improve selection among generated math solutions. It uses trained verifiers and multiple completed candidates, not a free single-answer improvement.
- [Let's Verify Step by Step, Lightman et al., 2023](https://arxiv.org/abs/2305.20050): process supervision outperformed outcome supervision in their MATH setting. The released PRM800K contains 800,000 step-level human labels. A generic off-the-shelf selector does not inherit that training evidence.
- [Scaling LLM Test-Time Compute Optimally, Snell et al., 2024](https://arxiv.org/abs/2408.03314): allocation depends strongly on difficulty; smaller models can outperform larger ones in particular FLOPs-matched settings where the small model already has nontrivial success. This supports selective intervention, not one universal recipe.
- [Large Language Models Cannot Self-Correct Reasoning Yet, Huang et al.](https://arxiv.org/abs/2310.01798): intrinsic correction without external feedback sometimes worsens reasoning. This is evidence about evaluated models/settings, not an eternal impossibility theorem. A second model is not automatically an independent source of truth.
- [Judging LLM-as-a-Judge, Zheng et al.](https://arxiv.org/abs/2306.05685): position, verbosity and self-enhancement biases matter. Agreement with human preference is not proof of executable correctness.
- [Weaver: Shrinking the Generation-Verification Gap with Weak Verifiers](https://arxiv.org/abs/2506.18203): combines imperfect verifiers, and distills an ensemble into a 400M cross-encoder. This is closer to the eventual lightweight-verifier idea than rationale distillation alone. Its sampling, ensemble and task-specific training costs cannot be omitted. The abstract and body use different retention figures/wording; we do not treat one headline percentage as a universal guarantee.
- [Step-DPO](https://arxiv.org/abs/2406.18629): step-level correct/incorrect preference pairs can improve trained reasoning models. This motivates keeping verified failures as well as successes, not training on a judge's agreement alone.

### Relevant negative evidence already in this repository

[Earlier deliberation experiments](../../benchmarks/DELIBERATION.md) found that
extra drafts and a Jev readiness gate could stall or approve work that later failed.
Plain non-thinking generation with the existing router performed better on that
one task. All those arms used Jev routing, so they did not isolate Jev's contribution.
We do not repeat that unbounded draft loop here. The new pilot uses one selection,
a same-candidate DeepSeek selector, and a genuinely Jev-free direct baseline.

## 3. What Jev and DeepSeek actually expose

Primary API documentation checked during this investigation:

- [DeepSeek chat API](https://api-docs.deepseek.com/api/create-chat-completion): model/thinking controls, JSON output, forced function calls, and returned `logprobs` with up to twenty `top_logprobs`. Returned probabilities are observations, not a callback for modifying the server's next-token sampling. Streaming text is not an editable decoding loop. Repeated one-token requests with prefix completion would be a separate high-overhead experiment, not a faithful plug-in implementation of FUDGE.
- [TypeSafe introduction](https://docs.typesafe.ai/): Choice, Score and Noul are typed decisions; the vendor recommends narrow judgments and decomposition for questions requiring extended reasoning.
- [TypeSafe confidence](https://docs.typesafe.ai/confidence.md): confidence is derived from the shape of option probabilities. It is not, by itself, the probability that selected SQL passes tests. Several equally good choices may yield low confidence; a confidently chosen flawed approach can still fail.

Thus Jev is technically suitable for **coarse, infrequent choices**. Its mathematical
verification reliability, calibration on a new task, computational footprint and
advantage over DeepSeek choosing for itself still require measurement. API price
is not parameter count, FLOPs, RAM or energy consumption.

## 4. What would make the hypothesis true?

For a frozen pool of complete candidate answers:

- `coverage = P(at least one candidate is correct)`.
- `selector_quality = P(chosen answer correct | coverage)`.
- If the selector must return a pool member, final accuracy is their product.

More samples can improve coverage while making false-positive selection worse.
For short plans, this clean decomposition is incomplete: an additional generator
must IMPLEMENT the plan. Correct-looking plans can produce invalid final code.
Our retrospective oracle therefore measures coverage of **observed plan-conditioned
completions**, not the intrinsic correctness of those plans.

Against a baseline, record both **rescues** (wrong becomes right) and
**regressions** (right becomes wrong). Net improvement is `(rescues-regressions)/N`,
not the number of times the judge changed its mind or reported high confidence.

For latency, an always-on branch approximately costs:

`proposal_time + selector_time + selected_answer_time`.

Even a 0.2-second selector is expensive if proposal generation and another API
round trip dominate. To claim speed improvement over a real workflow, saved
regeneration/tool time must exceed all added overhead. Report time-to-correct
outcome as well as latency of a single attempt; count failed attempts and abstentions.
For interventions chosen only on some tasks, evaluate that gating rule separately
and calibrate it on held-out data, not on an arbitrary confidence threshold.

## 5. Best next design, conditional on evidence

1. Start with one short, explicit decision at a known failure-prone point. Examples:
   choose a join/filter order, choose a concrete patch, or identify the one missing
   requirement. Do not ask an abstract judge whether an entire speculative plan
   is ready forever.
2. Supply actual evidence and requirements. Use deterministic validation for syntax,
   schemas, arithmetic and permissions when available; do not pay Jev to replace
   an exact check. Hidden evaluation tests must stay hidden.
3. Keep plans provisional and separate from execution history. Never treat an
   approved proposal as evidence that work ran or succeeded.
4. Run paired generator-only, same-pool self-selection and Jev-selection controls.
   Add a DeepSeek-only equal-budget deliberation arm before making an efficiency
   claim. Evaluate candidate order, abstention, correct-to-wrong changes, and
   distribution shifts. Use independently chosen tasks and multiple seeds.
5. Only after a reliable gain, collect independently verified choices and failures
   for a local verifier or trainable generator. Fine-tuning a hosted closed model
   is a separate provider capability, not something this interface grants.
6. Reproduce on another generator before claiming effectiveness is model-agnostic.
   No automatic stronger-model fallback in the present pilot.

## Reproduction and status

Use the project's existing Python dependencies. Default invocation makes no calls:

```sh
python research/decision_selection/experiment.py
# Opt-in, paid DeepSeek and Jev inference; at most 84 requests, no retries:
python research/decision_selection/experiment.py --live
```

Reads existing credentials privately; no keys exported or printed. Results go under
the ignored `.local/research/decision-selection/` directory. The manifest hashes
source and protocol. No tests, prompt changes or generation retries are selected
after seeing results in the recorded pilot. Twenty databases per task are checks
of that one generated program, not twenty independent inference examples.

Alternative OpenAI-compatible generators can use `--model`, `--base-url`,
`--generator-key-env` and `--options-json '{}'` (to omit DeepSeek-specific controls).
Those flags provide transport portability only; that backend must support JSON
mode and the requested sampling options. Only DeepSeek was measured here.

This investigation is local and has not been pushed or included in a release.
