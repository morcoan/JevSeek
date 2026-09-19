# Results: dynamic questions, temporary policies and Jev

## Bottom line

**No Jev-specific correctness gain or end-to-end efficiency gain demonstrated.** Jev answered a batch faster than DeepSeek, but generating the questions dominated the short task. Question scaffolding fixed one baseline mistake, and merely showing the questions—without any answers—fixed the same mistake.

The persistent-program version first ran into compiler and evidence-acquisition failures. The controlled follow-up is more informative about question answering but is explicitly exploratory on the same cases. Neither establishes what would happen with a1Bmodel, a long-lived policy or open-ended coding.

## A. Original compile-once, execute-twice experiment

16 tasks,71 hidden cases. Shared generated policy, different evaluator, one actual file observation followed by an actual owned candidate replacement.

| Arm | Tasks passing all cases |
|---|---:|
| Direct DeepSeek read then patch |15/16|
| Generated program executed by DeepSeek |0/16|
| Same program executed by Jev |0/16|
| Compiler's default patch |0/16|

This is **not evidence that Jev cannot answer useful questions**:

- 13 generated graphs failed deterministic schema/action validation, including patch IDs in read-phase votes or structural mismatches. There were no API errors.
- 3 graphs were syntactically valid but asked about unread file contents to choose which file to read. Both evaluators returned unknown for all23evaluated nodes. That is a reasonable response to missing evidence, not a classification failure.
- The template's example `r0`/`p0` fallbacks were copied. All3valid graphs read a distractor and selected the wrong patch. The example/schema prompt and simplistic vote aggregator are genuine confounds and poor compiler design—not intrinsic requirements of the user's idea.
- Compiler median4.247s; entire direct two-action cycle1.436s. Lower inference counts after invalid compilation must not be marketed as savings.

Actual research usage:54DeepSeek requests,27,784input/16,288output tokens;6Jev requests,8,436input/868output tokens. No retries, no API errors. Invalid cases remain in the denominator.

## B. Shared-evidence question-scaffolding follow-up

Frozen after observing A. No altered cases, no hidden answers in prompts, no regenerated best-of attempts. Each arm sees the **same actual file observation** from the original direct arm. Generate questions once, then compare no answers, DeepSeek answers and Jev answers. Final patch chooser is DeepSeek in every follow-up arm and is not told the answer provider.

| Arm | All16tasks | On13valid question lists | Median reconstructed whole cycle |
|---|---:|---:|---:|
| Original direct |15/16|12/13|1.436s|
| Generated questions, no answers |13/16|13/13|3.919s|
| Questions answered by DeepSeek |13/16|13/13|4.580s|
| Questions answered by Jev |13/16|13/13|4.309s|

**Why three scaffolding failures?** The author included an additional textual `unknown` field in each question on `cursor_order`, `duplicate_refresh` and `stable_priority`. The frozen strict schema rejected these lists. These are interface failures—not three wrong semantic judgments. A more permissive or typed compiler could avoid them; silently accepting them after seeing results would change the registered run. The valid-case breakdown makes the distinction explicit without discarding failures from overall reliability.

**Was there any positive signal?** Yes, all three scaffolding variants corrected `role_gate`, where direct selected a reversed subset relation. But questions-only made exactly the same correction, so **Jev was not necessary for the observed gain**. There is only one baseline error on these small/easy cases, and this follow-up was chosen after seeing them; this is not statistically persuasive general evidence.

### What Jev actually changed

- 56 questions evaluated in 13 batches/provider.
- DeepSeek/Jev disagreed on3labels, with2unknown labels each.
- No disagreement changed the chosen patch or pass/fail result.
- Two disagreements came from generated interval questions with contradictory polarity: the question asked whether an empty/reversed interval **occupies time**, while its `yes` definition said it **does not occupy time**. Jev returned no; DeepSeek returned yes. Calling either universally wrong would ignore the malformed question. Typed output alone cannot catch this semantic inconsistency.
- The remaining disagreement concerned retry-boundary inclusion. Both downstream choosers still selected the correct implementation from the raw evidence.

### Latency and token accounting

Median classifier-only request:

- DeepSeek: 0.723s.
- Jev: 0.255s—about 2.8× faster for this stage.

But the question author alone had median2.620s, and the final chooser still ran. Whole Jev-scaffold cycle median4.309s was approximately**3×the direct cycle**, not a speedup. Versus the DS-scaffold arm, it was only about6%lower in median reconstructed serial time. These are sums of separately observed component request times, NOT causally timed production arms. Provider order alternated; caching/network effects remain. A question-author request reached35.686s, so medians hide material tail latency.

Hypothetical deployed arm usage across all16cases, including the original shared read and counting the shared question author fully in each arm:

| Arm | DeepSeek input/output | Jev input/output |
|---|---:|---:|
| Direct |13,162 /192|0 /0|
| Questions only |26,855 /7,805|0 /0|
| Questions + DS |39,806 /8,137|0 /0|
| Questions + Jev |27,325 /7,805|22,109 /2,055|

Comparing192tokens for selected action IDs against thousands of question-description tokens is a real overhead of **this closed-world task**, not a universal coding-cost ratio. We did not measure dollar charges, energy or FLOPs. Jev SDK/schema serialization has input overhead; nominally identical semantic questions do not guarantee equal tokenized prompts across providers.

Actual follow-up usage:68DeepSeek+13Jev calls,0API errors/retries. DeepSeek59,445input/8,197output tokens;Jev22,109input/2,055output. Total both studies:122DeepSeek+19Jev=141paid requests. No further paid runs were performed for this investigation.

## Per-case outcomes

`Q-only`, `Q-DS`, and `Q-Jev` were identical on every task.

|Task|Direct|All three follow-up arms|
|---|---|---|
|lease_boundary|pass|pass|
|retry_budget|pass|pass|
|cursor_order|pass|invalid question schema|
|zero_override|pass|pass|
|role_gate|fail|pass|
|latest_completion|pass|pass|
|interval_touch|pass|pass|
|duplicate_refresh|pass|invalid question schema|
|event_watermark|pass|pass|
|case_identity|pass|pass|
|batch_ack|pass|pass|
|negative_bucket|pass|pass|
|empty_search|pass|pass|
|stable_priority|pass|invalid question schema|
|path_scope|pass|pass|
|first_present|pass|pass|

## What would make the next experiment meaningful?

1. **Fix compiler semantics first**, not merely JSON. Unknown about an unread contract should trigger acquiring that contract, not select a random default. Questions and their yes/no definitions must agree.
2. A typed restricted representation should prevent phase/action wiring errors; generated natural-language programs should never gain authority to execute arbitrary code or declare tests passed.
3. Test **persistent reuse on independent multi-step tasks**. For a reusable program, compilation cost can theoretically amortize: `compile_cost + N × evaluator_cost` versus `N × direct_decision_cost`. We did not demonstrate the same useful program surviving enough changing states for this to pay off. Code generation and tool times must still be included.
4. Include questions-only, fixed-question, budget-matched extra-generator and independent held-out controls. A faster evaluator replacing a necessary existing classifier is a narrower and more supportable optimization than claiming improved intelligence.
5. Test the intended weak generator directly. DeepSeek-first does not establish that a1Bmodel can ask the right questions or compile valid policies. A stronger question compiler might help, but its cost cannot be omitted.

**Recommendation:** do not add this to production as an always-on loop on this evidence. The narrow latency result supports Jev as a faster classifier **when that classification stage is already useful**; its usefulness here was not established.

## Verification and limits

Before A: all16owned buggy implementations failed at least one assertion; exactly one candidate/task passed all hidden assertions. No provider-generated Python was executed. Afterward,25applied repairs in A and55in B (including reused direct outcomes) re-evaluated unchanged. Frozen hashes, deterministic vote decisions, actual read observations and matched question/evidence inputs checked offline. All choices were made before hidden evaluation outcomes for the corresponding task. Raw transcripts remain private; aggregate JSON and reproducible harness are local research artifacts.

No app code changes, publication, EXE build, VM restart or stopped Terminal-Bench work.16hand-authored microtasks are not71independent tasks, realistic repositories, calibrated classification labels, general quality evidence or a basis for claiming architectural novelty. The second experiment reuses the first's cases and baseline sample, with different chooser instructions and later request timing; questions-only is the closer within-follow-up control.
