# Context-budget correction — frozen before corrected inference

The original external48case confirmation is retained: all24seven-object compiler calls failed HTTP400 max_tokens_exceeded. This is an operational failure, not24wrong semantic answers. A single isolated known-failure probe confirmed the error. Accepted5object requests had~87KBJSON/27kinput tokens;7object requests had~241KBJSON. Model metadata did not advertise a numeric context limit.

Minimal correction: shard INDEPENDENT sentence-translation questions into deterministic <=60,000UTF8JSON-byte /<=30question batches, maximum16requests per case. No source, criterion or clause is truncated or dropped. A singleton exceeding budget fails closed. A specifically identified max_tokens_exceeded error permits deterministic bisection into smaller independent batches; other errors never retry. Every failed and successful request is counted. Byte estimates are conservative heuristics, not tokenizer guarantees.

Keep EXACT original ordering catalog, question wording, solver and dataset axis conventions. Thus this is packaging/scaling repair, not selection of a better answer prompt after seeing the labels.

Phases:
1. **Posthoc transport replay:** first8seven-object cases from the failed run, all retained regardless correctness. At most128Jevrequests, no other inference. Not a new quality confirmation. Gate requires complete typed answers and no unrecovered transport failures on all8cases; does NOT use correctness labels.
2. **Fresh transport confirmation:**20new seven-object cases sampled with seed481709 excluding every prior development/confirmation ID. Frozen before this phase; one directQwen, one directJev, one DScompiler call, and<=16Jevcompiler calls/case. Bound380totalrequests(20Qwen,20DS,<=340Jev). Actual expected compiler requests~5/case. No semantic changes between phases.

Report the original operational failure separately. On fresh cases compare compiler+solver against directJev, directQwen and same-schema DScompiler. Include all abstentions, exact replayed conditional certificates, complete input coverage, input/output tokens and SUM of all chunk latencies. Do not advertise one chunk as whole-system latency. DirectJev can be a better path when the entire decision already has a small answer set; do not force every problem through an expensive compiler. No app or VM changes.
