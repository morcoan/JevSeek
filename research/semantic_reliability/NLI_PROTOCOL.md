# Real-document boundary test — ContractNLI (frozen before inference)

Purpose: test the semantic component outside generated capability profiles, not claim the optimizer solves legal reasoning. ContractNLI (Koreeda & Manning, Findings EMNLP2021) contains17fixed hypotheses on607public non-disclosure agreements. Labels: Entailment, Contradiction, NotMentioned. Real contracts contain exceptions and cross-references. This is benchmark text classification, NOT legal advice or automated rights decisions.

Official archive https://stanfordnlp.github.io/contract-nli/resources/contract-nli.zip, SHA256e03fc77bbf8b53e2976a250e81d8a294bc3d5e5fb014521e477dee9340d6287b, CC BY4.0. Only dev/test JSON extracted, no PDFs executed. Public-data training contamination possible. To stay within bounded context, eligible docs contain1000..18000characters (52/61dev,104/123test); do NOT generalize to excluded long docs.

Seed480771 selects4development docs and8test docs, all17hypotheses per document (68dev/136heldout labels). No annotation-dependent selection. Full document text is provided, not gold evidence spans or oracle retrieval. Never send annotations, expected labels, file URLs or formal answers to providers. No tuning between phases: this is a fixed boundary probe even if dev is poor.

Arms:
1. Jev standard3-way document NLI.
2. Generic4-way grounded policy: same frozen RULES/CRITERIA as reliability runtime; source shared ONCE because all questions have exactly the same single-document scope. Conflict becomes abstention, not NLI Contradiction.
3. Dual-polarity generic policy: agree on claim/negation; disagreement/conflict becomes abstention, NOT a correct NotMentioned label. Two unknown judgments map to predicted NotMentioned. Model uncertainty can still masquerade as source uncertainty; scoring/false labels expose it, not treated as proof.
4. DeepSeek standard3-way batched NLI with same full evidence/hypotheses, thinking disabled.

Jev calls use bounded independent-question packaging with complete evidence preserved; no text truncation, no non-token-limit retries, max16requests/arm/doc. Nominal60remote requests total (48Jev12DS); hard cap156 (<=12Jev+1DS/doc) for this run. DSmax1200tokens/temp0. No local model/server required. Rotate arm order, all decisions before label scoring. No hypothesis/threshold changes after outcomes.

Report doc-clustered and total accuracy, per-label precision/recall and macroF1, false Entailment predictions, abstention coverage/conditional accuracy, provider/schema errors and actual usage/time. NotMentioned is a substantive NLI label, not a free abstention. Unknown/conflict handling cannot establish trustworthiness in every domain. If generic scoping does not beat the task-specific baseline here, retain that negative result and do not advertise universally improved comprehension. No app deployment/publication changes.
