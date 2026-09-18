"""Fail-closed local pre-publication audit. Never prints matching secret values.

Ignores are not encryption. Review the resulting file list before publishing.
--staged reads Git's INDEX bytes, not potentially different working-tree files.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIRS = {'.pi', '.jevseek', '.local', '.git', '.venv', 'venv', '.build-venv', '.build-cache', 'node_modules', '__pycache__', 'release', 'dist', 'build', 'work', 'work_jit', 'work_pre', 'sessions'}
PRIVATE_NAMES = {'mcp.json', 'mcp.json.lock', 'credentials.json', 'secrets.json', 'facts.txt', 'desktop.json', 'runtime-terms.json', 'mcp-result.txt'}
PRIVATE_SUFFIXES = {'.log', '.jsonl', '.db', '.sqlite', '.sqlite3', '.pfx', '.p12', '.key', '.dmp', '.exe', '.dll', '.cab', '.zip'}
TOKEN_PATTERNS = [re.compile(rb'\b(?:sk-[A-Za-z0-9_-]{20,}|apikey_[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{30,})\b'),
                  re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]


def git(*args, cwd=ROOT):
    result = subprocess.run(['git', *args], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode: raise RuntimeError('Git audit failed; initialize a local Git repository first.')
    return result.stdout


def public_files(root=ROOT):
    raw = git('ls-files', '--cached', '--others', '--exclude-standard', '-z', cwd=root)
    return sorted(set(p.decode('utf-8') for p in raw.split(b'\0') if p))


def forbidden_path(name):
    parts = Path(name).parts
    lower = [p.lower() for p in parts]
    leaf = lower[-1]
    if any(p in PRIVATE_DIRS for p in lower): return True
    if leaf in PRIVATE_NAMES or leaf.startswith('client_secret'): return True
    if leaf.startswith('.env') and leaf != '.env.example': return True
    if leaf.endswith('.env') or Path(leaf).suffix in PRIVATE_SUFFIXES: return True
    if len(lower) > 1 and lower[0] == 'benchmarks' and (lower[1] in ('results', 'deliberation_results') or 'console' in leaf): return True
    return False


def known_secrets(root=ROOT):
    values = [v for k,v in os.environ.items() if re.search(r'KEY|TOKEN|SECRET|PASSWORD|JEV_KET', k, re.I) and len(v) >= 8]
    env = root / '.env'
    if env.exists():
        # A local-only equality scan. Values never appear in reports or console output.
        from dotenv import dotenv_values
        values += [v for k,v in dotenv_values(env).items() if v and len(v) >= 8 and re.search(r'KEY|TOKEN|SECRET|PASSWORD|JEV_KET', k, re.I)]
    return [v.encode('utf-8') for v in set(values)]


def scan_bytes(raw, secrets=(), username=None):
    reasons = []
    if any(secret in raw for secret in secrets): reasons.append('known_local_secret')
    if any(pattern.search(raw) for pattern in TOKEN_PATTERNS): reasons.append('credential_pattern')
    # Normalize escaped Windows separators without confusing URL schemes for paths.
    normalized = re.sub(rb'/+', b'/', raw.replace(bytes([92]), b'/')).lower()
    if username:
        user = username.encode('utf-8').lower()
        if any(marker + user + b'/' in normalized for marker in (b'/users/', b'/home/')):
            reasons.append('personal_home_path')
    return reasons


def audit(root=ROOT, staged=False):
    root = Path(root).resolve()
    files = (sorted(set(p.decode() for p in git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z', cwd=root).split(b'\0') if p))
             if staged else public_files(root))
    findings = []
    secrets = known_secrets(root)
    for name in files:
        path = root / name
        reasons = []
        if forbidden_path(name): reasons.append('private_path')
        if path.is_symlink(): reasons.append('symlink_not_allowed')
        if not path.resolve().is_relative_to(root): reasons.append('path_escape')
        if staged:
            raw = git('show', ':' + name, cwd=root)
        elif path.is_file(): raw = path.read_bytes()
        else: continue
        reasons += scan_bytes(raw, secrets, Path.home().name)
        if reasons: findings.append({'file': name, 'reasons': sorted(set(reasons))})
    # Force-added ignored files must never slip past a normal gitignore check.
    for name in git('ls-files', '--cached', '--ignored', '--exclude-standard', '-z', cwd=root).split(b'\0'):
        if name: findings.append({'file': name.decode(), 'reasons': ['tracked_but_ignored']})
    return {'ok': not findings, 'files_scanned': len(files), 'findings': findings, 'mode': 'index' if staged else 'public_candidates'}


def audit_history(root=ROOT):
    secrets = known_secrets(root)
    objects = git('rev-list', '--objects', '--all', cwd=root).splitlines()
    findings = []; checked = 0
    for row in objects:
        sha, _, path = row.partition(b' ')
        if git('cat-file', '-t', sha.decode(), cwd=root).strip() != b'blob': continue
        checked += 1
        name = path.decode('utf-8', errors='replace')
        reasons = ['private_historical_path'] if name and forbidden_path(name) else []
        reasons += scan_bytes(git('cat-file', 'blob', sha.decode(), cwd=root), secrets, Path.home().name)
        if reasons: findings.append({'file': name or '(historical blob)', 'object': sha.decode()[:12], 'reasons': reasons})
    return {'ok': not findings, 'blobs_scanned': checked, 'findings': findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged', action='store_true')
    parser.add_argument('--history', action='store_true', help='Also scan every reachable historical Git blob')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = audit(staged=args.staged)
    if args.history:
        report['history'] = audit_history()
        report['ok'] = report['ok'] and report['history']['ok']
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__': raise SystemExit(main())
