"""Evaluator-owned tests; loaded outside each agent workspace."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from engine import build, BuildError

class Acceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'src').write_text('aaaa')
        self.g = {'a':dict(inputs=['src'],output='out/a',command='a'),
                  'b':dict(deps=['a'],output='out/b',command='b'),
                  'c':dict(deps=['a'],output='out/c',command='c'),
                  'd':dict(deps=['b','c'],output='out/d',command='d'),
                  'z':dict(output='out/z',command='z')}
        self.calls=[]
    def run_node(self, name, command, root):
        self.calls.append(name)
        self.assertIsInstance(root, Path)
        # Parents are the engine's responsibility.
        (root/self.g[name]['output']).write_text(command)
    def go(self, targets=None):
        return build(self.g, ['d'] if targets is None else targets, self.root, self.run_node)
    def invalid(self):
        with self.assertRaises(BuildError): self.go()
        self.assertEqual(self.calls, [])
    def test_01_diamond_order(self): self.assertEqual(self.go(), ['a','b','c','d'])
    def test_02_cache(self):
        self.go(); self.assertEqual(self.go(), [])
    def test_03_content_not_mtime(self):
        self.go(); p=self.root/'src'; stat=p.stat(); p.write_text('bbbb'); os.utime(p, ns=(stat.st_atime_ns,stat.st_mtime_ns))
        self.assertEqual(self.go(), ['a','b','c','d'])
    def test_04_command_invalidation(self):
        self.go(); self.g['b']['command']='new'; self.assertEqual(self.go(), ['b','d'])
    def test_05_output_tampering(self):
        self.go(); (self.root/'out/a').write_text('wrong')
        self.assertEqual(self.go(), ['a'])
    def test_06_missing_output(self):
        self.go(); (self.root/'out/b').unlink(); self.assertEqual(self.go(), ['b'])
    def test_07_output_content_propagation(self):
        self.go(); (self.root/'out/a').unlink()
        def changed(name, command, root):
            self.run_node(name, 'different' if name=='a' else command, root)
        self.assertEqual(build(self.g,['d'],self.root,changed), ['a','b','c','d'])
    def test_08_preserve_other_records(self):
        self.go(['z']); self.go(); self.assertEqual(self.go(['z']), [])
    def test_09_target_order_and_duplicate(self):
        self.assertEqual(self.go(['c','b','c']), ['a','c','b'])
    def test_10_cycle_preflight(self):
        self.g['c']['deps']=['d']; self.invalid()
    def test_11_unknown_preflight(self):
        self.g['c']['deps']=['missing']; self.invalid()
    def test_12_missing_input_preflight(self):
        self.g['c']['inputs']=['absent']; self.invalid()
    def test_13_duplicate_output_preflight(self):
        self.g['c']['output']='out/../out/b'; self.invalid()
    def test_14_traversal(self):
        self.g['c']['output']='../escape'; self.invalid()
    def test_15_absolute(self):
        self.g['c']['output']=str(self.root/'absolute'); self.invalid()
    def test_16_reserved_manifest(self):
        self.g['c']['output']='.build-state.json'; self.invalid()
    def test_17_input_output_overlap(self):
        self.g['c']['output']='src'; self.invalid()
    def test_18_output_directory(self):
        self.g['c']['output']='.'; self.invalid()
    def test_19_unreachable_invalid(self):
        self.g['z']['deps']=['missing']; self.assertEqual(self.go(), ['a','b','c','d'])
    def test_20_callback_failure_transaction(self):
        self.go(); p=self.root/'.build-state.json'; old=p.read_bytes(); self.g['a']['command']='new'
        def fail(name, command, root):
            if name=='c': raise RuntimeError('boom')
            self.run_node(name,command,root)
        with self.assertRaises(BuildError) as caught: build(self.g,['d'],self.root,fail)
        self.assertIn('c', str(caught.exception)); self.assertIsNotNone(caught.exception.__cause__)
        self.assertEqual(p.read_bytes(),old)
    def test_21_missing_generated_output(self):
        with self.assertRaises(BuildError): build(self.g,['a'],self.root,lambda *args:None)
        self.assertFalse((self.root/'.build-state.json').exists())
    def test_22_corrupt_cache(self):
        (self.root/'.build-state.json').write_text('{bad'); self.assertEqual(self.go(), ['a','b','c','d'])
    def test_23_unknown_schema(self):
        (self.root/'.build-state.json').write_text(json.dumps({'version':999,'records':None}))
        self.assertEqual(self.go(), ['a','b','c','d'])
    def test_24_empty_no_mutation(self):
        self.assertEqual(self.go([]),[]); self.assertFalse((self.root/'.build-state.json').exists())
    def test_25_input_immutable(self):
        before=copy.deepcopy(self.g); targets=['d']; self.go(targets)
        self.assertEqual(self.g,before); self.assertEqual(targets,['d'])
    def test_26_atomic_replace(self):
        original=os.replace; calls=[]
        def spy(src,dst): calls.append((src,dst)); return original(src,dst)
        with patch('os.replace',side_effect=spy): self.go()
        self.assertTrue(any(Path(dst)==self.root/'.build-state.json' for _,dst in calls))
        self.assertFalse(any(Path(src).exists() for src,_ in calls))
    def test_27_dependency_list_change(self):
        self.go(); self.g['d']['deps']=['c','b']; self.assertEqual(self.go(), ['d'])
    def test_28_output_path_change(self):
        self.go(); self.g['b']['output']='out/new-b'; self.assertEqual(self.go(), ['b','d'])
    def test_29_new_target_missing_preflight(self):
        with self.assertRaises(BuildError): self.go(['a','missing'])
        self.assertEqual(self.calls,[])
    def test_30_inputs_list_change(self):
        self.go(); (self.root/'src2').write_text('aaaa'); self.g['a']['inputs']=['src2']
        self.assertEqual(self.go(), ['a','b','c','d'])

if __name__=='__main__': unittest.main(verbosity=2)
