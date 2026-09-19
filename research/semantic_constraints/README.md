# Jev as a semantic constraint coprocessor

**A working, domain-limited augmentation—not a claim of general intelligence.**

On24fresh synthetic placement problems with withheld host phrasing, Jev's semantic relation plus the same exact solver produced22fully valid minimum-cost assignments. Direct nonthinking Qwen3-1.7B produced0; Qwen-derived relations plus the solver produced0; DeepSeek-derived batched relations plus the solver produced10. Every assignment was checked against hidden Boolean facts and an independently enumerated optimum, not against another model's opinion.

See [results and limitations](RESULTS.md), [frozen protocol](PROTOCOL.md), [confirmation aggregates](confirmation_summary.json), and [native tool replay protocol](INTEGRATION_PROTOCOL.md).

## The useful boundary

```text
LLM receives a task with records and requirements
                 |
                 v
      semantic-assignment tool
                 |
        Jev: independent judgments
        “Does host H satisfy requirement R?”
                 |
                 v
      explicit eligibility relation
                 |
      exact constrained optimizer
                 |
                 v
      proposed assignment -> LLM
```

**Jev interprets meaning; code enforces global consistency.** The weak LLM does not have to invent a valid algorithm, maintain30interacting predicates, or implement correct advice in unconstrained SQL.

This differs from asking Jev to approve a draft. Its answers are executable constraints consumed by the reasoning engine. It also differs from expecting a solver to understand prose: the solver-without-semantics control failed all24confirmation tasks.

This is a form of neuro-symbolic/tool-augmented reasoning. Neither that broad concept nor modular learned predicates are new; [PAL](https://proceedings.mlr.press/v202/gao23f.html) and [ViperGPT](https://viper.cs.columbia.edu/) are relevant precedents. [TypeSafe's workflow article](https://typesafe.ai/blog/introducing-system-one-models-and-jev) likewise motivates narrow independent decisions composed in code. The contribution here is a measured local experiment and working tool connection, **not a novelty claim**.

## What the test actually contains

- 6 hosts, 5 services, at most 1 service per host.
- 6 binary capabilities described in natural language: persistent storage, public-internet egress, usable GPU, native architecture, OS, and public listener exposure.
- Requirements combine AND, inclusive OR, NOT and implication.
- Select a truly feasible assignment minimizing total host cost.
- Jev evaluates 30 host/service pairs in one request.
- A deterministic search checks all 720 possible assignments under the predicted relation.
- An independent hidden-fact interpreter and cost enumeration score the chosen plan.

These are synthetic, small, controlled-language problems. A hand-built parser for this tiny known grammar could solve them perfectly. We did not prove superiority to such a parser, arbitrary prose understanding, general coding ability, or a guarantee of correct real deployments. The point is that a learned semantic interface can supply usable constraints without exposing the latent test facts.

## Actual LLM tool connection

`integration.py` used the real Qwen native tool-call interface across all24confirmation tasks. The model called `semantic_assignment`24/24times, consumed its result, and returned the identical assignment24/24times.22passed hidden feasibility+optimality, exactly preserving the two Jev failures.

**This was cached replay of the already-recorded real Jev labels, not24new independent quality trials.** It used48new local Qwen calls and zero new remote calls. The host validated the request ID and executed the actual solver; no model-generated Python, shell command or physical deployment ran. The system instructed the model to use the planning tool, so this is not an autonomous tool-discovery benchmark.

## Minimal semantic interface

Input records remain raw evidence; no latent Boolean feature dictionary is supplied:

```json
{
  "host": "Files survive restart. Public-internet egress is blocked. ...",
  "requirement": "Data must survive restart AND outbound internet must be blocked."
}
```

Typed answer: `eligible | ineligible | unknown`. Unknown becomes an unavailable edge. No confidence threshold, probability multiplication, or assumption that a model score is a proof.

The solver receives only the predicted relation, IDs and costs. It can prove optimality **relative to that relation**, not that the model understood every sentence correctly. The remaining semantic errors caused two invalid confirmation plans; a real agent must not automatically deploy from this alone.

## Run locally

Research-only, Windows-tested. Uses the existing project Python/provider dependencies and the verified llama.cpp CUDA distribution already cached at `.jevseek/bonsai-validation/bonsai/runtime-cuda/llama-server.exe`. That runtime must exist; this is not a new portable app release. The helper downloads the pinned official Qwen3-1.7B Q8 model (~1.8GB), verifies SHA-256, and starts only its own authenticated loopback server. It never changes the selected app model or starts the stopped Linux VM.

```powershell
# Offline32case /960pair fixture checks; no providers or model server
python research/semantic_constraints/experiment.py

# Opt-in, billable remote research plus local inference
python research/semantic_constraints/experiment.py --phase development --run
python research/semantic_constraints/analyze.py PATH_TO_DEVELOPMENT

# Only runs if the frozen development gate passed
python research/semantic_constraints/experiment.py --phase confirmation --development PATH_TO_DEVELOPMENT --run
python research/semantic_constraints/analyze.py PATH_TO_CONFIRMATION

# Opt-in local native-tool replay, no new Jev/DeepSeek calls
python research/semantic_constraints/integration.py PATH_TO_CONFIRMATION --run
```

Results/calls/fixtures stay in ignored `.local/research/semantic-constraints/`. Model credentials load privately from existing local configuration; never go into model-server environment or artifacts. All research-owned servers close after runs. No application code or public GitHub content changed.

## Next research boundary

A coding application would need a typed constraint domain whose semantics can be checked: dependency compatibility, requirement/test coverage, valid API combinations, or action preconditions. Those are **future hypotheses**, not results of this placement study. The lesson is to have Jev supply semantic relations to reliable execution, rather than ask a weak generator to turn “this looks wrong” into a correct implementation.
