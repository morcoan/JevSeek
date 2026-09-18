"""Native pywebview/WebView2 smoke test in a temporary profile (no model call)."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import webview
from jevseek.desktop import DesktopAPI


def main():
    report = {}
    folder = ROOT / '.jevseek' / 'ui-checks' / f'native-{time.time_ns()}'
    folder.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='jevseek-native-') as temp:
        api = DesktopAPI(temp)
        webview.settings['ALLOW_DOWNLOADS'] = False
        webview.settings['ALLOW_FILE_URLS'] = False
        window = webview.create_window('JevSeek · native validation', str(ROOT / 'frontend' / 'dist' / 'index.html'),
                                       js_api=api, width=1200, height=860, min_size=(360, 500),
                                       text_select=True, zoomable=True, background_color='#FCFAF9')
        api._choose_folder = lambda: [temp]
        window.events.closing += api._request_close

        def probe():
            try:
                if not window.events.loaded.wait(25): raise TimeoutError('Native document did not load')
                for _ in range(80):
                    heading = window.evaluate_js("document.querySelector('h1')?.textContent || ''")
                    if heading: break
                    time.sleep(.25)
                report['heading'] = heading
                window.evaluate_js("window.pywebview.api.bootstrap().then(r => window.__nativeCheck = r)")
                for _ in range(60):
                    result = window.evaluate_js('window.__nativeCheck || null')
                    if result: break
                    time.sleep(.1)
                report['bridge_ok'] = bool(result and result.get('ok') and result['data'].get('desktop'))
                report['empty_profile'] = not result['data']['sessions']
                # Verify argument transport through pywebview's generated decorated methods.
                prefs = {'theme': 'dark', 'workspace': temp, 'use_mcp': False}
                window.evaluate_js('window.pywebview.api.save_preferences(' + json.dumps(prefs) + ').then(r => window.__savedCheck = r)')
                for _ in range(60):
                    saved = window.evaluate_js('window.__savedCheck || null')
                    if saved: break
                    time.sleep(.1)
                report['argument_roundtrip'] = saved.get('ok') and saved['data'] == prefs
                report['font'] = window.evaluate_js("getComputedStyle(document.querySelector('h1')).fontFamily")
                report['no_preview_banner'] = window.evaluate_js("document.querySelector('.preview-banner') === null")
                report['no_overflow'] = window.evaluate_js('document.documentElement.scrollWidth <= innerWidth')
                # Exercise rendered navigation and its real bridge rather than only evaluate API.
                window.evaluate_js("[...document.querySelectorAll('button')].find(e => e.textContent.includes('Settings')).click()")
                time.sleep(.6)
                report['settings_rendered'] = window.evaluate_js("document.querySelector('h1')?.textContent === 'Settings'")
                try:
                    if sys.platform == 'win32':
                        # Capture the WebView2 compositor; desktop grabs can be black in a locked/RDP session.
                        from System import Action
                        holder = {}
                        def capture():
                            holder['task'] = window.native.webview.CoreWebView2.CallDevToolsProtocolMethodAsync('Page.captureScreenshot', '{"format":"png"}')
                        window.native.Invoke(Action(capture))
                        deadline = time.monotonic() + 10
                        while not holder['task'].IsCompleted and time.monotonic() < deadline: time.sleep(.05)
                        if not holder['task'].IsCompleted: raise TimeoutError('Compositor capture did not finish')
                        image = json.loads(str(holder['task'].Result))['data']
                        (folder / 'native-window.png').write_bytes(base64.b64decode(image))
                        report['screenshot'] = str(folder / 'native-window.png')
                except Exception as exc:
                    report['screenshot_error'] = type(exc).__name__
            except Exception as exc:
                report['error'] = f'{type(exc).__name__}: {exc}'
            finally:
                (folder / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
                window.destroy()

        webview.start(probe, gui='edgechromium' if sys.platform == 'win32' else None, http_server=True, private_mode=True)
    print(json.dumps(report, indent=2))
    return 0 if all(report.get(k) for k in ('heading', 'bridge_ok', 'empty_profile', 'argument_roundtrip', 'no_preview_banner', 'no_overflow', 'settings_rendered')) else 1


if __name__ == '__main__': raise SystemExit(main())
