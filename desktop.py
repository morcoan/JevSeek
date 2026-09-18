"""JevSeek desktop entry point, from source or a standalone Windows executable."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile

from jevseek.paths import default_workspace, is_frozen, resource_root, state_home

PROJECT = resource_root()


def _message(text):
    if is_frozen() and sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, 'JevSeek', 0x10)
    else:
        print(text, file=sys.stderr)


def _mcp_command(argv, output):
    """A windowless EXE reports helper results to a caller-chosen local file."""
    if output is None:
        _message('Use --mcp-output FILE with --mcp. The helper writes its result to that file.')
        return 2
    stream = io.StringIO()
    code = 0
    try:
        from mcp_setup import main as mcp_main
        with redirect_stdout(stream): mcp_main(argv)
    except BaseException as exc:
        code = 2
        stream = io.StringIO(f'MCP setup failed ({type(exc).__name__}). Check configuration and server availability.\n')
    from jevseek.session import Redactor
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(Redactor.environment().text(stream.getvalue()), encoding='utf-8')
    return code


def main(argv=None):
    # Windowless Python has no stdout/stderr. SDK loggers still expect file objects;
    # send diagnostics to the null device, not a shareable secret-bearing log.
    if sys.stdout is None: sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None: sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    os.environ.setdefault('OPENHANDS_SUPPRESS_BANNER', '1')
    os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP', 'True')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, help='Initial workspace; saved preferences take precedence')
    parser.add_argument('--sessions-dir', type=Path, help='Alternate local session storage')
    parser.add_argument('--debug', action='store_true', help='Source development only')
    parser.add_argument('--mcp-output', type=Path, help='Write a --mcp command result to this local file')
    parser.add_argument('--mcp', nargs=argparse.REMAINDER, help='Run the bundled MCP configuration helper, not the GUI')
    parser.add_argument('--self-test', type=Path, metavar='REPORT', help='Offline packaged SDK/tool smoke; write JSON report')
    parser.add_argument('--live-check', action='store_true', help='With --self-test only: opt-in billable read-only provider check using supplied environment keys')
    parser.add_argument('--smoke-test', type=Path, metavar='REPORT', help='Open/check/close native UI in a disposable profile')
    args = parser.parse_args(argv)
    if args.mcp is not None: return _mcp_command(args.mcp, args.mcp_output)
    if args.self_test:
        from jevseek.packaged_checks import backend_check
        return backend_check(args.self_test, live=args.live_check)
    if args.live_check: parser.error('--live-check requires --self-test REPORT')
    if args.debug and is_frozen():
        _message('Developer tools are disabled in the release EXE. Use a source checkout for development.')
        return 2
    index = PROJECT / 'frontend' / 'dist' / 'index.html'
    if not index.is_file():
        _message('Frontend missing. Source: cd frontend && npm ci && npm run build. Release: download a complete JevSeek build.')
        return 2
    try:
        import webview
        from dotenv import load_dotenv
        from jevseek.desktop import DesktopAPI
        from jevseek.credentials import CredentialStore
        # Never load an adjacent/CWD .env in the distributable or read builder secrets.
        if not is_frozen() and not args.smoke_test: load_dotenv(PROJECT / '.env')
        data = state_home()
        temp_profile = tempfile.TemporaryDirectory(prefix='jevseek-native-check-') if args.smoke_test else None
        if temp_profile:
            data = Path(temp_profile.name)
            workspace = data / 'workspace'; workspace.mkdir()
            import uuid
            credentials = CredentialStore(service='JevSeek-smoke-' + uuid.uuid4().hex)
        else:
            workspace = args.workspace or default_workspace()
            credentials = CredentialStore()
        api = DesktopAPI(PROJECT, args.sessions_dir, workspace, state_dir=data, credentials=credentials, require_runtime_terms=is_frozen())
        webview.settings['ALLOW_DOWNLOADS'] = False
        webview.settings['ALLOW_FILE_URLS'] = False
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True
        runtime = PROJECT / 'webview2'
        if is_frozen():
            if not (runtime / 'msedgewebview2.exe').is_file():
                raise RuntimeError('Bundled WebView2 runtime is missing')
            webview.settings['WEBVIEW2_RUNTIME_PATH'] = str(runtime)
            if sys.getwindowsversion().build < 22000:
                # Microsoft requires these read/execute-only AppContainer ACLs for
                # Fixed Runtime120+ on Windows10. Never grant access to user state.
                import subprocess
                command = [str(Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32' / 'icacls.exe'), str(runtime),
                           '/grant', '*S-1-15-2-1:(OI)(CI)(RX)', '/grant', '*S-1-15-2-2:(OI)(CI)(RX)', '/T', '/C']
                subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        window = webview.create_window('JevSeek', str(index), js_api=api, width=1200, height=860,
                                      min_size=(360, 500), background_color='#FCFAF9',
                                      text_select=True, zoomable=True)
        if window is None: raise RuntimeError('Window could not be created')
        api._choose_folder = lambda: window.create_file_dialog(webview.FileDialog.FOLDER)
        api._close_window = window.destroy
        window.events.closing += api._request_close
        probe = None
        if args.smoke_test:
            from jevseek.packaged_checks import native_check
            probe = lambda: native_check(window, api, args.smoke_test, runtime)
        try:
            webview.start(probe, gui='edgechromium' if sys.platform == 'win32' else None,
                          debug=args.debug, http_server=True, private_mode=True)
        finally:
            if temp_profile: temp_profile.cleanup()
        if args.smoke_test:
            return 0 if json.loads(args.smoke_test.read_text())['ok'] else 2
    except Exception as exc:
        if args.smoke_test:
            args.smoke_test.parent.mkdir(parents=True, exist_ok=True)
            args.smoke_test.write_text(json.dumps({'ok': False, 'error': type(exc).__name__}))
        else:
            _message(f'{type(exc).__name__}: the desktop engine could not start. Use a complete Windows x64 release on Windows 10/11, or see docs/DESKTOP.md for source setup.')
        return 2
    return 0


if __name__ == '__main__':
    multiprocessing.freeze_support()
    raise SystemExit(main())
