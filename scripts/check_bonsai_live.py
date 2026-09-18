"""Opt-in real Bonsai setup + React-triggered agent integration.

Downloads the selected model/runtime, uses GPU/RAM and bills Jev requests.
Never uses DeepSeek. Test workspace/session/profile stay in ignored .jevseek.
"""
from __future__ import annotations
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--model', choices=['prism','crack'], default='crack')
    args=parser.parse_args()
    if not args.run: parser.error('Pass --run to consent to model downloads and billable Jev integration.')
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env')
    from jevseek.credentials import ENV_NAMES, environment_keys, CredentialStore
    keys=environment_keys()
    try: keys.update(CredentialStore().load())
    except Exception: pass
    if not keys.get('jev'): raise SystemExit('A Jev key is required.')
    for names in ENV_NAMES.values():
        for name in names: os.environ.pop(name,None)
    os.environ['JEV_KET']=keys['jev']
    from jevseek.desktop import DesktopAPI
    from playwright.sync_api import sync_playwright, expect
    output=ROOT/'.jevseek'/'bonsai-live'/str(time.time_ns()); output.mkdir(parents=True)
    workspace=output/'workspace';workspace.mkdir()
    fixture=workspace/'fixture.txt';fixture.write_text('BONSAI_CHECK=local_generation_verified\n')
    api=DesktopAPI(ROOT,sessions_dir=output/'sessions',workspace=workspace,state_dir=ROOT/'.jevseek'/'bonsai-validation')
    api.save_preferences({'theme':'system','workspace':str(workspace),'use_mcp':False})
    errors=[];violations=[];phases=set()
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'frontend'/'dist')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch()
            page=browser.new_page(viewport={'width':1200,'height':900})
            page.on('pageerror',lambda e: errors.append(str(e)))
            page.on('console',lambda m: errors.append(m.text) if m.type=='error' else None)
            methods=['bootstrap','poll','list_sessions','get_session','save_preferences','local_model_status','setup_local_model','cancel_local_setup','use_deepseek','start_run','cancel_run','get_key_status','open_external']
            page.expose_function('__bonsaiBridge',lambda name,args:getattr(api,name)(*args))
            page.add_init_script('window.pywebview={api:Object.fromEntries('+json.dumps(methods)+'.map(n=>[n,(...a)=>window.__bonsaiBridge(n,a)]))};')
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.get_by_role('button',name='Settings',exact=False).click()
            page.get_by_label('Local generation model').select_option(args.model)
            page.get_by_role('button',name='Set up & use Bonsai',exact=True).click()
            screenshot_progress=False
            deadline=time.time()+1800
            while time.time()<deadline:
                state=api.local_model_status()['data'];phases.add(state['phase'])
                if state['phase']=='downloading' and not screenshot_progress:
                    page.locator('.local-model-card').scroll_into_view_if_needed()
                    page.screenshot(path=str(output/'downloading.png'));screenshot_progress=True
                if not state['busy']: break
                page.wait_for_timeout(500)
            state=api.local_model_status()['data']
            assert state['phase']=='ready',state
            assert state['selected']==args.model and not api.get_key_status()['data']['providers']['deepseek']
            expect(page.locator('.local-model-card')).to_contain_text('DeepSeek is no longer required',timeout=10000)
            def audit(name):
                page.wait_for_timeout(250)
                page.locator('.local-model-card').scroll_into_view_if_needed()
                page.screenshot(path=str(output/(name+'.png')))
                page.evaluate((ROOT/'frontend'/'node_modules'/'axe-core'/'axe.min.js').read_text('utf-8'))
                violations.extend(page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))"))
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            audit('local-ready-light')
            page.set_viewport_size({'width':360,'height':800});page.evaluate("document.documentElement.dataset.theme='dark'");audit('local-ready-mobile-dark')
            page.set_viewport_size({'width':1200,'height':900})
            page.get_by_role('button',name='New conversation',exact=False).first.click()
            page.get_by_role('textbox',name='Message JevSeek').fill('Read fixture.txt and report the exact BONSAI_CHECK value. Do not change files or use shell or MCP.')
            page.get_by_role('button',name='Send message',exact=True).click()
            deadline=time.time()+240
            while time.time()<deadline:
                sessions=api.list_sessions()['data']['sessions']
                if sessions and api._active is None: break
                page.wait_for_timeout(500)
            assert api._active is None,'Agent timed out'
            sessions=api.list_sessions()['data']['sessions'];assert len(sessions)==1
            snapshot=api.get_session(sessions[0]['session_id'])['data']
            events=snapshot['events']
            tools=[e['data'] for e in events if e['kind']=='tool_started']
            usage=[e['data'] for e in events if e['kind']=='usage']
            assert tools and all(t['tool']=='read' for t in tools),tools
            assert any(u['provider']=='bonsai' for u in usage)
            assert not any(u['provider']=='deepseek' for u in usage)
            assert snapshot['meta']['status']=='completed',snapshot['meta']
            assert fixture.read_text()=='BONSAI_CHECK=local_generation_verified\n'
            page.wait_for_timeout(1000)
            expect(page.locator('.conversation')).to_contain_text('local_generation_verified')
            page.screenshot(path=str(output/'conversation.png'))
            browser.close()
        report={'model':args.model,'setup':state,'phases':sorted(phases),'tool_calls':tools,'usage_providers':sorted({u['provider'] for u in usage}),'status':snapshot['meta']['status'],'fixture_unchanged':True,'axe_violations':violations,'console_errors':errors,'no_deepseek_key':True}
        (output/'report.json').write_text(json.dumps(report,indent=2),'utf-8')
        print(json.dumps({'evidence':str(output),**report},indent=2))
        return 1 if errors or violations else 0
    finally:
        if api._active: api.cancel_run(); api._thread.join(timeout=330)
        api._bonsai.close();server.shutdown()


if __name__=='__main__':raise SystemExit(main())
