# JevSeek research archive — results, not a success-only story

**Publication snapshot:2026-09-19.** This index is the authoritative status ledger. Historical reports/protocols remain as written: statements such as “not published” or “app unchanged” describe their original experiment, not this publication. No new paid inference, model launch or benchmark-VM restart was performed to publish these results.

## What we learned

**Jev is useful as a low-latency, inexpensive semantic decision component where the output space already exists and code can enforce/assemble the result.** It has not been shown to make thinking DeepSeek Flash generally smarter. Adding a critic or reranker to a competent agent often added cost without solving more tasks.

The cost objective is **lower total API spend at preserved task success**, not fewer Jev+Flash tokens. Jev1.13 charges input at$0.042/M and output is free under the checked public rates. The finite-choice experiment estimated34%lower cost than nonthinking Flash and85%lower than thinking Flash, at equal observed accuracy and lower latency. These are small endpoint results and list-price estimates, not whole-agent invoices or general quality guarantees.

## Complete study ledger

| Investigation | Status / result | Runtime decision | Evidence |
|---|---|---|---|
|Original routing / frozen plans / synthetic deliberation | One build-engine task favored feedback-driven JIT and plain generation; not a Jev-router ablation | Existing JIT/nonthinking design retained | [Original notebook](../RESEARCH.md), [routing](../benchmarks/RESULTS.md), [deliberation](../benchmarks/DELIBERATION.md) |
|Backend context and archival retrieval | Real context-accounting failure fixed; bounded source/history retained. Tiny retrieval pilot, no general memory claim | Existing v0.2.1/v0.2.2 fixes retained; no always-on neural reranker | [Backend](BACKEND_CONTEXT.md), [memory](context_memory/README.md) |
|Decision/plan selection |12SQL tasks: direct9, first-plan10, Flash self-selection11, Jev11, oracle12 | No unique Jev gain; not adopted | [Report](decision_selection/RESULTS.md), [literature](decision_selection/README.md) |
|Actual decoder-prefix steering | Direct9/12; Jev paused selection6/12. Later cached lookahead gain also achieved by a literal control | Failed/fragile; not adopted | [Report](decoding_control/RESULTS.md) |
|Generated question/action graphs | Initial compiled agents0/16; follow-up questions-only/Flash/Jev all13/16 | Compiler issues and no Jev-specific gain; not adopted | [Report](dynamic_questions/RESULTS.md) |
|Verified SQL search, repair and sketches | Selection/repair failed to create missing correct solutions. Sketch confirmation8/28for both Jev and Flash; exact-match artifacts make this NOT8robustly correct solutions | No dependable general coding/SQL win; research only | [All failures and caveats](verified_search/RESULTS.md) |
|Semantic constraints + exact optimization | Jev+solver22/24truly feasible minimum-cost plans vs direct Qwen0, Qwen+solver0, Flash batched semantics+solver10 | Domain-limited capability prototype, not general intelligence | [Result](semantic_constraints/RESULTS.md), [entry](INTELLIGENCE_SEARCH.md) |
|Evidence-scoped interpretation | Fresh48synthetic plans: focused47optimal/48feasible vs legacy43/43. Known-error diagnostics kept separate | Useful scoping lesson; generic semantic layer not enabled | [Result](semantic_reliability/RESULTS.md) |
|Ordering transport and uncertainty | Original24seven-object compiler requests failed context limits. Packing replay8/8, fresh20/20for BOTH Jev-direct and Jev+solver.32authored uncertainty cases passed both modes | Transport repair is engineering, not a new reasoning gain over direct Jev | [Result](semantic_reliability/RESULTS.md), [label evidence](semantic_reliability/boundary_summary.json) |
|Real ContractNLI documents | Heldout136labels: standard Jev105, generic107, dual101, Flash109 | Generic grounding not reliable; not adopted | [Result](semantic_reliability/RESULTS.md) |
|Native Flash+Jev integration | Allocation strict2/6/7/8(plain/self-tool/Jev-tool/thinking); Jev tool8/8, one final-format failure recovered offline. Ordering5/6/7/8. NLI107/107/102/114 | Narrow planning latency trade-off; thinking strongest. Jev grounding blocked by default in the research adapter | [Controlled report](flash_integration/RESULTS.md) |
|Three agentic interventions | Memory/coverage/loop: every main arm4/4per avenue;0extra tasks solved by Jev. Native batching defect corrected uniformly | All three stopped; ceilinged authored pilot, not proof of impossibility | [Report](agentic_screen/RESULTS.md), [original hypotheses](AGENTIC_OPPORTUNITIES.md) |
|Finite-decision efficiency | All provider arms96/96; compact Jev.225s vs plain1.162s/thinking3.583s. Jev input reduced52.7%relative to verbose Jev | Reusable specialist endpoint; no automatic app-wide router | [Measured report](efficiency/RESULTS.md) |
|Cost-weighted offloading | Same saved experiment repriced: Jev$0.00109137 vs plain$0.00164730/thinking$0.00737070(off-peak,96queries). No new quality trial | Optimize dollars/Flash calls, count Jev/fallback costs; not combined tokens | [Cost audit](cost_offload/README.md) |
|Argument offloading | Schema-fixed arguments: same output,0generation calls instead of1;28offline tests. General Jev slot/span prototype has39offline contracts but0live trials | **Only deterministic schema-determined bypass adopted in source. Neural argument adapter archived, not enabled** | [Status and prototype](argument_offload/README.md) |
|Terminal-Bench4 + local CRACK/Jev | Separate smoke integration reward1.0. Real sweep cancelled: one reward0, one trial error/no reward, third interrupted | No full benchmark score; VM stopped; not resumed | [Status](tbench4/README.md), [partial records](tbench4/partial_summary.json) |
|Bend2 full rewrite | Pinned-version feasibility review; no rewrite or speed experiment | No demonstrated win; architecture unchanged | [Review](BEND_FEASIBILITY.md) |

## What changed in the app for this publication

Only a **deterministic no-model argument bypass** was added. After existing Jev tool selection, if a conservative JSON-schema subset fixes every argument, code supplies that object instead of paying Flash/Bonsai to reproduce it. All optional/free/unsupported cases still use the original generator. No additional Jev call, source truncation, changed routing, generalized grounded reasoning, neural completion shortcut or synthesized-code offload was enabled.

The earlier semantic argument adapter was not yet live-tested. It is preserved under `argument_offload/`, including its proposed protocol and offline tests, instead of being quietly promoted to production. The tested finite-catalogue selector likewise remains a research API: its preconditions are not true of every coding-agent turn.

This is a **source publication**, not a new EXE release. Existing release assets remain unchanged. Whole-agent savings and offload coverage are unmeasured; no blanket percentage is claimed.

## Public evidence and reproduction boundary

Published: owned study runners/evaluators, frozen protocols, failed approaches, aggregate JSON summaries, selected label-only evidence, source/data hashes, limitations and dependency instructions. The pending transport/NLI summaries were completed by offline replay only.

Not published: `.env`, native-vault contents, personal MCP settings, agent memory/sessions, provider raw request bodies/headers, model weights, third-party dataset caches, VM disks/SSH keys, generated workspaces or build artifacts. **Do not force-add ignored folders to reproduce historical traces.** Some offline analyzers require those private original traces and cannot reconstruct them from public aggregate metrics alone. Rerunning the paid protocols creates new evidence, not access to the historical raw calls.

Public benchmark inputs are fetched separately from their pinned upstream repositories under their own licenses. No model-weight files or full ContractNLI documents are redistributed. Owned code is under the root MIT license; third-party material retains its upstream terms.

All used heldout IDs/seeds are now USED. Public-dataset contamination, small authored samples, correlated query families, imperfect graders, provider load/cache and moving aliases limit generalization. Native replay and offline format repair are not new independent quality samples. Confidence and valid JSON are not proofs of semantic truth or safe execution.

## Running research safely

Install the project core dependencies with `requirements.lock`. Read the relevant protocol before invoking a runner. Paid runs require explicit opt-in flags(`--run`/`--live`); local-model and Terminal-Bench runners require separate provisioned runtime/data and may have much larger resource/time requirements. Importing the published modules does not intentionally launch a study.

Recommended offline publication checks:

```sh
python -m unittest -v test_argument_offload research.argument_offload.test_prototype
python research/semantic_reliability/preflight.py
python research/semantic_reliability/preflight_bounded.py
python scripts/public_audit.py --history
```

Do not mistake the historical command examples for permission to restart the cancelled VM or incur API charges. No further paid experiments were launched for this publication.
