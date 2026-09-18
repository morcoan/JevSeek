# Intent-relevant memory: a finite window over a growing archive

**Status: scoped investigation and v0.2.2 implementation, September 18, 2026.**
This is not a claim of literal infinite model context, perfect recall, or a new
Terminal-Bench score. No VM, task sweep or generation-model benchmark was run.

## The incident and immediate fix

A real session stopped after 55 tool results, then stopped again on Resume with
`ContextOverflow: Context accounting reserve exhausted`. In v0.2.1, context was
trimmed to its budget **before** adding `archived_execution_count`. That extra
JSON field could overflow an otherwise valid projection. Retrying rebuilt the
same oversized state, rather than repairing it.

The fix counts every field before fitting. If necessary, optional retrieved
pages, historical rows, duplicate source snapshots and older detailed effects
are removed from the projection. Original records remain saved. Current intent,
earlier user requests, previous conversational reference, latest effect and
verification/status metadata are not silently discarded.

A read-only diagnostic projected the actual saved history through both versions
while varying reserved-overhead bytes to locate the exact bookkeeping boundary:

| Measurement | Result |
|---|---:|
| Reserved overhead at matching boundary | 1,973 bytes |
| Available router budget | 22,027 bytes |
| Old projection | Exact reported reserve-exhausted exception |
| Corrected projection | 21,022 bytes, 51 archived effects |
| Saved log changed / effects replayed | No / no |

The overhead above is a controlled matching boundary, not a claim to have
reconstructed the original process's exact MCP catalog. The user's trace and
paths remain private and are not in this repository. No provider was called by
this diagnostic.

## What the literature supports

- **[MemGPT (2023)](https://arxiv.org/abs/2310.08560):** external storage and explicit
  paging can provide the *appearance* of more context while model calls remain
  finite. Its experiments do not establish perfect retrieval or unlimited task
  performance. This motivates separate authoritative archives and disposable
  working sets, not continually increasing the prompt.
- **[Lost in the Middle (2023)](https://arxiv.org/abs/2307.03172):** relevant evidence
  can be used less effectively when buried in long input. More supplied text is
  not necessarily better. Its tested models/tasks are not current JevSeek scores.
- **[LongMemEval (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/file/d813d324dbf0598bbdc9c8e79740ed01-Paper-Conference.pdf):** evaluates extraction,
  cross-session reasoning, temporal reasoning, updates and abstention, and separates
  indexing, retrieval and reading. This motivates testing newer corrections and
  missing evidence rather than just easy keyword needles. We did **not** run the
  LongMemEval benchmark or reproduce its published results.

## Scoped Jev retrieval study

Source: [`experiment.py`](experiment.py). The fixture contains one user record,
12 hand-authored fact records and 3,000 unrelated later tool records. There are
10 answerable questions and two intentionally unsupported questions. It covers
exact terms, paraphrases, a prohibition, approval, an updated configuration and
a resolved diagnostic. Original negative and superseded facts stay in the corpus.

| Method | Measurement | Observed |
|---|---|---:|
| Latest 8 records | Contains answer on 10 answerable questions | 0/10 |
| SQLite FTS5/BM25, top 4 | Contains answer on 10 answerable questions | 9/10 |
| Candidate union: lexical top 16 + recent 8 + first 8 fact records | Contains answer | 10/10 |
| Jev-1.13.0, single choice over that candidate union | Correct record or correct abstention | 12/12 |

The lexical miss was the paraphrase about whether an autonomous job could fetch
packages from the internet; its fact concerned public-network access in unattended
runs. Jev selected that fact when the diversity tier exposed it. Jev also chose
newer Meridian/Falcon records and abstained on both unsupported questions.

**Measured one run:** 12 Jev calls, 31,791 reported input tokens, 2,044 reported
output tokens, zero request errors; 1.957 seconds cumulative request time,
0.153 seconds median and 0.288 seconds maximum. These are sequential API timings
on one machine/connection, not end-to-end agent latency or causal speedup. Provider
billing cost was not measured; Jev is billable. No DeepSeek/Bonsai call was made.

### Important caveats

This is a tiny, hand-authored, intentionally old-evidence fixture, **not** an
independent quality benchmark. The early-history diversity tier favors this
layout and cannot scale to every old fact. Recency's failure is expected by
construction. Retrieval recall@4 and single-choice selection accuracy are
different metrics: their percentages are not a fair head-to-head answer-quality
comparison. There is no blind reader, randomized placement, embedding baseline,
repeated sampling, adversarial instruction suite or real task-success measurement.
The study does not establish calibrated confidence, general reliability, or a
causal Jev contribution over other semantic rerankers. If the correct record is
not in the candidates, Jev cannot select it.

## What ships, versus what remains research

**Shipping:** `jevseek/memory.py` builds a session-local SQLite FTS5 cache of
original user messages, assistant finals and tool results. Large saved output is
indexed in ~2 KB text pages with 128-character overlap, rather than only its
head/tail excerpt. Event sequence, kind, status and page preserve provenance.
Only artifact paths resolving inside that session are read. Search uses literal
terms, not user-supplied SQL/FTS syntax. It never searches arbitrary workspace files.

Context can include up to two relevant older execution pages beside recent
results, only if budget permits. **Jev selects the `recall` tool** when more
historical evidence is needed; the generation model supplies a search query or
exact `record_seq`, and `next_offset` supports further pages. This uses the same
native-function validation boundary as other actions, but archive lookup itself
is local and read-only. Recalled output is excluded from indexing to prevent
recursive self-reinforcement. A recall does not invalidate current source caches
or count as a possible workspace change. Missing search hits never imply absence.

**Not shipping as a default:** the study's extra Jev reranking call and fixed
early-history candidate tier. One favorable synthetic run does not justify extra
calls on every context build. Production uses local lexical selection and Jev's
existing tool-routing decision to request more evidence; these are distinct from
an always-on semantic reranker. No hidden extra memory-provider calls occur.

The cache `memory.sqlite3` is disposable private data alongside the authoritative
session log/artifacts. If damaged, optional automatic retrieval falls back to the
existing context; explicit recall reports an error. Close the app before removing
a damaged cache to rebuild it next time. Indexing/retrieval still consumes disk,
CPU and RAM, and sessions themselves currently load their event log into memory.
This is **not** constant-memory processing of an infinitely long log.

### Hard limits we deliberately keep

All user requirements remain pinned, rather than guessed away by a relevance
model. A task whose required instructions/schema/metadata alone exceed the budget
can still pause safely. Arbitrarily long conversations with unbounded accumulating
user instructions are therefore **not solved** by this release. Archives persist;
model windows, disk and retrieval recall are finite. Old file observations may be
stale, assistant claims are not evidence, and execution uncertainty is never
cleared by retrieval. Actual current source still needs reading before edits.

The next defensible experiment is randomized evidence placement, distractor and
paraphrase variation, withheld tasks, multiple relevant records, update/conflict
cases and reader/task outcomes under equal token/cost budgets. Durable constraint
revision needs its own design before dropping old user instructions automatically.

## Reproduce only this investigation

```powershell
# Local indexing and retrieval only; no provider calls
python research/context_memory/experiment.py
# Explicitly paid Jev-only 12-call selection experiment
python research/context_memory/experiment.py --live
```

Uses installed project dependencies. Credentials follow the application's private
Jev vault/environment setup. Results are written under ignored
`.local/research/context-memory/`; do not publish raw local traces. The script
never executes a workspace task or reads the user's conversations/workspace code.
A source build/static audit and this scoped study do not certify the new release
on every Windows system; no broad test-suite run was performed for this update.
