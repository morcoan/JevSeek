"""OPT-IN paid-provider smoke: send one read-only task through React + DesktopAPI.
Run with --run to consent to provider calls. No mocked model or tool implementations.
Only the disposable fixture workspace is requested; tools are NOT sandboxed.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
from jevseek.desktop import DesktopAPI
from playwright.sync_api import sync_playwright, expect


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Explicitly allow one real model/API-backed UI task')
    if not parser.parse_args().run: parser.error('Pass --run to explicitly allow provider calls.')
    load_dotenv(ROOT / '.env')
    folder = ROOT / '.jevseek' / 'ui-live' / str(time.time_ns())
    workspace = folder / 'workspace'; workspace.mkdir(parents=True)
    fixture = workspace / 'hello.py'
    fixture.write_text('APP_NAME = "JevSeek desktop bridge verified"\n', encoding='utf-8')
    before = hashlib.sha256(fixture.read_bytes()).hexdigest()
    api = DesktopAPI(folder, workspace=workspace)
    api.save_preferences({'theme': 'light', 'workspace': str(workspace), 'use_mcp': False})
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / 'frontend' / 'dist')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    report = {'evidence_dir': str(folder)}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            methods = ['bootstrap', 'list_sessions', 'get_session', 'poll', 'save_preferences', 'choose_workspace', 'start_run', 'cancel_run', 'compact_session', 'list_artifacts', 'read_artifact', 'open_external']
            page.expose_function('__localBridge', lambda method, args: getattr(api, method)(*args))
            page.add_init_script('window.pywebview = {api: Object.fromEntries(' + json.dumps(methods) + '.map(name => [name, (...args) => window.__localBridge(name, args)]))};')
            page.goto(f'http://127.0.0.1:{server.server_port}')
            expect(page.get_by_role('heading', name='What would you like to work on?')).to_be_visible()
            page.get_by_role('textbox', name='Message JevSeek').fill('Read hello.py in the workspace and tell me the exact value of APP_NAME. Do not write or edit any files, run shell commands, or use MCP.')
            start = time.monotonic()
            page.get_by_role('button', name='Send message', exact=True).click()
            while time.monotonic() - start < 180:
                page.wait_for_timeout(500)
                response = api.poll(0)['data']
                result = next((e['data'] for e in reversed(response['events']) if e['kind'] == 'result'), None)
                if result and not response['active']: break
            else:
                api.cancel_run()
                raise TimeoutError('Provider-backed UI task did not finish within 180 seconds; cooperative stop requested.')
            report.update({'status': result['status'], 'session_id': result['session_id'], 'summary': result['summary'], 'seconds': round(time.monotonic() - start, 2)})
            snapshot = api.get_session(result['session_id'])['data']
            calls = [e['data'] for e in snapshot['events'] if e['kind'] == 'tool_finished']
            report['tools'] = [{'tool': c['tool'], 'status': c['status']} for c in calls]
            report['fixture_unchanged'] = hashlib.sha256(fixture.read_bytes()).hexdigest() == before
            report['read_only'] = bool(calls) and all(c['tool'] == 'read' for c in calls)
            expect(page.locator('.markdown')).to_contain_text('JevSeek desktop bridge verified', timeout=10000)
            page.screenshot(path=str(folder / 'live-conversation.png'))
            # Reload and open the finished session: no additional model/tool work.
            saved_count = len(snapshot['events'])
            page.reload()
            page.locator('.history-item').first.click()
            expect(page.locator('.markdown')).to_contain_text('JevSeek desktop bridge verified')
            page.wait_for_timeout(700)
            report['offline_reopen_no_replay'] = len(api.get_session(result['session_id'])['data']['events']) == saved_count and api.poll(0)['data']['active'] is None
            browser.close()
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: live UI assertion failed; inspect local evidence.'
    finally:
        server.shutdown()
        if api._thread and api._thread.is_alive():
            api.cancel_run(); api._thread.join(60)
        (folder / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report.get('status') == 'completed' and all(report.get(k) for k in ('fixture_unchanged', 'read_only', 'offline_reopen_no_replay')) and 'error' not in report else 1


if __name__ == '__main__': raise SystemExit(main())
