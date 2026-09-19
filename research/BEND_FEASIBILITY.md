# Bend2 rewrite feasibility — assessed, not adopted

**Status: literature/source feasibility review on2026-09-18; no rebuild, speed benchmark or application change.**

The request was to rebuild the entire Windows JevSeek application in [Bend](https://bend-lang.com/). The inspected project was Bend2(v2.0.5), not the older HVM-based Bend1. The inspected release archive SHA256 was `4db70e77ce1b1027f1d0e15dee025921fa794a9b415add4350ec7c64acf2775b`; the source review covered its base effects and compiler entry point.

At that inspected version, a native full replacement lacked the required Windows desktop path and several essential interfaces: HTTPS/TLS/JSON integration, process execution for existing tools, durable fsync/locking semantics, native credential storage and existing WebView/React/OpenHands integration. Foreign C/JavaScript adapters could supply missing functionality, so this is a practical feasibility decision—not a mathematical claim that such software could never be written.

JevSeek is largely a sequential API/tool-I/O orchestrator. No measured CPU-bound hotspot justified assuming a parallel-compute language would accelerate it. A small pure deterministic component could be a separate experiment, but it was not implemented or benchmarked. No Bun/WSL install, Windows feature change or reboot was performed for this review.

**Decision:** leave the working Python/native-tool/React architecture alone. No performance win was demonstrated, and a whole rewrite would add unvalidated platform and persistence risk. This is a historical review of a pinned version, not a statement about all future Bend releases.
