"""Explicit offline release checks. Never run automatically on normal app startup."""
from __future__ import annotations
import base64
import json
from pathlib import Path
import sys
import tempfile
import time

from .paths import is_frozen, resource_root


def backend_check(output, live=False):
    import os
    from .credentials import ENV_NAMES, environment_keys
    from .session import Redactor
    live_keys = environment_keys() if live else {}
    redactor = Redactor([*Redactor.environment().secrets, *live_keys.values()])
    # The opt-in harness supplies keys via a private child environment, not argv.
    # Clear them before spawning any shell; clients receive explicit values only.
    if live:
        for names in ENV_NAMES.values():
            for name in names: os.environ.pop(name, None)
    report = {'frozen': is_frozen(), 'python_bundled': bool(getattr(sys, '_MEIPASS', None))}
    build_info = resource_root() / 'build-info.json'
    if build_info.is_file():
        report['build_info'] = json.loads(build_info.read_text(encoding='utf-8'))
    tools = models = None
    try:
        from .session import Session
        from .models import Models, Settings
        from .tools import Tools
        from mcp_setup import read_config
        from .credentials import CredentialStore
        import os, uuid
        service = 'JevSeek-release-check-' + uuid.uuid4().hex
        vault = CredentialStore(service=service)
        before = dict(os.environ)
        try:
            vault.update({'deepseek': 'offline_vault_test_123456789', 'jev': 'offline_vault_test_987654321'})
            reopened = CredentialStore(service=service)
            report['native_vault_roundtrip'] = reopened.load() == vault.load()
            vault.update({'deepseek': None, 'jev': None})
            report['native_vault_removal'] = reopened.load() == {}
            report['keys_not_exported'] = dict(os.environ) == before
        finally:
            vault._backend.delete_password(service, 'provider-keys-v1')
        with tempfile.TemporaryDirectory(prefix='jevseek-tool-check-') as temp:
            workspace = Path(temp)
            s = Session.create(workspace / 'sessions', workspace, redactor=redactor)
            # Client construction/import coverage only, no request or cost.
            models = Models(s, Settings(), credentials={'deepseek': 'offline_test_not_a_key', 'jev': 'offline_test_not_a_key'})
            tools = Tools(workspace, workspace / 'terminal', {})
            # Verify the new packaged path, with both provider entrypoints blocked.
            # These are argument contracts, not paid model-quality trials.
            generate = models.generate; system_one = models.jev.system_one
            generated = []
            def no_model_io(*args, **kwargs):
                raise AssertionError('Unexpected provider call in offline release check')
            try:
                models.generate = no_model_io; models.jev.system_one = no_model_io
                schema = {'type':'object', 'properties':{'scope':{'const':'workspace'}},
                          'required':['scope'], 'additionalProperties':False}
                report['schema_determined_arguments'] = models.arguments({}, 'mcp.fixed', schema, '') == {'scope':'workspace'}
                def record_generation(stage, messages, schema=None):
                    generated.append({'stage':stage, 'messages':messages, 'schema':schema})
                    return {'path':'fixture.txt'}
                models.generate = record_generation
                state = {'user_intent':'Read fixture.txt'}
                answer = models.arguments(state, 'read', tools.schemas['read'], '')
                report['free_arguments_use_original_generator'] = (answer == {'path':'fixture.txt'}
                    and len(generated) == 1 and generated[0]['stage'] == 'arguments'
                    and generated[0]['schema'] == tools.schemas['read']
                    and json.loads(generated[0]['messages'][1]['content']) == state)
            finally:
                models.generate = generate; models.jev.system_one = system_one
            outcomes = []
            for name, args in [
                ('write', {'path': 'fixture.txt', 'file_text': 'alpha\n'}),
                ('read', {'path': 'fixture.txt'}),
                ('edit', {'path': 'fixture.txt', 'old_str': 'alpha', 'new_str': 'beta'}),
                ('bash', {'command': 'Write-Output (3 * 7)', 'timeout': 10}),
            ]:
                result = tools.execute(name, args)
                outcomes.append({'tool': name, 'ok': not result['is_error'] and result['exit_code'] in (None, 0),
                                 'expected_output': '21' in result['text'] if name == 'bash' else True})
            report['tools'] = outcomes
            report['fixture_edited'] = (workspace / 'fixture.txt').read_text().strip() == 'beta'
            report['mcp_config_empty'] = read_config(workspace / 'missing.json') == {'mcpServers': {}}
            report['ok'] = report['fixture_edited'] and all(r['ok'] and r['expected_output'] for r in outcomes) and all(report[k] for k in ('native_vault_roundtrip','native_vault_removal','keys_not_exported',
                'schema_determined_arguments','free_arguments_use_original_generator'))
            if live:
                if not all(live_keys.values()): raise ValueError('Explicit provider keys are required for --live-check')
                from .agent import Agent
                models.close()
                models = Models(s, Settings.environment(), credentials=live_keys)
                before_fixture = (workspace / 'fixture.txt').read_bytes()
                answer = Agent(s, models, tools).run('Read fixture.txt and report its exact contents. Do not write, edit, run commands, or use MCP. This is a read-only integration check.')
                calls = [e['data']['tool'] for e in s.events if e['kind'] == 'tool_finished']
                report['live'] = {'status': answer['status'], 'summary': answer['summary'], 'tools': calls,
                                  'fixture_unchanged': (workspace / 'fixture.txt').read_bytes() == before_fixture}
                report['ok'] = report['ok'] and answer['status'] == 'completed' and bool(calls) and all(c == 'read' for c in calls) and report['live']['fixture_unchanged']
            tools.close(); tools = None
            models.close(); models = None
    except Exception as exc:
        report.update(ok=False, error=type(exc).__name__, detail=redactor.text(str(exc))[:1500])
    finally:
        if tools is not None: tools.close()
        if models is not None: models.close()
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report.get('ok') else 2


def native_check(window, api, output, runtime):
    report = {'ok': False, 'frozen': is_frozen(), 'bundled_runtime_present': (runtime / 'msedgewebview2.exe').is_file()}
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    def phase(name):
        report['phase'] = name
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    try:
        phase('waiting_for_document')
        if not window.events.loaded.wait(30): raise TimeoutError('Native document load')
        phase('reading_dom')
        for _ in range(120):
            heading = window.evaluate_js("document.querySelector('h1')?.textContent || ''")
            if heading: break
            time.sleep(.25)
        report['ui_rendered'] = 'work on?' in heading
        phase('calling_native_bridge')
        window.evaluate_js('window.pywebview.api.get_key_status().then(r => window.__releaseKeys = r)')
        for _ in range(100):
            keys = window.evaluate_js('window.__releaseKeys || null')
            if keys: break
            time.sleep(.1)
        report['vault_supported'] = bool(keys and keys['ok'] and keys['data']['key_setup']['supported'])
        report['no_inherited_or_bundled_keys'] = not any(keys['data']['providers'].values())
        if is_frozen():
            phase('waiting_for_license_text')
            # React renders the dialog before its bundled text fetch finishes.
            # Wait for actual visible terms, not merely for the main heading.
            deadline = time.monotonic() + 15
            report['terms_shown'] = False
            while time.monotonic() < deadline:
                shown = window.evaluate_js("(() => { const e = document.querySelector('.runtime-license-text'); return Boolean(e && e.getClientRects().length && e.textContent.includes('MICROSOFT SOFTWARE LICENSE TERMS')); })()")
                if shown:
                    report['terms_shown'] = True
                    break
                time.sleep(.1)
        report['no_preview'] = window.evaluate_js("!document.querySelector('.preview-banner')")
        report['no_overflow'] = window.evaluate_js('document.documentElement.scrollWidth <= innerWidth')
        report['local_ui_only'] = window.get_current_url().startswith('http://127.0.0.1:')
        phase('capturing_compositor')
        if sys.platform == 'win32':
            from System import Action
            holder = {}
            def capture():
                core = window.native.webview.CoreWebView2
                holder['version'] = str(core.Environment.BrowserVersionString)
                holder['task'] = core.CallDevToolsProtocolMethodAsync('Page.captureScreenshot', '{"format":"png"}')
            window.native.Invoke(Action(capture))
            report['browser_version'] = holder['version']
            # Never block on Task.Result while holding Python's GIL. WebView2 may
            # need a Python/CLR callback to finish the asynchronous compositor call.
            deadline = time.monotonic() + 10
            while not holder['task'].IsCompleted and time.monotonic() < deadline: time.sleep(.05)
            if holder['task'].IsCompleted:
                png = json.loads(str(holder['task'].Result))['data']
                Path(output).with_suffix('.png').write_bytes(base64.b64decode(png))
                report['screenshot'] = True
            else:
                report['screenshot'] = False
        checks = ['ui_rendered', 'vault_supported', 'no_inherited_or_bundled_keys', 'no_preview', 'no_overflow', 'local_ui_only']
        if is_frozen(): checks += ['bundled_runtime_present', 'terms_shown']
        report['ok'] = all(report.get(k) for k in checks)
        phase('complete')
    except Exception as exc:
        report.update(ok=False, error=type(exc).__name__, detail=str(exc)[:1500])
    finally:
        path = Path(output); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        window.destroy()
