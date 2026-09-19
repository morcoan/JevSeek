# Argument offloading: production subset and incomplete neural prototype

**Status: offline-only prototype; live argument quality/cost experiment NOT RUN.**

The user later requested publication and adoption only of demonstrated wins. Accordingly the general Jev argument adapter was NOT enabled in JevSeek. It is preserved here instead of being deleted or described as a validated saving.

## What actually ships in source

`jevseek/argument_offload.py` recognizes a conservative subset of schemas that determine the entire argument object: closed empty objects, mandatory constants/singleton enums/nulls, and closed required nested objects. No values/defaults are inferred. Optional, free-form, reference or unsupported fields keep the original nonthinking generator path with the original input. Existing routing, native validation, persistence, cancellation and tool execution remain in control.

This deterministic subset has28offline tests, including enumeration of a small schema/value universe, an actual agent persist-before-effect/no-replay check, and a paired provider-call check: same fixed arguments,1original generation call versus0with the bypass,0extraJev calls. It is an engineering win, **not evidence of a new semantic capability or a measured whole-agent saving percentage**.

## What remains research-only

- `compiler.py`: finite enum/boolean slots, optional omission distinct from null, read paths/ranges copied from supplied context, explicit FALLBACK, context/schema fingerprints, no evidence truncation.
- `models_snapshot.py`: the prior proposed runtime adapter, retained as a standalone research snapshot. One non-retried Jev call; low-confidence/missing/invalid/unsupported results use the original Flash argument input. Confidence is an abstention heuristic, not truth.
- `test_prototype.py`:39offline mock/schema/cancellation contracts. The earlier combined57test result was these39plus18existing provider/agent/adapter tests. Mock calls do NOT establish neural accuracy or cost savings.
- `snapshot_manifest.json`: hashes before publication-time archival. Only imports/module documentation changed in the archived model/test copies so they can run independently from production.
- `PROTOCOL.md`: proposed6development+16confirmation gate. It was written, but the fixtures/runner/live calls were NOT completed. The user redirected work to publication. There are no hidden live results to infer from this protocol.

Run offline:

```sh
python -m unittest -v test_argument_offload
python -m unittest -v research.argument_offload.test_prototype
```

No live provider calls occur in these tests. Constructing the research model snapshot with credentials and calling its methods CAN spend credits; it is not an application plugin and is never imported by the desktop/backend.

## Do not transfer unrelated percentages

The earlier finite-catalogue endpoint showed [speed improvements](../efficiency/RESULTS.md) and [estimated cost savings](../cost_offload/README.md). Those results used complete, already-bound procedures. They do NOT demonstrate that this new argument compiler preserves task quality or saves the same percentages on actual coding sessions.

A future experiment must compare actual arguments/task effects against the original generator, count all Jev/Flash/fallback costs, reject unsupported requested optional values rather than defaulting them away, and retain every regression. No such further inference is running or planned by this publication.
