# Build only from scripts/build_windows.py's allowlisted, private-data-free stage.
from pathlib import Path
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

ROOT = Path(SPECPATH).parent
STAGE = Path(os.environ['JEVSEEK_BUILD_STAGE'])
RUNTIME = Path(os.environ['JEVSEEK_WEBVIEW2_RUNTIME'])

# SDK registration and pydantic schemas use dynamic imports. Do not collect the
# entire developer environment; the build runs in a dedicated pinned virtualenv.
hidden = ['keyring.backends.Windows', 'clr', 'pythonnet', 'clr_loader', '_cffi_backend', 'binaryornot.data', 'win32timezone']
for package in ('openhands.sdk', 'openhands.tools.file_editor', 'openhands.tools.terminal',
                'typesafe_sdk', 'tiktoken_ext', 'fastmcp'):
    hidden += collect_submodules(package)

datas = [(str(STAGE / 'frontend' / 'dist'), 'frontend/dist'),
         (str(STAGE / 'THIRD_PARTY_NOTICES'), 'THIRD_PARTY_NOTICES'),
         (str(STAGE / 'build-info.json'), '.'),
         (str(RUNTIME), 'webview2')]
for package in ('openhands.sdk', 'openhands.tools.file_editor', 'openhands.tools.terminal',
                'typesafe_sdk', 'litellm', 'tiktoken', 'webview', 'fastmcp', 'binaryornot'):
    datas += collect_data_files(package, excludes=['**/tests/**', '**/test/**', '**/.env*', '**/proxy/**'])
for distribution in ('openhands-sdk', 'openhands-tools', 'typesafe-sdk', 'pywebview', 'keyring', 'fastmcp'):
    datas += copy_metadata(distribution, recursive=True)

a = Analysis([str(STAGE / 'desktop.py')], pathex=[str(STAGE)], binaries=[], datas=datas,
             hiddenimports=hidden, hookspath=[], runtime_hooks=[],
             excludes=['tkinter', 'IPython', 'pytest', 'matplotlib', 'scipy', 'numpy', 'pandas',
                       'torch', 'tensorflow', 'transformers', 'playwright', 'browser_use',
                       'browser_harness', 'lmnr', 'tom_swe'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='JevSeek',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=True,
          icon=str(ROOT / 'packaging' / 'JevSeek.ico'),
          version=str(ROOT / 'packaging' / 'version.txt'))
