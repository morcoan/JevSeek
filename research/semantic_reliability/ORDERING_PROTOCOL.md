# External ordering transfer — frozen before model calls

Use BIG-Bench-Hard logical_deduction_{three,five,seven}_objects, repository revision9ee07bd481feebf959a6b59d61ea57bdcf30964d.250examples/file, all750parse structurally. Selection seed340171:12development (6three/6five),48confirmation (24five not in development/24seven). This is a public, synthetic third-party benchmark, not an independent real-world sample; contamination possible. Seven-object size withheld from development.

The adapter extracts only the named object list, sentences and answer options. A documented axis convention sets left-to-right, cheapest-to-priciest, oldest-to-newest, or highest-to-lowest finisher. It does NOT parse the logical meaning of sentences or use target labels to build a program.

For every source sentence and every option, interpreter selects one canonical constraint from the SAME catalog: before(a,b), at(a,position), not_at(a,position), or unsupported. Each scoped Jev question contains its exact source sentence and context, no other rule text. Deterministic code enumerates all <=5040orders satisfying compiled premises, then chooses the unique option entailed in ALL remaining orders. Missing/unsupported/inconsistent/ambiguous translations abstain; never silently drop a premise. This is a different global reasoning structure from min-cost placement. The kernel proves entailment only conditional on correct translation, not correctness of the natural-language interpretation.

Arms, same source and catalogs:
- Direct nonthinking Qwen1.7B option choice.
- Direct Jev option choice (separates using a stronger model from symbolic computation).
- **Focused Jev typed compiler + exact ordering solver (primary).**
- DeepSeek typed compiler + same solver, one batched JSON request.

One call per arm/case, rotation by case.0retries. Qwen allowed-label grammar, temp0,max200tokens; DScompiletemp0,max1000. No model-generated executable code, no hidden answer labels in input. Exact formal certificate replayed offline. Source hashes/selection frozen. Original parser examples inspected for structural compatibility before selection but no provider outcomes seen; all sample counts/failures retained.

Development<=48requests:12localQwen,24Jev,12DS. Proceed to confirmation with identical policy only if primary solves>=10/12 and exceeds Qwen direct OR Qwen direct is itself at ceiling. This is a pragmatic discovery gate, not proof of superiority over direct Jev. Confirmation<=192requests, total<=240. If gate fails, do not run the confirmation sample with a tuned policy under this protocol.

Report success/abstentions by object count, paired comparisons vs BOTH direct baselines and strong compiler, conditional proof validity, source/criterion consistency, actual usage and full call+solver timing. A specialized parser for this controlled grammar could outperform learned translation; not measured here and no superiority claim over it. Distinguish useful reusable semantic interface from novelty/general intelligence. No app/VM/publishing changes.
