"""Diagnose the exact cached Fixed WebView2 runtime before packaging."""
from pathlib import Path
import faulthandler
import json
import os
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import webview
from jevseek.desktop import DesktopAPI
from jevseek.credentials import CredentialStore
from jevseek.packaged_checks import native_check
from test_credentials import MemoryVault

folder = ROOT / '.jevseek' / 'fixed-runtime-checks' / str(time.time_ns()); folder.mkdir(parents=True)
trace = (folder / 'threads.txt').open('w')
faulthandler.enable(file=trace)
faulthandler.dump_traceback_later(40, file=trace)
version = json.loads((ROOT / 'packaging' / 'webview2.json').read_text())['version']
runtime = ROOT / '.build-cache' / 'webview2' / version
with tempfile.TemporaryDirectory() as temp:
    api = DesktopAPI(temp, credentials=CredentialStore(MemoryVault()))
    webview.settings['WEBVIEW2_RUNTIME_PATH'] = str(runtime)
    window = webview.create_window('Fixed runtime validation', str(ROOT / 'frontend' / 'dist' / 'index.html'), js_api=api, width=1200, height=860)
    print('Evidence:', folder, flush=True)
    done = threading.Event()
    def probe():
        try: native_check(window, api, folder / 'report.json', runtime)
        finally: done.set()
    def watchdog():
        if not done.wait(85):
            print('Fixed runtime watchdog timed out', flush=True)
            os._exit(2)
    threading.Thread(target=watchdog, daemon=True).start()
    webview.start(probe, gui='edgechromium', http_server=True)
print((folder / 'report.json').read_text())
