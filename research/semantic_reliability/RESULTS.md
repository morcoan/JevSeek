# Semantic reliability results and boundaries

## 1. Known-error diagnosis, then fresh planning cases

The prior semantic-constraint study retained two failures: mistaken egress implication and public/private exposure. These known cases were diagnostic data, not heldout validation.

| Sample | Legacy | Revised global wording | Focused evidence | Dual polarity |
|---|---:|---:|---:|---:|
|12known diagnostic cases, optimal plans |10/12 historical |—|12/12|12/12|
|48fresh synthetic cases, optimal plans |43/48|39/48|**47/48**|not run|
|48fresh cases, feasible plans |43/48|43/48|**48/48**|not run|

Focused asks each host/service compatibility question with exactly its target evidence and requirement, rather than asking the model to bind all entities from a large shared board. It was selected by the diagnostic protocol, not by retuning the fresh cases. The fresh sample uses three authored vocabularies over the same small capability/logic ontology—not new real-world deployment environments.

Of1440fresh pair judgments, focused had1434correct,0false positives and6false negatives(including5unknowns). Versus legacy it rescued5plans and regressed1; descriptive paired p=.219. Versus revised-global it rescued9/regressed1(p=.0215). Small correlated samples and an adaptive research sequence limit these p-values. The exact solver guarantees optimality only relative to the predicted relation; it cannot certify the neural interpretation.

`diagnostic_summary.json`, `fresh_summary.json`, `DIAGNOSTIC_PROTOCOL.md`, `FRESH_PROTOCOL.md` preserve the details. Diagnostic24Jev calls; fresh144Jev calls; no API errors.

## 2. External ordering: keep the transport failure in the record

BIG-Bench-Hard cases were selected from a pinned public dataset. Jev-direct chooses an answer. Jev-compiler and Flash-compiler translate sentences into enumerated constraints, then the SAME owned exact solver evaluates them. Flash compiler is nonthinking, not the best thinking Flash agent.

| Sample | Qwen direct | Jev direct | Jev compiler+solver | Flash compiler+solver |
|---|---:|---:|---:|---:|
|12development(3/5objects) |7/12|12/12|12/12|12/12|
|48original confirmation(5/7objects) |17/48|46/48|24/48|39/48|
|20fresh seven-object cases after packing repair |8/20|20/20|20/20|14/20|

**All24seven-object Jev-compiler calls in the original confirmation failed at the API context limit.** They are retained as operational failures, not falsely called incorrect semantic judgments. The approximately241KB request was too large; an87KB/27k-input-token request had worked. The SDK model-list endpoint did not report the context limit. Subsequently checked official documentation states64krequest tokens and32kstate+longest-question tokens; byte packing remains deliberately conservative.

`bounded.py` packs independent, unchanged questions within60000UTF8bytes/30questions and allows bounded subdivision only for specifically identified token-limit errors. It never truncates clauses or proceeds with missing labels. An8case replay of USED failures completed8/8(40Jev calls): repair evidence, NOT another heldout quality sample. The unchanged repair then ran20new seven-object IDs:160calls(20Qwen,20Flash,120Jev); both Jev arms20/20. **No accuracy advantage of the compiler over direct Jev was demonstrated.**

Publication's offline `analyze_boundary.py` recomputed all28replay/fresh solver outputs, checked dataset selection/source hashes and exact question coverage, and exported label-only `boundary_summary.json`. No new inference was needed. `ORDERING_PROTOCOL.md` and `TRANSPORT_PROTOCOL.md` retain limits and selection details.

## 3. Unknown/conflict stress suite

32authored cases cover supported/refuted/unknown/conflict, scope identity and instruction-like source text. Focused and dual each scored32/32,0false accepts and0abstentions in2totalJev calls. These are unit-like authored language cases, **not proof of prompt-injection resistance or calibrated safety**. See `uncertainty_summary.json` and `UNCERTAINTY_PROTOCOL.md`.

## 4. Real documents: generic grounding did not become reliable

ContractNLI full documents were used without oracle evidence spans.4development documents preceded8heldout test documents; each has17hypotheses. Restricted document lengths were1000–18000characters.

| Heldout136labels | Correct |
|---|---:|
|Standard three-way Jev |105/136|
|Generic four-state Jev mapped to NLI |107/136|
|Dual-polarity Jev |101/136|
|Nonthinking Flash, one batched matrix |109/136|

60requests total(48Jev/12Flash), including development. Around79%is NOT reliable arbitrary-document understanding. More elaborate dual checks did not improve the result. Labels within each document are clustered; eight documents are not136independent examples. This motivated blocking experimental Jev document grounding by default in the later Flash integration, where it also regressed.

`boundary_summary.json` includes development/test separation, predictions, abstentions and false-entailment counts. Publication replay verified12documents' source hashes, exact visible-only payloads, label decoding and original grades; no provider calls. `NLI_PROTOCOL.md` remains frozen.

## Adoption decision

Keep evidence scope, explicit uncertainty, source-version isolation and transport budgets as engineering lessons. Keep these semantic solvers **research-only**, not a universal replacement for Flash reasoning, grounding or tool argument generation. The later controlled comparison against thinking Flash is [separate](../flash_integration/RESULTS.md).

All underlying failures remain recorded. No app change or model/VM launch was made to produce this publication summary.
