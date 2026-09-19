"""Run the actual EXE with no Python/Node on PATH, from an unrelated folder.

Offline: real native SDK file/shell tools + real bundled browser + bundled MCP
helper. No API keys or model requests. The app is not an OS sandbox.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import psutil

ROOT = Path(__file__).resolve().parents[1]


def stop_tree(process):
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in reversed(children):
            try: child.kill()
            except psutil.Error: pass
        parent.kill()
    except psutil.Error: pass
    process.wait(timeout=15)


def isolated_environment(profile):
    env = {k:v for k,v in os.environ.items() if not any(w in k.upper() for w in ('KEY','TOKEN','SECRET','PASSWORD'))
           and not k.startswith(('PYTHON','PI_','WEBVIEW2','_PYI')) and k not in ('VIRTUAL_ENV','CONDA_PREFIX','JEV_KET')}
    windows = Path(os.environ.get('SystemRoot', 'C:/Windows'))
    env.update(PATH=os.pathsep.join(map(str, [windows/'System32', windows/'System32/WindowsPowerShell/v1.0', windows])),
               JEVSEEK_DATA_DIR=str(profile), PYINSTALLER_RESET_ENVIRONMENT='1')
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, default=ROOT/'release'/'JevSeek.exe')
    args = parser.parse_args()
    out = ROOT/'.jevseek'/'release-checks'/str(time.time_ns()); out.mkdir(parents=True)
    isolated = out/'exe-only'; isolated.mkdir()
    exe = isolated/'JevSeek.exe'; shutil.copy2(args.exe, exe)
    # These adjacent files must never become release configuration.
    (isolated/'.env').write_text('DS_KEY=adjacent_test_value_123456789\nJEV_KET=adjacent_test_value_987654321\n')
    (isolated/'mcp.json').write_text('invalid adjacent config must not be read')
    env = isolated_environment(out/'profile')
    results = {}; processes = []
    for mode in ('self-test','smoke-test'):
        report = out/(mode+'.json')
        process = subprocess.Popen([str(exe), '--'+mode, str(report)], cwd=isolated, env=env)
        processes.append((mode, process, report))
    for mode, process, report in processes:
        try:
            code = process.wait(timeout=150)
            results[mode] = {'exit': code, 'report': json.loads(report.read_text()) if report.exists() else {'ok':False,'error':'No report'}}
        except subprocess.TimeoutExpired:
            stop_tree(process)
            results[mode] = {'exit': -1, 'report': {'ok':False,'error':'Timed out; diagnostic tree stopped'}}
    mcp_output = out/'mcp-result.txt'
    process = subprocess.Popen([str(exe),'--mcp-output',str(mcp_output),'--mcp','list'],cwd=isolated,env=env)
    try:
        code = process.wait(timeout=90)
        results['mcp-helper'] = {'exit':code,'ok':code==0 and mcp_output.exists() and not mcp_output.read_text().strip()}
    except subprocess.TimeoutExpired:
        stop_tree(process); results['mcp-helper'] = {'exit':-1,'ok':False}
    backend = results['self-test']['report']; native = results['smoke-test']['report']
    expected = json.loads((ROOT/'release'/'build-info.json').read_text(encoding='utf-8'))
    results['package_identity'] = (backend.get('build_info') == expected
                                   and backend.get('frozen') and backend.get('python_bundled')
                                   and native.get('frozen') and native.get('bundled_runtime_present'))
    results['ok'] = (all(results[m]['exit']==0 and results[m]['report'].get('ok') for m in ('self-test','smoke-test'))
                     and results['mcp-helper']['ok'] and results['package_identity'])
    results['environment'] = 'Windows/PowerShell-only PATH; no provider keys, PYTHONHOME or PYTHONPATH; EXE copied outside source'
    (out/'report.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps({'evidence':str(out),**results},indent=2))
    # Do not retain duplicate400MB binaries per validation run. Reports/screenshots remain.
    exe.unlink(missing_ok=True)
    return 0 if results['ok'] else 1


if __name__=='__main__': raise SystemExit(main())
