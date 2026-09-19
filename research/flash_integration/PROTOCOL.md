# DeepSeek V4.1 Flash + Jev — native integration comparison

Frozen before inference. New user request: test whether Jev improves DeepSeek on appropriate structured reasoning and grounded decisions. Research harness only; no app, release, VM or physical resource changes.

## Identity and question
Official https://api-docs.deepseek.com/news/news260910 identifies `deepseek-flash` as V4.1 Flash. Use the official chat-completions endpoint, log requested/reported models and reasoning usage. Primary baseline and agent orchestration are nonthinking (thinking disabled, reasoning_effort none), matching the app. ALSO include thinking-enabled direct Flash (high, max8192completion tokens) on EVERY case; report truncations rather than silently retrying. No claim against unconstrained maximum-compute Flash.

## Tasks / split
6development +24confirmation cases, two/eight per avenue:
- **Allocation:** new seeds621000..621009; 6candidates/5jobs, minimum integer cost, complete natural-language capabilities and Boolean requirements. Cycle deployment/test-runner/document-processor vocabularies. Same synthetic generator as previous research, NOT new real-world domains. Independent enumeration verifies hidden optima; no facts/AST/labels/optima sent to providers.
- **Ordering:**10new seven-object BIG-Bench-Hard cases, seed621811, excluding ALL prior ordering development/confirmation/transport IDs. External public synthetic benchmark; contamination possible. Since direct Jev already matches compiler accuracy at much less input overhead, use one bounded answer-choice judgment, NOT the wasteful giant compiler catalog.
- **Grounded document decisions:**10new ContractNLI test documents, seed622033,1000..18000characters, excluding all previous selected documents;17fixed hypotheses each. Full unannotated text, never gold evidence spans. Model predicts Entailment/Contradiction/NotMentioned. This is a boundary probe where earlier gains were weak, not a promised positive result; no legal advice or automated rights decisions.

All selection/protocol/source hashes saved before calls. The first2peravenue are development, remaining8 confirmation. No score-based dropping, no tuning on confirmation. Gate concerns transport/native tool correctness only, not whether Jev wins. If implementation repair is necessary, preserve the failed run and freeze a revised protocol before new data.

## Four arms
1. **Flash direct:** plain nonthinking, final JSON.
2. **Flash thinking direct:** same problem/output, reasoning enabled high,8192token cap.
3. **Flash + self-backed decision tool:** real native tool_choice auto -> separate Flash specialist assessment -> same owned deterministic processing -> tool message -> Flash final response.
4. **Flash + Jev-backed decision tool:** identical native tool name/schema/description/orchestrator prompt, but backend assessment from Jev -> same processing -> tool message -> Flash final response.

Tool backend identity is hidden from the orchestrator. Each tool takes only the current request_id; it cannot change sources, access gold or execute code/effects. Live provider calls, not cached label replay. The self-backed tool is the strong scaffold/extra-call control: it sees the SAME scoped questions, criteria and evidence as Jev. For allocation, both feed their four-way judgments to the SAME exact assignment solver. Unknown/conflict edges are unavailable, not Boolean false facts. Solver optimality is conditional on interpreted eligibility. Ordering/NLI do not get a fake solver that cannot certify language.

Agent may choose not to call the available tool (record it). At most one native tool turn, followed by final JSON with no further tools. It may correct the proposed answer using original evidence; no instruction to blindly copy. Final-answer quality is primary, tool-stage quality separately measured. No generated code executes. Rotate arm order. Same final token allowance(2048) for plain/agent reports. Backend Flash JSON2048,temp0; Jev bounded requests<=2/case. No semantic retries. Temperature0; no API retries.

## Budget / evidence
At most210Flash +60Jev requests for both phases; expected210Flash+30Jev. Reasoning tokens/cold-start exclusions disclosed. No local model or VM required. Stop at the frozen sample: do not expand until a win appears.

Record all native messages, tool args/results, errors, usage, backend decisions, complete call timings and deterministic solver latency. Report TOTAL per-arm latency and input/output/reasoning/cache tokens, not just Jev's stage. No dollar/FLOP/energy claims. API aliases may be mutable; no weight-checksum claim.

Metrics: final feasible AND globally minimum-cost allocation; final ordering accuracy; document/hypothesis accuracy, macroF1, false Entailment decisions, abstentions. Paired rescues/regressions by avenue vs direct and self-tool; separate thinking baseline. Document-level clustering, small samples, public-data contamination and synthetic-generator limits explicit. Null/negative transfer is a valid outcome. No universal intelligence/coding claims.
