"""Isolated key-setup UI regression. Fake keys/test vault only; no provider calls."""
from __future__ import annotations
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jevseek.credentials import CredentialStore, ENV_NAMES
from jevseek.desktop import DesktopAPI
from test_credentials import MemoryVault
from playwright.sync_api import sync_playwright, expect


def main():
    for names in ENV_NAMES.values():
        for name in names: os.environ.pop(name, None)
    output = ROOT / '.jevseek' / 'key-ui-checks' / str(time.time_ns()); output.mkdir(parents=True)
    violations = []; errors = []
    ds = 'ui_test_deepseek_123456789'; jev = 'ui_test_jev_123456789'
    with tempfile.TemporaryDirectory(prefix='jevseek-key-ui-') as temp:
        vault = MemoryVault(); api = DesktopAPI(temp, credentials=CredentialStore(vault), require_runtime_terms=True)
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT / 'frontend' / 'dist')))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(); page = browser.new_page(viewport={'width': 1200, 'height': 900})
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
                methods = ['bootstrap', 'poll', 'list_sessions', 'get_session', 'save_preferences', 'save_keys', 'remove_key', 'get_key_status', 'open_external', 'accept_runtime_terms', 'close_app']
                page.expose_function('__keyTestBridge', lambda name, args: getattr(api, name)(*args))
                page.add_init_script('window.pywebview={api:Object.fromEntries(' + json.dumps(methods) + '.map(n=>[n,(...a)=>window.__keyTestBridge(n,a)]))};')
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.get_by_role('dialog', name='Microsoft runtime terms')).to_be_visible()
                expect(page.get_by_role('button', name='Agree & continue')).to_be_disabled()
                def audit(name):
                    page.screenshot(path=str(output / (name + '.png')))
                    page.evaluate((ROOT / 'frontend' / 'node_modules' / 'axe-core' / 'axe.min.js').read_text(encoding='utf-8'))
                    result = page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))")
                    violations.extend({'screen': name, **v} for v in result)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                expect(page.locator('.runtime-license-text')).to_contain_text('MICROSOFT SOFTWARE LICENSE TERMS')
                audit('runtime-terms-light')
                page.get_by_role('checkbox').check()
                page.get_by_role('button', name='Agree & continue').click()
                expect(page.get_by_role('dialog', name='Connect your providers')).to_be_visible()
                expect(page.get_by_role('button', name='Save keys securely')).to_be_disabled()
                audit('first-run-light')
                page.get_by_role('button', name='Set up later').click()
                page.get_by_role('textbox', name='Message JevSeek').fill('Retain this draft while I set up keys')
                page.get_by_role('button', name='Send message', exact=True).click()
                expect(page.get_by_role('dialog')).to_be_visible()
                page.get_by_label('DeepSeek API key', exact=True).fill(ds)
                page.get_by_label('TypeSafe / Jev API key', exact=True).fill(jev)
                expect(page.get_by_label('DeepSeek API key', exact=True)).to_have_attribute('type', 'password')
                page.get_by_role('button', name='Save keys securely').click()
                expect(page.get_by_text('Saved securely.', exact=False)).to_be_visible()
                expect(page.get_by_label('DeepSeek API key', exact=True)).to_have_value('')
                expect(page.get_by_label('TypeSafe / Jev API key', exact=True)).to_have_value('')
                assert vault.value and ds in vault.value and jev in vault.value
                assert not any(ds.encode() in f.read_bytes() for f in Path(temp).rglob('*') if f.is_file())
                assert page.evaluate('localStorage.length === 0 && sessionStorage.length === 0')
                assert not page.evaluate('(key)=>document.documentElement.outerHTML.includes(key)', ds)
                audit('keys-saved-light')
                page.get_by_role('button', name='Remove saved DeepSeek key').click()
                page.get_by_role('button', name='Keep key').click()
                assert api.get_key_status()['data']['providers']['deepseek']
                page.get_by_role('button', name='Remove saved DeepSeek key').click()
                page.get_by_role('button', name='Remove saved key', exact=True).click()
                expect(page.get_by_text('Saved key removed.', exact=True)).to_be_visible()
                assert not api.get_key_status()['data']['providers']['deepseek']
                assert api.get_key_status()['data']['providers']['jev']
                vault.fail = True
                page.get_by_label('DeepSeek API key', exact=True).fill(ds)
                page.get_by_role('button', name='Save keys securely').click()
                expect(page.get_by_role('alert')).to_contain_text('Could not save')
                expect(page.get_by_label('DeepSeek API key', exact=True)).to_have_value('')
                audit('vault-error-light')
                page.set_viewport_size({'width': 360, 'height': 800})
                page.evaluate("document.documentElement.dataset.theme='dark'")
                audit('keys-mobile-dark')
                page.keyboard.press('Escape')
                expect(page.get_by_role('textbox', name='Message JevSeek')).to_have_value('Retain this draft while I set up keys')
                browser.close()
        finally: server.shutdown()
    report = {'screens': 5, 'axe_violations': violations, 'console_errors': errors, 'plaintext_project_or_browser_storage': False, 'draft_retained': True}
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'evidence': str(output), **report}, indent=2))
    return 1 if violations or errors else 0


if __name__ == '__main__': raise SystemExit(main())
