# Semantic reliability: what generalized, what did not

**Status: completed research; no generic production semantic-reasoning layer enabled.**

Evidence scoping improved the synthetic planning interpreter. API-budget sharding repaired a real transport failure without truncating evidence. Neither result establishes general grounding reliability or superiority over thinking Flash. Full-contract judgments remained fallible.

Read [results](RESULTS.md). Protocols and original runtime files remain frozen; publication adds documentation and an offline boundary analyzer, not new model trials.

## Components

- `runtime.py`: scoped evidence/claims; supported, refuted, unknown and conflict; exact Boolean evaluation over unknown completions; content-keyed cache.
- `engine.py`: revision-scoped cache and optimistic/pessimistic assignment-cost bounds. It was subsequently checked through the Flash integration's729unknown-edge solver cases; semantic labels remain model judgments, not proofs.
- `bounded.py`: conservative UTF-8 payload/question budgets; subdivision only for the recognized token-limit error; no evidence truncation or missing-question acceptance.
- `diagnostic.py`, `fresh.py`: known-error diagnostics then new synthetic confirmation.
- `ordering_experiment.py`, `transport.py`: external BIG-Bench-Hard ordering and transport correction.
- `uncertainty.py`: authored uncertainty/conflict stress cases.
- `nli.py`: real ContractNLI document boundary probe.
- `analyze_boundary.py`: offline source/input/solver replay and label-only public export for the completed transport/NLI runs. It requires private original traces and separately cached upstream data; importing it makes no model calls.

## Reproduction and data

Install project core dependencies. The recorded Qwen runner additionally requires the official pinned Qwen3-1.7B GGUF and an existing Windows llama.cpp runtime at the research helper's configured path; those binaries are not redistributed. See `../verified_search/local_model.py`. Live scripts explicitly require `--run` and spend API credits; local-model scripts may start their OWN loopback server. Do not run them expecting an offline audit.

Offline checks:

```sh
python research/semantic_reliability/preflight.py
python research/semantic_reliability/preflight_bounded.py
```

Each `*_PROTOCOL.md` declares sample selection, request budgets and scoring. Files under `.local/research/semantic-reliability/data/` are private cache inputs, not bundled downloads. Fetch independently from the pinned sources below and verify the hashes in public summaries/protocols. The public `boundary_summary.json` exposes per-case answer labels, document-level predictions, source/data hashes and usage—no full contract text, personal sessions or provider request bodies.

- [BIG-Bench-Hard](https://github.com/suzgunmirac/BIG-Bench-Hard/tree/9ee07bd481feebf959a6b59d61ea57bdcf30964d), logical_deduction_three/five/seven_objects.json. Pin: `9ee07bd481feebf959a6b59d61ea57bdcf30964d`. Observe the upstream repository/dataset license and citation.
- [ContractNLI](https://github.com/stanfordnlp/contract-nli), Koreeda & Manning2021, CC BY4.0. Cached dev/test hashes are retained in `boundary_summary.json`; original ZIP SHA256 `e03fc77bbf8b53e2976a250e81d8a294bc3d5e5fb014521e477dee9340d6287b`. No oracle evidence spans or formal/gold annotations were shown to providers.
- [Logic-LM](https://aclanthology.org/2023.findings-emnlp.248/) and [Logic-LM++](https://aclanthology.org/2024.nlrse-1.6/) motivate interpretation/solver separation and semantic-error checks. They are not evidence that this implementation inherits their results.

Public-benchmark contamination is possible. All used IDs/seeds are USED, not fresh heldout evidence for a rerun. No model training or weight modification occurred.
