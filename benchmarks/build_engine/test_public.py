import tempfile
import unittest
from pathlib import Path
from engine import build

class Smoke(unittest.TestCase):
    def test_dependency_and_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root/'src').write_text('source')
            graph = {'a': {'inputs':['src'], 'output':'a.out', 'command':'compile'},
                     'b': {'deps':['a'], 'output':'b.out', 'command':'link'}}
            def run(name, command, root):
                (root/graph[name]['output']).write_text(command)
            self.assertEqual(build(graph, ['b'], root, run), ['a','b'])
            self.assertEqual(build(graph, ['b'], root, run), [])

if __name__ == '__main__': unittest.main()
