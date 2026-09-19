# Uniform native batching correction (before continuation)

The initial run is preserved, not used to claim a capability result:37branches were rejected solely for multiple native calls in one response despite requesting parallel_tool_calls=False.36bundles were independent reads; one was read+configure. Initial98paid requests (86Flash12Jev) are retained.

Correct the runner, not the model/task: process supported native calls sequentially, return a tool result for every requested call ID, validate every schema, and enforce the ORIGINAL conservative limit of4total executed tool actions/branch and at most3probe executions/model turn. Do not run actions after finish. No arbitrary code, tools or file paths are admitted.

Reuse the recorded helper outputs and initial agent messages for ALL52branches. Replay recorded calls only if their full messages exactly match the reconstructed state. Generate ONLY missing continuations after previously rejected bundles. Identical prompts, sources, helpers, criteria, cases and grading; no answer selection, new hints or corrective messages. Cap4agent model turns/branch; at most111additionalFlash requests,0additionalJev/helper requests, keeping combined provider attempts<=209(original98+111), below244original ceiling. Fourworkers;360s continuation deadline.

This is a transport-corrected continuation on the SAME pilot cases, not a new heldout sample or independent replication. Original failures remain available. Apply the original futility gate to corrected final artifacts only, with helper and replayed-call latencies/tokens included. No subsequent sample expansion this turn.
