# Small-generator / stronger-critic experiment

Frozen after the DeepSeek development result (11/12direct=Jev-pair, gate failed) and BEFORE any Qwen inference. The strong-generator configuration is not being rescued or rerun. This is a new test of a capability-gap hypothesis: Jev might supply judgment absent in a genuinely smaller generator.

## Model and containment
Official Qwen/Qwen3-1.7B-GGUF, revision90862c4b9d2787eaed51d12237eafdfe7c5f6077, Q8_0 file1834426016bytes, SHA256061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a. Nonthinking, max16384context,1200generationtokens, temperature0.7/top_p0.8, per-sample seed logged. JSON-schema grammar ensures response envelope; it does not ensure SQL correctness. Own nonce-authenticated loopback llama.cpp server, provider credentials stripped from child environment, job-close process cleanup. Existing app preferences, other model servers, Windows features and stopped VM/benchmark are untouched. One research model downloaded (~1.8GB), no weight modification/training.

## Policy and controls
Use EXACT same public selected12development /28DB-disjoint confirmation tasks as the prior protocol. They were not selected based on this model's behavior. Three Qwen SQL samples per task. Same complete-query execution observations, blinded labels, pairwise/global questions and tie rules as PROTOCOL.md. No graph/question-author stage. No critiques or repair-generation yet.

Compare first Qwen sample, first executable, execution majority, analytic random expectation, Qwen self-judgment, Jev judgment, and DeepSeek judgment on the SAME Qwen candidate pool. The additional DeepSeek judge asks whether an ordinary stronger model would work as well; it does NOT provide alternative SQL solutions. Primary treatment remains Jev pairwise tally. Global choices secondary, not substituted to rescue a losing primary. Same SQL metric/limitations as prior protocol; original one-DB row-multiset agreement is not official Spider accuracy or proof of semantic correctness.

Generators/judges see no gold SQL or gold result. Strong-model outputs are never used to create or repair Qwen candidates. Candidates execute under the same read-only/VM budget. Each task's gold evaluation happens after all judges decide.

## Gate and budgets
Development once: <=36localgeneration+12localjudge+12Jev+12DeepSeek=72requests. Proceed to28confirmation cases ONLY if Jev primary beats direct, is at least as good as majority, and rescues >=1case beyond first-executable. No policy changes between development and confirmation. Confirmation <=168requests. Total this configuration <=240requests. Original52DeepSeek-phase calls remain a separately reported failed attempt. No retries or best-run picking.

If development passes but confirmation does not improve direct/majority/self-choice, do not claim validated gain. Report paired differences, oracle coverage, DS-judge control, exact sample outputs/results, API/format errors and side effects. A small sample with correlated DB questions supports only narrow observed gains, not universal intelligence or model-agnostic effectiveness. Model strength difference is the hypothesis, not a claim established before measurement.

Charge all3Qwen generations to search arms. Compare latency with first sample, majority and both judges, not only remote classifier time. Record tokens by provider; local API charge zero is not zero hardware/energy cost. Serial timings reflect this machine, and extra-compute quality gains are not equal-budget scaling results. Do not deploy/apply/publish app changes from this experiment.
