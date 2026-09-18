# Task: implement a reliable incremental build engine
Complete engine.py using Python standard library only. Public API:

class BuildError(Exception)
def build(graph, targets, root, run): -> list[str]

root is a pathlib.Path or string naming an existing directory. graph maps node names to dictionaries with `deps` (list of node names), `inputs` (list of relative file paths), `output` (one relative file path), and `command` (string). Missing deps/inputs mean empty lists. targets is a list of requested node names. run(name, command, root_path) is a callback that creates that node's output; it returns None on success or raises. Output parents must exist before calling run. Return the names actually executed in deterministic DFS postorder: targets in given order, dependencies in listed order, deduplicate shared nodes. Build only reachable nodes.

Incremental rules:
- Store a JSON manifest in root/.build-state.json, load it on later calls; no process-global cache.
- A node fingerprint includes its command, ordered dependency names and their fingerprints AND current output CONTENT hashes, ordered input paths and their CONTENT hashes, and its output path. Hash file bytes, not timestamps or sizes. SHA256 is suitable.
- Skip a node only if its fingerprint matches the stored record AND its output exists AND its content hash matches the recorded output hash.
- Rebuilding a dependency does not force a dependent rebuild if the dependency fingerprint and resulting output content are unchanged.
- If an input/command/dependency list/output path changes, rebuild affected nodes and dependents, not unrelated nodes.
- Preserve manifest records for nodes outside the requested closure. Unknown manifest schema or invalid JSON is a cold cache, not a crash.
- Persist manifest atomically using a temporary file + os.replace only AFTER all requested targets succeed. On any failure retain the exact old manifest bytes. Output artifacts need not be rolled back. Clean up temporary manifest files.

Validation:
- Before invoking any callback, traverse the entire reachable closure and reject unknown targets/dependencies, cycles, missing input files, duplicate output paths, absolute paths and path traversal outside root (including symlink escape). Inputs and outputs must remain inside root; normalize paths before comparison. Reject outputs that overlap .build-state.json or ANY reachable input file, and output paths that are existing directories. Unreachable invalid graph nodes must not cause failure.
- Wrap callback exceptions in BuildError with node name and original cause. If a callback returns without producing a regular output file, raise BuildError.
- Empty targets returns [] and does not create/modify state.
- Don't mutate graph or targets.

Use `python -m unittest -v test_public.py` for a local smoke test and `python acceptance.py` for the independent acceptance suite. Do not modify SPEC.md, test_public.py or acceptance.py. You may create extra tests. Finish only after verification. No external packages.
