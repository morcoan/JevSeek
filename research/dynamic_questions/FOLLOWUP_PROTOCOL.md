# Exploratory follow-up: dynamic questions without generated action wiring

Frozen AFTER the initial 16-task results but BEFORE this follow-up's calls. This is a diagnostic on the SAME cases, not an independent replication or rescue of the original score.

## Why
Initial graph pilot: direct15/16, programDS0/16, programJev0/16.13 graphs violated the phase/action schema, and3 valid graphs asked about unread contents. Both evaluators correctly returned unknown throughout those3 graphs. The example r0/p0 defaults were copied and selected the wrong file/patch. These compiler/prompt/DSL failures prevent an informative test of classification quality. Do not attribute them to Jev.

## Fixed design
Reuse each original direct arm's actual file read and its observed contents, without using test outcomes or winning patch IDs. All16 direct reads selected the relevant file. Generate2–6 atomic, action-relevant yes/no/unknown questions from that observed state, ONCE per case, no action votes or branching program. Same questions/evidence are supplied to both evaluators.

Compare:
- archived direct patch choice (original single decision on this exact state);
- **questions only:** same generator chooses patch with the generated questions visible but no answers;
- **questions + DS:** DeepSeek classifies the questions, then the same generator chooses a patch with those labels;
- **questions + Jev:** Jev classifies the identical questions in a parallel batch, then the same generator chooses a patch with those labels.

Question author and all patch choices use deepseek-flash with thinking disabled; Jev1.13.0. The chooser is NOT told which provider produced the labels. Answers are explicitly fallible assessments, never facts overriding raw code. No confidence displayed. Node question/purpose/yes/no criteria visible equally. No hidden tests, source previous choices, results or expected answers in any provider input. No changes to tasks, candidates or hidden cases. No generated code execution. No provider retries or result-based additional attempts. Invalid output counts as arm failure. Invalid question list fails all3 follow-up arms.

Expected maximum80DeepSeek+16Jev requests (question author1, classifier1, chooser3 per task plus Jev1),96total. Author max1400tokens, classifier300, chooser100. Alternate evaluator/chooser order by task. All decisions precede evaluation. Stop after16cases, no extra paid runs. Report graph failure separately and retain it.

## Measurements
All-cases patch correctness; paired rescues/regressions against archived direct and questions-only; Jev-vsDS differences; question count, unknowns, changed choices; median classifier-only latency AND full per-case serial sums including shared original read, question generation, classification and patch choice. Original read and generated questions counted fully in EACH reconstructed deployed arm. Token usage by provider, actual call costs unknown. Questions-only controls for prompts/generation but is NOT fully budget-matched; original direct is a single earlier sample, order/cache/network effects remain.

This tests the simpler dynamically generated-question scaffolding, NOT successful persistent cognitive-program reuse, graph redesign, full open-ended coding, a1Bmodel or cross-generator transfer. Same16closed-world easy cases and near-ceiling baseline limit conclusions. Any one-case improvement is exploratory and must not be presented as proven general gain. No app/VM/publishing changes.
