# Routing pilot: intent versus a generated plan

[← Research overview](../RESEARCH.md)

This early, small pilot asked whether a one-sentence DeepSeek plan improved Jev's
choice among `read`, `write`, `edit` and `bash` compared with the user's request
alone. It predates the production multi-turn backend.

## Observations

| Probe | With a plan | Without a plan |
| :-- | :-- | :-- |
| Six basic requests | 6/6 expected tool choices | 6/6 |
| Six adversarial requests | 6/6 expected tool choices | 6/6 |
| Clear request plus an injected wrong plan | One read request flipped to `write` | Expected choice retained |
| Ambiguous request plus a helpful plan | Followed the intended interpretation supplied by the plan | Did not recover that interpretation |

The helpful-plan case does not show that the agent inferred the user's intent:
the injected plan supplied information not established in the original request.
Similarly, 12/12 clear examples is not evidence of general routing perfection.

These pilots did **not** execute both conditions as matched full agent loops.
Their scope is tool-choice sensitivity, not end-to-end implementation quality or
cost. Historical scripts (`jev_test.py`, `jev_test2.py`, `jev_test3.py`) and raw
outputs are preserved privately rather than included in the public source.

## Project decision

Do not insert a model-generated plan into the tool router's factual state. On this
small sample it added no gain on the clear examples and introduced an avoidable
source of incorrect assumptions. That is a design choice for JevSeek, not a proof
that planning is generally harmful.

The later runtime goes beyond raw input alone: it includes **user intent,
completed tool arguments and actual observations**. Those are execution facts,
not a proposed plan. An explicit `ask` decision pauses for clarification; numerical
confidence is not a correctness or security guarantee.

## Follow-up

The [JIT-versus-frozen study](../benchmarks/RESULTS.md) tested full multi-turn
execution with a shared executor and independent evaluator. The original
`jev_agent.py` demo was subsequently replaced by a compatibility entry point to
the real backend. [Production context findings →](BACKEND_CONTEXT.md)
