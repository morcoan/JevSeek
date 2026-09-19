"""Control only the private, already-provisioned research VM. No Windows installs."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'.local'/'research'/'linux-sandbox'


def ssh_args():
    config=json.loads((STATE/'vm-config.json').read_text())
    empty=STATE/'ssh-config';empty.touch(exist_ok=True)
    return ['ssh','-F',str(empty),'-i',str(STATE/'id_ed25519'),'-p',str(config['ssh_port']),'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ForwardAgent=no','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(STATE/'known_hosts'),'-o','ConnectTimeout=10','-o','ServerAliveInterval=20','research@127.0.0.1']


def remote(command, **kwargs):
    return subprocess.run(ssh_args()+[command],**kwargs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['status','start','stop'])
    args=parser.parse_args()
    if not (STATE/'vm-config.json').exists():raise SystemExit('Research VM has not been provisioned on this machine.')
    if args.action=='status':
        return remote('uname -sr; free -m; docker version --format "{{.Server.Version}}"; systemctl is-active jevseek-network-guard').returncode
    if args.action=='stop':
        return remote('sudo systemctl poweroff').returncode  # Linux VM ONLY, never Windows.
    check=remote('true',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if check.returncode==0:print('Linux VM is already running.');return 0
    # Never launch a second process against the same virtual disk.
    pidfile=STATE/'pid.json'
    if pidfile.exists():
        import psutil
        pid=json.loads(pidfile.read_text())['pid']
        if psutil.pid_exists(pid):raise SystemExit('A previous VM PID still exists. Inspect it rather than starting a second VM.')
    argv=json.loads((STATE/'launch-args.json').read_text())
    if Path(argv[0]).resolve()!=STATE/'qemu'/'qemu-system-x86_64.exe':raise SystemExit('Unexpected VM executable; inspect local configuration.')
    env={k:v for k,v in os.environ.items() if k.upper()!='JEV_KET' and not any(s in k.upper() for s in ('KEY','TOKEN','PASSWORD','SECRET'))}
    with (STATE/'qemu.log').open('ab') as log:
        p=subprocess.Popen(argv,cwd=STATE,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0))
    pidfile.write_text(json.dumps({'pid':p.pid}))
    for _ in range(60):
        if p.poll() is not None:raise SystemExit('VM exited. Inspect private qemu.log. No Windows settings were changed.')
        if remote('test -f /var/lib/jevseek-sandbox-ready && docker info >/dev/null',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
            print('Linux Docker sandbox ready. Windows was not restarted.');return 0
        time.sleep(2)
    raise SystemExit('VM still starting. Inspect status; do not launch another copy.')


if __name__=='__main__':raise SystemExit(main())
