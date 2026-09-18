"""Download/verify the pinned Microsoft x64 runtime into an ignored build cache.

Not run by end users. Build releases offline after this step. The fixed runtime
must be refreshed for security updates; it does not auto-update itself.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-initial-hash', action='store_true', help='Maintainer only: pin a freshly verified Microsoft download')
    args = parser.parse_args()
    if sys.platform != 'win32': parser.error('Build the Windows release on Windows x64.')
    manifest_path = ROOT / 'packaging' / 'webview2.json'
    manifest = json.loads(manifest_path.read_text())
    if not manifest['sha256'] and not args.record_initial_hash:
        parser.error('Runtime hash is not pinned. Maintainer verification is required.')
    url = manifest['url']
    if urlsplit(url).hostname != 'msedge.sf.dl.delivery.mp.microsoft.com' or urlsplit(url).scheme != 'https':
        raise ValueError('Only the official pinned Microsoft HTTPS endpoint is accepted')
    cache = ROOT / '.build-cache' / 'webview2'; cache.mkdir(parents=True, exist_ok=True)
    cab = cache / (manifest['version'] + '.cab')
    if not cab.exists():
        import requests
        temporary = cab.with_suffix('.part')
        with requests.get(url, stream=True, timeout=(20, 180)) as response:
            response.raise_for_status()
            if urlsplit(response.url).hostname != urlsplit(url).hostname: raise ValueError('Unexpected download redirect')
            with temporary.open('wb') as target:
                for chunk in response.iter_content(1024 * 1024): target.write(chunk)
        temporary.replace(cab)
    digest = hashlib.file_digest(cab.open('rb'), 'sha256').hexdigest()
    if manifest['sha256'] and digest != manifest['sha256']: raise ValueError('Microsoft runtime checksum mismatch')
    extracted = cache / manifest['version']
    if not (extracted / 'msedgewebview2.exe').is_file():
        unpack = cache / ('extract-' + manifest['version']); unpack.mkdir(exist_ok=True)
        subprocess.run([str(Path.home().anchor) + 'Windows/System32/expand.exe', str(cab), '-F:*', str(unpack)], check=True, stdout=subprocess.DEVNULL)
        candidates = list(unpack.rglob('msedgewebview2.exe'))
        if len(candidates) != 1: raise ValueError('Unexpected Microsoft runtime structure')
        if extracted.exists(): shutil.rmtree(extracted)
        shutil.move(str(candidates[0].parent), extracted)
        if unpack.exists(): shutil.rmtree(unpack)
    exe = extracted / 'msedgewebview2.exe'
    escaped = str(exe).replace("'", "''")
    command = f"$s=Get-AuthenticodeSignature -LiteralPath '{escaped}'; @{{status=[string]$s.Status;subject=$s.SignerCertificate.Subject;version=(Get-Item -LiteralPath '{escaped}').VersionInfo.ProductVersion}} | ConvertTo-Json -Compress"
    verification = json.loads(subprocess.check_output(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command], text=True))
    if verification['status'] != 'Valid' or 'Microsoft Corporation' not in verification['subject']:
        raise ValueError('The runtime must have a valid Microsoft Authenticode signature')
    if verification['version'] != manifest['version']: raise ValueError('Runtime version mismatch')
    if args.record_initial_hash:
        manifest['sha256'] = digest
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'version': manifest['version'], 'sha256': digest, 'microsoft_signature': verification['status'], 'cab_bytes': cab.stat().st_size, 'runtime_dir': str(extracted)}, indent=2))


if __name__ == '__main__': main()
