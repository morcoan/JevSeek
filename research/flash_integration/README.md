# Jev integrated with DeepSeek V4.1 Flash

Research-only live native tool integration for structured reasoning and grounded decisions. **Not wired into the production app, not general coding intelligence, not authorization to execute a plan.**

- [Frozen experiment protocol](PROTOCOL.md)
- [Thinking-control budget amendment](CONFIRMATION_AMENDMENT.md)
- [Results and recommendation](RESULTS.md)
- `agent.py`: opt-in reusable integration entrypoint.
- `integration.py`: frozen native tool loop and matched Jev/Flash specialist backends.
- `answer_codec.py`: format-only output recovery, independently tested; never selects by truth or solver agreement.

## How it works

Flash receives the real task and a native `decision_analysis` tool. A validated request ID selects the immutable visible snapshot. The tool then:

1. **Allocation:** scopes each candidate/requirement judgment, then uses exact assignment search and unknown-edge cost bounds.
2. **Ordering:** asks one bounded Jev answer-choice question (prior work found a large compiler unnecessary on many such tasks).
3. **Grounded document claims:** uses full-source, three-way NLI; no pretend mathematical proof of natural-language/legal interpretation.

The proposed result comes back through an actual tool message; Flash produces the final answer. For the strong control, the SAME tool uses Flash instead of Jev for semantic assessments. The orchestrator is not told which backend it gets. Live model labels, not cached-quality replay. The frozen experimental loop allowed Flash to correct a tool proposal and scored the final answer, not just the intermediate tool.

## Entry point

```python
from research.flash_integration.agent import solve
from research.flash_integration.integration import Flash
from research.decoding_control.providers import credentials, jev_client

ds_key, jev_key = credentials()  # existing vault/.env helper; never print/export keys
flash, jev = Flash(ds_key), jev_client(jev_key)
try:
    result, trace = solve(
        {"id": "request-1", "kind": "allocation", "visible": snapshot},
        flash, jev, semantic_backend="jev",  # or "deepseek" for matched control
    )
finally:
    flash.close()
    jev.close()
```

`snapshot` must contain the documented visible allocation goal, `hosts` (IDs -> integer `cost` and natural-language `profile`) and `services` (IDs -> requirements). Limits: <=8hosts, one service/host, nonnegative integer costs<=1e12. **The caller must supply current evidence; content hashes do not detect real-world changes that were never observed.** Grounding expects `document` and `hypotheses`; ordering currently supports the explicitly documented BBH layout/axis conventions, not arbitrary prose layout.

The Jev document-grounding path is **blocked by default** because it regressed in this study; running that experimental branch requires `allow_experimental_grounding=True`. This is an explicit kind guard, not an untested learned task router.

Outputs are proposals under model-assessed semantics. Exact solvers can be perfectly correct over incorrect semantic judgments. Unknown/conflict handling is conservative, not a guarantee of correctness. Do not automatically deploy resources, approve legal decisions or bypass application permission checks.

## Reproduction

Existing cached research datasets and provider credentials are required; no local model/VM needed. Old frozen source must remain unchanged for hash replay.

```sh
python research/flash_integration/preflight.py
python research/flash_integration/experiment.py --phase development --run
python research/flash_integration/analyze.py PRIVATE_DEVELOPMENT_DIRECTORY
python research/flash_integration/confirmation.py --phase confirmation --development PRIVATE_DEVELOPMENT_DIRECTORY --run
python research/flash_integration/analyze.py PRIVATE_CONFIRMATION_DIRECTORY
python research/flash_integration/analyze_format.py PRIVATE_CONFIRMATION_DIRECTORY
```

`--run` explicitly enables paid inference. Merely importing the module does not send requests. Do not repeat a used confirmation set and call it new evidence.

## Sources / scope

- [Official V4.1 Flash model announcement / API alias](https://api-docs.deepseek.com/news/news260910).
- [Previous semantic-constraint study](../semantic_constraints/RESULTS.md).
- [Evidence-scoping protocol](../semantic_reliability/FRESH_PROTOCOL.md).
- [BIG-Bench-Hard](https://github.com/suzgunmirac/BIG-Bench-Hard), revision `9ee07bd481feebf959a6b59d61ea57bdcf30964d`; public synthetic ordering problems.
- [ContractNLI](https://stanfordnlp.github.io/contract-nli/), Koreeda and Manning, Findings EMNLP2021, CC BY4.0 dataset. Full-text inputs, no oracle evidence spans; <=18000character subset only.
- [Logic-LM](https://aclanthology.org/2023.findings-emnlp.248/) and [Logic-LM++](https://aclanthology.org/2024.nlrse-1.6/) motivate separating interpretation from exact reasoning, while warning that syntactic validity does not prove semantic correctness. Our measured results, not these papers, determine the integration recommendation.

Public benchmark contamination, small paired samples, document-correlated NLI labels and the synthetic allocation generator limit generalization. No dollar, energy, FLOP or broad coding-gain claims.
