"""Opt-in Windows EXE Bonsai/native integration, no cloud requests.

Uses local CDP only in the test child's environment. Reuses the previously
validated CRACK GGUF and runtime cache; never opens a debugging port normally.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    if not args.run: parser.error('Pass --run to launch the EXE and load the local 27B model.')
    from jevseek.bonsai import isolated_environment
    import httpx
    import psutil
    from playwright.sync_api import sync_playwright, expect
    output=ROOT/'.jevseek'/'bonsai-frozen'/str(time.time_ns());output.mkdir(parents=True)
    exe=output/'JevSeek.exe';os.link(ROOT/'release'/'JevSeek.exe',exe)
    profile=output/'profile';(profile/'bonsai').mkdir(parents=True)
    runtime=ROOT/'.jevseek'/'bonsai-validation'/'bonsai'/'runtime-cuda'
    if not runtime.is_dir():raise SystemExit('First run the source Bonsai integration to validate/cache runtime files.')
    shutil.copytree(runtime,profile/'bonsai'/'runtime-cuda',copy_function=os.link)
    with socket.socket() as sock: sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env=isolated_environment()
    env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    windows=Path(os.environ.get('SystemRoot','C:/Windows'))
    env.update(PATH=';'.join(str(p) for p in (windows/'System32',windows,windows/'System32'/'WindowsPowerShell'/'v1.0')),
               JEVSEEK_DATA_DIR=str(profile),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=f'--remote-debugging-port={port} --remote-debugging-address=127.0.0.1')
    env['OPENHANDS_SUPPRESS_BANNER']='1'
    backend=output/'backend.json'
    subprocess.run([str(exe),'--self-test',str(backend)],cwd=output,env=env,timeout=180,check=True)
    assert json.loads(backend.read_text())['ok']
    process=subprocess.Popen([str(exe)],cwd=output,env=env)
    errors=[]
    try:
        with httpx.Client(trust_env=False,timeout=2) as client:
            deadline=time.time()+120
            while time.time()<deadline:
                if process.poll() is not None:raise RuntimeError('EXE exited before rendering')
                try:
                    r=client.get(f'http://127.0.0.1:{port}/json/version')
                    if r.status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.5)
            else:raise TimeoutError('Native WebView2 debugging connection')
        with sync_playwright() as p:
            browser=p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
            deadline=time.time()+30
            while time.time()<deadline:
                pages=[page for context in browser.contexts for page in context.pages if page.url.startswith('http://127.0.0.1:')]
                if pages:break
                time.sleep(.25)
            page=pages[0];page.on('pageerror',lambda e:errors.append(str(e)))
            expect(page.get_by_role('dialog',name='Microsoft runtime terms')).to_be_visible(timeout=30000)
            page.get_by_role('checkbox').check();page.get_by_role('button',name='Agree & continue').click()
            page.wait_for_timeout(1000)
            if page.get_by_role('button',name='Set up local Bonsai instead of DeepSeek').count():
                page.get_by_role('button',name='Set up local Bonsai instead of DeepSeek').click()
            else:page.get_by_role('button',name='Settings',exact=False).first.click()
            page.get_by_label('Local generation model').select_option('crack')
            page.get_by_role('button',name='Set up & use Bonsai',exact=True).click()
            deadline=time.time()+180;phases=set()
            while time.time()<deadline:
                state=page.evaluate('async()=> (await window.pywebview.api.local_model_status()).data');phases.add(state['phase'])
                if not state['busy']:break
                page.wait_for_timeout(500)
            assert state['phase']=='ready' and state['selected']=='crack',state
            expect(page.locator('.local-model-card')).to_contain_text('DeepSeek is no longer required',timeout=10000)
            page.locator('.local-model-card').scroll_into_view_if_needed();page.screenshot(path=str(output/'native-local-ready.png'))
            owned=psutil.Process(process.pid).children(recursive=True)
            model_processes=[c.pid for c in owned if c.name()=='llama-server.exe'];assert model_processes
            # Returning to cloud closes only the app-owned model process.
            page.get_by_role('button',name='Switch to DeepSeek').click()
            expect(page.locator('.local-model-card')).to_contain_text('DeepSeek selected',timeout=20000)
            assert all(not psutil.pid_exists(pid) for pid in model_processes)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.evaluate('setTimeout(()=>window.pywebview.api.close_app(), 100)')
            browser.close()
        process.wait(timeout=30)
        report={'ok':not errors,'frozen_backend':True,'native_bonsai_setup':True,'phases':sorted(phases),'owned_server_stopped_on_switch':True,'python_node_absent_from_child_path':True,'console_errors':errors,'cloud_calls':0}
        (output/'report.json').write_text(json.dumps(report,indent=2),'utf-8')
        print(json.dumps({'evidence':str(output),**report},indent=2))
        return 0 if report['ok'] else 1
    finally:
        if process.poll() is None:
            try:
                children=psutil.Process(process.pid).children(recursive=True)
                for child in children[::-1]:child.kill()
                process.kill();process.wait(timeout=15)
            except psutil.NoSuchProcess:pass


if __name__=='__main__':raise SystemExit(main())
