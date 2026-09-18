"""Incremental build engine. Implement the contract in SPEC.md."""
from pathlib import Path

class BuildError(Exception):
    pass

def build(graph, targets, root, run):
    root = Path(root)
    executed = []
    for name in targets:
        node = graph[name]
        run(name, node['command'], root)
        executed.append(name)
    return executed
