"""Offline browser integration/visual checks. Fixtures exist ONLY in a temp profile.
Requires: pip install playwright; python -m playwright install chromium
Build frontend first. Does not contact providers or modify production sessions.
"""
from __future__ import annotations

import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jevseek.desktop import DesktopAPI
from jevseek.session import Session
from playwright.sync_api import sync_playwright, expect

OUT = ROOT / '.jevseek' / 'ui-checks' / str(time.time_ns())
OUT.mkdir(parents=True, exist_ok=True)
print(f'Evidence: {OUT}', flush=True)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass


def fixture_runner(session, prompt, acknowledge, use_mcp, cancel):
    """Transport fixture, NOT a model response or test of agent quality."""
    with session.lock:
        session.reload()
        if acknowledge: session.acknowledge_pending()
        if prompt: session.append('user', text=prompt)
        session.append('run_started', model='deepseek-flash', thinking='disabled')
        session.append('model_started', stage='router', model='jev-1.13.0')
        if prompt and 'wait' in prompt.lower():
            cancel.wait(15)
            session.append('error', stage='cancelled', error='Cancelled between calls')
            return {'session_id': session.id, 'status': 'cancelled', 'summary': 'Stopped. The session was saved.'}
        time.sleep(.8)
        request, _ = session.artifact('example-request', {'path': 'src/engine.py'}, {'text': ''})
        session.append('tool_started', call_id='example', tool='read', target='src/engine.py', request=request)
        artifact, output = session.artifact('example', {'path': 'src/engine.py'}, {'text': 'def build(target):\n    return target.resolve()\n'})
        session.append('tool_finished', call_id='example', tool='read', target='src/engine.py', status='ok', exit_code=None, text='def build(target):\n    return target.resolve()\n', artifact=artifact, full_output=output)
        summary = 'The entry point is in `src/engine.py`. It resolves the requested target before building.\n\n### A good place to start\n\n- Follow `build(target)` to understand how the project fits together.\n- Add coverage for missing targets before changing the behavior.\n\n```python\ndef build(target):\n    return target.resolve()\n```\n\nThis is an **offline UI test fixture**. No model ran and no workspace files were changed.'
        session.append('final', status='completed', summary=summary)
        return {'session_id': session.id, 'status': 'completed', 'summary': summary}


def main():
    reports = []
    console_errors = []
    with tempfile.TemporaryDirectory(prefix='jevseek-ui-') as temp:
        project = Path(temp); workspace = project / 'my-project'; workspace.mkdir()
        api = DesktopAPI(project, workspace=workspace, runner=fixture_runner)
        api._choose_folder = lambda: [str(workspace)]
        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / 'frontend' / 'dist')))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1280, 'height': 900}, reduced_motion='reduce')
            page.on('pageerror', lambda e: console_errors.append(str(e)))
            page.on('console', lambda m: console_errors.append(m.text) if m.type == 'error' else None)
            methods = ['bootstrap', 'list_sessions', 'get_session', 'poll', 'save_preferences', 'choose_workspace', 'start_run', 'cancel_run', 'compact_session', 'list_artifacts', 'read_artifact', 'open_external']
            page.expose_function('__fixtureBridge', lambda method, args: getattr(api, method)(*args))
            page.add_init_script('window.pywebview = {api: Object.fromEntries(' + json.dumps(methods) + '.map(name => [name, (...args) => window.__fixtureBridge(name, args)]))};')
            page.goto(f'http://127.0.0.1:{server.server_port}')
            expect(page.get_by_role('heading', name='What would you like to work on?')).to_be_visible()
            page.evaluate('document.fonts.ready')

            def capture(name, axe=True):
                page.screenshot(path=str(OUT / f'{name}.png'), full_page=True)
                overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth')
                if overflow: raise AssertionError(f'Horizontal page overflow: {name}')
                if axe:
                    page.evaluate((ROOT / 'frontend' / 'node_modules' / 'axe-core' / 'axe.min.js').read_text(encoding='utf-8'))
                    result = page.evaluate("async () => (await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v => ({id:v.id, impact:v.impact, nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))")
                    reports.append({'screen': name, 'violations': result})
                    (OUT / 'report.json').write_text(json.dumps({'screens': reports, 'console_errors': console_errors}, indent=2), encoding='utf-8')

            capture('welcome-light')
            expect(page.get_by_role('button', name='Send message', exact=True)).to_be_disabled()
            page.get_by_role('button', name='Explore a project').click()
            draft = page.get_by_role('textbox', name='Message JevSeek').input_value()
            page.get_by_role('button', name='Settings', exact=False).first.click()
            expect(page.get_by_role('heading', name='Settings', exact=True)).to_be_visible()
            capture('settings-light')
            page.get_by_role('textbox', name='Default workspace folder').fill(str(workspace / 'missing'))
            page.get_by_role('button', name='Save folder').click()
            expect(page.get_by_role('alert')).to_contain_text('existing workspace')
            page.get_by_role('button', name='Dismiss error').click()
            expect(page.get_by_role('textbox', name='Default workspace folder')).to_have_value(str(workspace))
            page.get_by_role('radio', name='Dark').check()
            expect(page.get_by_role('radio', name='Dark')).to_be_enabled()
            expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
            capture('settings-dark')
            page.get_by_role('button', name='Conversation', exact=True).click()
            expect(page.get_by_role('textbox', name='Message JevSeek')).to_have_value(draft)
            capture('welcome-dark')
            page.get_by_role('button', name='Send message', exact=True).click()
            expect(page.get_by_text('offline UI test fixture', exact=False)).to_be_visible(timeout=20000)
            expect(page.get_by_role('textbox', name='Message JevSeek')).to_have_value('')
            activity_toggle = page.get_by_role('button', name='Workspace activity')
            if activity_toggle.get_attribute('aria-expanded') != 'true': activity_toggle.click()
            capture('conversation-dark')
            page.get_by_role('button', name='Reading a file').click()
            expect(page.get_by_text('Recorded preview.', exact=False)).to_be_visible()
            # Do not drag the viewport away from someone reading earlier output.
            page.locator('.content-scroll').evaluate('(el) => { el.scrollTop = 0; }')
            page.wait_for_timeout(100)
            first_session = api.list_sessions()['data']['sessions'][0]['session_id']
            api._transient(first_session, 'model_progress', {'stage': 'arguments', 'characters': 12})
            page.wait_for_timeout(700)
            assert page.locator('.content-scroll').evaluate('(el) => el.scrollTop') == 0
            page.get_by_label('Conversation options').click()
            page.get_by_role('button', name='Compact history').click()
            expect(page.get_by_text('Factual history compacted locally. No model or tool ran.', exact=True)).to_be_visible()
            saved = api.get_session(first_session)['data']['events']
            assert sum(e['kind'] == 'compaction' for e in saved) == 2
            assert sum(e['kind'] == 'tool_finished' for e in saved) == 1
            page.get_by_label('Conversation options').click()
            page.get_by_role('button', name='Files', exact=True).click()
            expect(page.get_by_role('button', name='Tool output', exact=False)).to_be_visible()
            capture('files-dark')
            page.get_by_role('button', name='Tool output', exact=False).click()
            expect(page.get_by_role('dialog')).to_be_visible()
            capture('artifact-dark')
            page.keyboard.press('Escape')
            expect(page.get_by_role('dialog')).not_to_be_visible()
            page.get_by_role('button', name='Activity', exact=True).click()
            expect(page.locator('.activity-item')).to_have_count(1)
            capture('activity-dark')
            page.locator('.activity-item').click()
            expect(page.get_by_role('button', name='All conversations')).to_be_visible()
            capture('activity-detail-dark')
            page.get_by_role('button', name='Open conversation').click()
            page.get_by_role('textbox', name='Message JevSeek').fill('Please wait so I can test cooperative stop.')
            page.get_by_role('button', name='Send message', exact=True).click()
            expect(page.get_by_role('button', name='Stop agent', exact=True)).to_be_visible()
            capture('running-dark')
            page.get_by_role('button', name='Stop agent', exact=True).click()
            expect(page.get_by_role('button', name='Resume run')).to_be_visible(timeout=10000)
            capture('stopped-dark')
            # Seed a separate, explicitly interrupted log. The UI must never auto-replay it.
            s = Session.create(project / '.jevseek' / 'sessions', workspace)
            s.append('user', text='Interrupted tool fixture')
            s.append('tool_started', call_id='interrupted', tool='bash', target='python checks.py')
            page.reload()
            page.get_by_role('button', name='Interrupted tool fixture', exact=True).click()
            expect(page.get_by_text('An interrupted tool needs your review')).to_be_visible()
            capture('interrupted-dark')
            page.get_by_role('textbox', name='Message JevSeek').fill('I inspected the files; continue read-only.')
            page.get_by_role('button', name='Send message', exact=True).click()
            expect(page.get_by_role('dialog')).to_be_visible()
            expect(page.get_by_role('button', name='Close dialog')).to_be_focused()
            page.keyboard.press('Shift+Tab')
            assert page.evaluate("document.activeElement.closest('dialog') !== null")
            expect(page.get_by_role('button', name='Acknowledge & send')).to_be_disabled()
            capture('review-dialog-dark')
            page.get_by_role('checkbox').check()
            page.get_by_role('button', name='Acknowledge & send').click()
            expect(page.get_by_text('offline UI test fixture', exact=False)).to_be_visible(timeout=10000)
            # Responsive drawer, drafts, focus, table/code overflow and theme at 360px.
            page.set_viewport_size({'width': 360, 'height': 800})
            page.get_by_role('textbox', name='Message JevSeek').fill('Keep this unsent draft')
            capture('conversation-mobile-dark')
            page.get_by_role('button', name='Open navigation').click()
            expect(page.get_by_role('button', name='New conversation')).to_be_visible()
            capture('navigation-mobile-dark')
            page.keyboard.press('Shift+Tab')
            assert page.evaluate("document.activeElement.closest('.sidebar') !== null")
            page.get_by_role('button', name='Settings', exact=False).first.click()
            page.get_by_role('radio', name='Light').check()
            expect(page.get_by_role('radio', name='Light')).to_be_enabled()
            capture('settings-mobile-light')
            page.get_by_role('button', name='Open navigation').click()
            page.get_by_role('button', name='Conversation', exact=True).click()
            expect(page.get_by_role('textbox', name='Message JevSeek')).to_have_value('Keep this unsent draft')
            capture('conversation-mobile-light')
            page.get_by_role('button', name='Open navigation').click()
            page.get_by_role('button', name='New conversation').click()
            capture('welcome-mobile-light')
            # 200% effective desktop zoom: CSS viewport halves, content must reflow.
            page.set_viewport_size({'width': 640, 'height': 450})
            capture('zoom-200-light')
            # No runtime bridge: honestly disclosed, no fabricated activity or active send.
            preview = browser.new_page(viewport={'width': 1280, 'height': 900})
            preview.goto(f'http://127.0.0.1:{server.server_port}')
            expect(preview.get_by_text('Browser preview', exact=True)).to_be_visible(timeout=10000)
            expect(preview.get_by_role('button', name='Send message', exact=True)).to_be_disabled()
            preview.close()
            browser.close()
        server.shutdown()
    evidence = {'screens': reports, 'console_errors': console_errors}
    (OUT / 'report.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    failures = [(r['screen'], v['id'], v['nodes']) for r in reports for v in r['violations']]
    print(json.dumps({'screens': len(reports), 'axe_violations': len(failures), 'console_errors': console_errors, 'failures': failures}, indent=2))
    return 1 if failures or console_errors else 0


if __name__ == '__main__': raise SystemExit(main())
