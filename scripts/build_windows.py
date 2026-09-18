"""Build the standalone x64 EXE from an allowlisted, secret-free staging tree.

Run using .build-venv/Scripts/python.exe after installing requirements + build tools.
No private state, .env, MCP config, history, machine paths or agent memory is copied.
"""
from __future__ import annotations
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def licenses(stage):
    target = stage / 'THIRD_PARTY_NOTICES'; target.mkdir()
    entries = []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata['Name'].lower()):
        name = dist.metadata['Name']; version = dist.version
        folder = target / 'python' / name
        files = []
        for item in dist.files or []:
            lower = item.name.lower()
            if not (lower.startswith(('license', 'licence', 'copying', 'notice', 'copyright', 'authors')) or '/licenses/' in str(item).lower()): continue
            source = Path(dist.locate_file(item))
            if not source.is_file() or source.suffix in ('.py', '.pyc'): continue
            folder.mkdir(parents=True, exist_ok=True)
            dest = folder / item.name
            if dest.exists() and dest.read_bytes() != source.read_bytes():
                dest = folder / (hashlib.sha256(str(item).encode()).hexdigest()[:8] + '-' + item.name)
            shutil.copy2(source, dest); files.append(dest.relative_to(target).as_posix())
        entries.append({'name': name, 'version': version, 'license': dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'See upstream notices', 'files': files})
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.is_file(): shutil.copy2(python_license, target / 'Python-LICENSE.txt')
    upstream = ROOT / 'packaging' / 'licenses'
    if upstream.is_dir(): shutil.copytree(upstream, target / 'upstream')
    lock = json.loads((ROOT / 'frontend' / 'package-lock.json').read_text())
    for relative, info in lock['packages'].items():
        if not relative or info.get('dev'): continue
        package = ROOT / 'frontend' / relative
        name = relative.removeprefix('node_modules/').replace('/', '__')
        folder = target / 'javascript' / name; folder.mkdir(parents=True, exist_ok=True)
        for file in package.iterdir():
            if file.is_file() and file.name.lower().startswith(('license', 'licence', 'copying', 'notice')):
                shutil.copy2(file, folder / file.name)
        (folder / 'package-info.json').write_text(json.dumps({'package': name, 'version': info.get('version'), 'license': info.get('license')}, indent=2))
    (target / 'python-packages.json').write_text(json.dumps(entries, indent=2), encoding='utf-8')
    (target / 'README.txt').write_text('Third-party notices for the JevSeek Windows build.\nPython package inventory includes build dependencies as well as runtime dependencies.\nWebView2 is Microsoft software, not relicensed by this project. Its own bundled component notices are preserved in webview2/.\n', encoding='utf-8')


def icon():
    from PIL import Image, ImageDraw
    image = Image.new('RGBA', (256, 256)); draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((6, 6, 249, 249), radius=48, fill='#ed9dc4')
    points = [(10,10),(30,10),(30,23),(23,23),(23,30),(10,30),(10,23),(17,23),(17,17),(10,17)]
    draw.polygon([(int(x*6.4),int(y*6.4)) for x,y in points], fill='#281b23')
    draw.rectangle((64,64,108,108), fill='#fcfaf9')
    image.save(ROOT / 'packaging' / 'JevSeek.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])


def main():
    if sys.platform != 'win32' or sys.maxsize < 2**32: raise SystemExit('Use 64-bit Windows Python.')
    if sys.prefix == sys.base_prefix: raise SystemExit('Use an isolated build venv, not the global Python environment.')
    manifest = json.loads((ROOT / 'packaging' / 'webview2.json').read_text())
    runtime = ROOT / '.build-cache' / 'webview2' / manifest['version']
    if not (runtime / 'msedgewebview2.exe').is_file(): raise SystemExit('Run scripts/prepare_webview2.py first.')
    cab = runtime.parent / (manifest['version'] + '.cab')
    with cab.open('rb') as source: actual = hashlib.file_digest(source, 'sha256').hexdigest()
    if actual != manifest['sha256']: raise SystemExit('Pinned Microsoft runtime checksum failed.')
    stage = ROOT / 'build' / 'stage'
    if stage.exists(): shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for name in ('desktop.py', 'main.py', 'mcp_setup.py'):
        shutil.copy2(ROOT / name, stage / name)
    (stage / 'jevseek').mkdir()
    for source in (ROOT / 'jevseek').glob('*.py'):
        if source.is_symlink(): raise ValueError('Symlink in runtime source')
        shutil.copy2(source, stage / 'jevseek' / source.name)
    built = ROOT / 'frontend' / 'dist'
    if not (built / 'index.html').is_file(): raise SystemExit('Run npm ci && npm run build in frontend first.')
    if any(p.is_symlink() for p in built.rglob('*')): raise ValueError('Symlink in frontend build')
    shutil.copytree(built, stage / 'frontend' / 'dist')
    licenses(stage); icon()
    shutil.copy2(ROOT / 'LICENSE', stage / 'THIRD_PARTY_NOTICES' / 'JevSeek-LICENSE.txt')
    info = {'product': 'JevSeek', 'version': '0.2.1', 'platform': 'Windows x64', 'python': sys.version.split()[0],
            'webview2': manifest['version'], 'webview2_cab_sha256': actual,
            'private_state_included': False, 'source_files': sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*.py'))}
    (stage / 'build-info.json').write_text(json.dumps(info, indent=2))
    # A caller may have API keys in its shell. Analysis hooks must not inherit them.
    env = {k:v for k,v in os.environ.items() if not any(word in k.upper() for word in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD')) and k not in ('PYTHONPATH', 'PYTHONHOME', 'JEV_KET')}
    env.update(JEVSEEK_BUILD_STAGE=str(stage), JEVSEEK_WEBVIEW2_RUNTIME=str(runtime),
               OPENHANDS_SUPPRESS_BANNER='1', LITELLM_LOCAL_MODEL_COST_MAP='True', AWS_EC2_METADATA_DISABLED='true')
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--distpath', str(ROOT / 'release'),
               '--workpath', str(ROOT / 'build' / 'pyinstaller'), str(ROOT / 'packaging' / 'JevSeek.spec')]
    subprocess.run(command, cwd=stage, env=env, check=True)
    exe = ROOT / 'release' / 'JevSeek.exe'
    with exe.open('rb') as source: digest = hashlib.file_digest(source, 'sha256').hexdigest()
    shutil.copytree(stage / 'THIRD_PARTY_NOTICES', ROOT / 'release' / 'THIRD_PARTY_NOTICES', dirs_exist_ok=True)
    (ROOT / 'release' / 'SHA256SUMS.txt').write_text(f'{digest}  JevSeek.exe\n')
    (ROOT / 'release' / 'build-info.json').write_text(json.dumps(info, indent=2))
    print(json.dumps({'exe': str(exe), 'bytes': exe.stat().st_size, 'sha256': digest}, indent=2))


if __name__ == '__main__': main()
