# Dynamic question-program pilot — frozen before provider calls

## Hypothesis
A generator can compile task-specific, action-relevant questions and answer-to-action mappings once. A fast typed classifier can execute this temporary policy over evolving tool evidence with fewer generator calls than direct reasoning, without losing repair accuracy. This is NOT decoder steering or candidate-plan ranking.

## Scope and safety
16 new hand-authored closed-world Python repair tasks, each with a buggy function, a symptom, three readable evidence files and four prewritten replacement functions. Exactly one replacement must pass all hand-authored hidden cases. The model selects actual read and patch actions. Only repository-owned prewritten code executes, in memory; API-generated strings are NEVER executed. No app changes, broad application suites, VM, Terminal-Bench or real repository edits. These are easy, small repair-selection fixtures, not open-ended coding, not 16 independent repositories, not proof for a 1B model. Evidence file names are descriptive, intentionally making relevant-file discovery fairly easy. Candidate patches make the search space easier than writing code from scratch.

## Arms (same generator alias deepseek-flash, thinking disabled)
1. **Direct:** generator selects one file read, observes its actual content, selects a replacement. Two calls, no questions.
2. **Dynamic + DS:** generator compiles a declarative question program from initial state, then DeepSeek classifies its ready questions, first to choose a read and again using the resulting evidence to choose a patch. Compiler runs once, never sees hidden files or test outcomes. No action-generation calls after compilation.
3. **Dynamic + Jev:** EXACT SAME compiled program, Jev classifies ready questions in parallel per phase, deterministic runtime chooses read/patch. A different read can yield different second-phase evidence. No extra generator call.
4. **Compiler fallback (diagnostic):** apply the program's initially chosen fallback patch without any classification. This distinguishes information in compiler mappings/defaults from evaluation value. It is not a paid fourth arm.

Question-program schema: read phase 1–3 nodes; patch phase 2–6 nodes; every node includes id, narrow question, purpose, yes/no definitions and per-answer action votes (integers -2..2). Unknown votes are always zero. Runtime sums votes; fallback wins ties if tied, otherwise lexical action ID wins. Patch abstain is allowed and counts as failure. No probability multiplication, confidence thresholds or score-as-correctness assumptions. All nodes of a phase are independent; phase transition provides the dependency. Fixed action budget one read then one patch. This is a two-level temporary decision graph, not an unrestricted DAG or self-rewriting long-running agent.

The compiler must not ask the evaluator to choose a patch/action directly; questions should identify evidence-supported distinctions that change an action. It can still violate this semantically: report examples rather than claim perfect automatic dedup or omission detection. Syntax/IDs/votes/count bounds validated deterministically; malformed compile or inference fails the affected arm, with no retries or replacement runs. The graph is reused across evidence updates; no LLM-generated redesign is tested here.

## Procedure and controls
- Validate owned buggy/candidate functions and hidden expected cases before any paid call; freeze source hashes in a manifest.
- Shuffle patch IDs and evidence-file IDs deterministically by task. Run each of 16 tasks once. Alternate provider-arm order by task; no result-based additional trials.
- Compile before any direct/evaluator calls for a task. Compiler and direct see the same initial source, symptom, file list and candidate replacements, but not each other's output.
- Both evaluators receive identical classification instructions/schema and the same graph. They see only the file their own policy read, with source hashes.
- No hidden tests/expected results or winning candidate sent to any provider. Test execution happens only AFTER all arms' choices on that task; no feedback rescue loop.
- API retries zero. Expected 80 DeepSeek +32 Jev calls (one compiler+two direct+two DS evaluator; two Jev evaluator per task). Invalid graph/call may reduce counts. Cap of 112 total requests. Compiler max 2400 output tokens, direct max 100, classifier max 300. Provider errors count, never silently discard cases.

## Outcomes (specified before calls)
Primary: fraction of 16 tasks passing ALL hidden cases after the actual chosen replacement, paired rescues/regressions against direct and against DS graph evaluator.
Secondary: evidence-file selection, invalid programs, abstentions, unknown answers, number of generated nodes and evaluations, compiler-fallback accuracy, actual request latency/input/output/cache tokens, reconstructed per-arm serial wall time including the compiler in BOTH dynamic arms. Shared compilation is measured once physically but charged fully to each hypothetical deployed arm. Do not report just classifier time as whole-system speedup.

No dollar/energy/FLOP savings without verified billing/measurement. No inference of parallel-request throughput from per-call batched answers. No calibrated accuracy interpretation of Jev confidence. Small hand-authored pilot, descriptive paired counts only, no general coding or cross-model gain claim. Repeated runs, larger unseen tasks, fixed-question control, budget-matched direct extra call and stronger open-ended sandboxes would be follow-ups, not silently added to this run.
