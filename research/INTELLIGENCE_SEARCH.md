# Finding a useful Jev augmentation boundary

## Result

A **domain-limited working mechanism** emerged: use Jev to translate natural-language compatibility requirements into explicit constraints, then use exact code to solve the global problem. Let the LLM call this capability as a tool instead of expecting it to reason out or implement every step correctly.

On24fresh synthetic confirmation cases: Jev+solver22valid minimum-cost plans, Qwen3-1.7B alone0, Qwen judgments+same solver0, solver without semantic filtering0, DeepSeek batched judgments+same solver10. The actual Qwen native-tool replay invoked and consumed the module24/24times and preserved all outcomes, including two failures. Replay uses cached real Jev labels and is not another independent quality trial.

**This does not establish general intelligence, arbitrary coding improvement, or changes to model weights.** The domain has6binary capabilities and researcher-designed language/logic templates. A specialized parser for that tiny language could solve it exactly. Jev interpretation itself remained fallible. The result is an agent/tool capability gain with independently checked constraints, not a universal breakthrough.

## Evidence

- [Working mechanism, code and native tool connection](semantic_constraints/README.md)
- [Exact heldout results, costs, two failures and limitations](semantic_constraints/RESULTS.md)
- [Frozen development/confirmation protocol](semantic_constraints/PROTOCOL.md)
- [Prior SQL attempts and why apparent gains were insufficient](verified_search/RESULTS.md)

## What changed the outcome?

|Boundary|Finding|
|---|---|
|Jev selects complete SQL from a strong model's pool|No gain on the development cases|
|Jev selects from a1.7Bmodel's pool|No correct alternatives existed on failures|
|Jev flags defects and weak model revises|Defects sometimes recognized; bad implementation repeated|
|Jev supplies a positive semantic sketch|Some improvement, but weak implementation and benchmark artifacts remained|
|**Jev supplies semantic constraints to exact execution**|**Heldout22/24valid optimal plans; native LLM-tool consumption works**|

The important distinction: **make the semantic judgments operationally enforceable.** Do not merely tell a weak generator “be careful” and hope it implements the logic correctly.

No application/runtime changes, public upload, VM restart or benchmark resumption were made. Research models ran only in owned authenticated loopback processes and were closed afterward. Raw calls, fixtures and audit evidence remain private under `.local/research/`.
