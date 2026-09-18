import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from mcp_setup import update, read_config, load_servers

class MCPConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'mcp.json'
    def test_empty(self):
        self.assertEqual(load_servers(self.path),{})
    def test_merge_replace_remove(self):
        update('one',{'url':'http://localhost:9765/mcp','transport':'http'},self.path)
        update('two',{'command':'python','args':['server.py'],'transport':'stdio'},self.path)
        update('one',{'url':'http://localhost:9766/mcp','transport':'http'},self.path)
        self.assertEqual(len(read_config(self.path)['mcpServers']),2)
        update('one',None,self.path)
        self.assertEqual(list(load_servers(self.path)),['two'])
    def test_case_insensitive_registration_and_removal(self):
        update('blender',{'url':'http://localhost:9765/mcp'},self.path)
        update('Blender',{'url':'http://localhost:9765/mcp'},self.path)
        self.assertEqual(list(read_config(self.path)['mcpServers']),['blender'])
        update('BLENDER',None,self.path)
        self.assertEqual(load_servers(self.path),{})
    def test_invalid_atomic(self):
        update('ok',{'url':'http://localhost/mcp'},self.path)
        original=self.path.read_bytes()
        with self.assertRaises(ValueError): update('bad',{'url':'ftp://host/x'},self.path)
        self.assertEqual(self.path.read_bytes(),original)
        self.assertEqual(list(self.path.parent.glob('.mcp-*')),[])
    def test_environment_not_persisted(self):
        update('one',{'url':'http://localhost/mcp','headers':{'Authorization':'Bearer ${MCP_TEST_TOKEN}'}},self.path)
        with patch.dict(os.environ,{'MCP_TEST_TOKEN':'example-secret'}):
            self.assertEqual(load_servers(self.path)['one'].headers['Authorization'].get_secret_value(),'Bearer example-secret')
        self.assertNotIn('example-secret',self.path.read_text())
    def test_missing_env(self):
        update('one',{'command':'python','env':{'TOKEN':'${MCP_TEST_ABSENT}'}},self.path)
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError): load_servers(self.path)
    def test_disabled(self):
        update('one',{'command':'python','enabled':False,'env':{'TOKEN':'${MCP_TEST_ABSENT}'}},self.path)
        self.assertEqual(load_servers(self.path),{})
    def test_invalid_json_preserved(self):
        self.path.write_text('{broken')
        with self.assertRaises(json.JSONDecodeError): update('one',{'command':'python'},self.path)
        self.assertEqual(self.path.read_text(),'{broken')
    def test_exclusive_transport(self):
        with self.assertRaises(ValueError): update('one',{'url':'http://localhost','command':'python'},self.path)
        self.assertFalse(self.path.exists())

if __name__=='__main__': unittest.main()
