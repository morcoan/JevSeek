"""Export only audited Git-eligible source files, never the whole local folder.
Does not create a remote, commit, upload or publish anything.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from public_audit import ROOT, audit, audit_history, public_files


def main():
    report = audit()
    history = audit_history()
    if not report['ok'] or not history['ok']:
        raise SystemExit('Source/history audit failed. Inspect the local audit report before exporting.')
    destination = ROOT / 'release' / 'public-source'
    if destination.exists(): shutil.rmtree(destination)
    destination.mkdir(parents=True)
    names = public_files()
    for name in names:
        source = ROOT / name
        if source.is_symlink() or not source.resolve().is_relative_to(ROOT): raise ValueError('Unsafe source path')
        target = destination / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    archive = ROOT / 'release' / 'JevSeek-source.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for name in names: zipped.write(destination / name, 'JevSeek/' + name)
    with archive.open('rb') as source: digest = hashlib.file_digest(source, 'sha256').hexdigest()
    evidence = {'source_files': len(names), 'source_zip_sha256': digest, 'source_audit': report, 'history_audit': history,
                'private_directories_included': False, 'published': False}
    (ROOT / '.jevseek' / 'public-export.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__': main()
