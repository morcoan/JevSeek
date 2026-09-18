"""Project-local MCP registration. Uses OpenHands/FastMCP, no custom protocol.
Config is loaded on startup only. Treat stdio commands as trusted executable code.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from dotenv import load_dotenv
from filelock import FileLock
from openhands.sdk.mcp.config import MCPServer, to_fastmcp_mcp_config

from jevseek.paths import is_frozen, mcp_config, resource_root

PROJECT = resource_root()
CONFIG = mcp_config()
if not is_frozen(): load_dotenv(PROJECT / '.env')


def read_config(path=CONFIG):
    if not path.exists():
        return {'mcpServers': {}}
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or set(data) != {'mcpServers'} or not isinstance(data['mcpServers'], dict):
        raise ValueError('Expected {"mcpServers": {"name": {...}}}')
    for name, server in data['mcpServers'].items():
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
            raise ValueError('Server names must contain only letters, digits, _ or -')
        MCPServer.model_validate(server)
        if bool(server.get('url')) == bool(server.get('command')):
            raise ValueError('Each server requires exactly one of url or command')
        if server.get('url'):
            url = urlsplit(server['url'])
            if url.scheme not in ('http','https') or not url.hostname or url.username or url.password:
                raise ValueError('Use an http(s) URL without embedded credentials')
    return data


def expand(value):
    if isinstance(value, str):
        def sub(match):
            key = match.group(1)
            if key not in os.environ:
                raise ValueError(f'Missing environment variable: {key}')
            return os.environ[key]
        return re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}', sub, value)
    if isinstance(value, dict): return {k: expand(v) for k,v in value.items()}
    if isinstance(value, list): return [expand(v) for v in value]
    return value


def load_servers(path=CONFIG):
    return {name: MCPServer.model_validate(expand(server))
            for name, server in read_config(path)['mcpServers'].items()
            if server.get('enabled', True)}


async def discover(servers):
    from fastmcp import Client
    async with Client(to_fastmcp_mcp_config(servers), timeout=15) as client:
        return [t.name for t in await client.list_tools()]


def update(name, server, path=CONFIG):
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path)+'.lock'):
        data=read_config(path)
        # Human-facing server labels are case-insensitive; don't duplicate Blender/blender.
        matches=[key for key in data['mcpServers'] if key.casefold()==name.casefold()]
        canonical=matches[0] if matches else name
        for key in matches: data['mcpServers'].pop(key)
        if server is not None: data['mcpServers'][canonical]=server
        fd,tmp=tempfile.mkstemp(dir=path.parent, prefix='.mcp-',suffix='.json')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(data,f,indent=2); f.write('\n')
            read_config(Path(tmp))
            os.replace(tmp,path)
        finally:
            Path(tmp).unlink(missing_ok=True)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action',required=True)
    add=sub.add_parser('add-http'); add.add_argument('name'); add.add_argument('url')
    add.add_argument('--transport',choices=['http','sse'],default='http')
    add=sub.add_parser('add-stdio'); add.add_argument('name'); add.add_argument('command'); add.add_argument('args',nargs=argparse.REMAINDER)
    sub.add_parser('list')
    check=sub.add_parser('check'); check.add_argument('name',nargs='?')
    rm=sub.add_parser('remove'); rm.add_argument('name')
    a=p.parse_args(argv)
    if a.action=='list':
        for name,s in read_config()['mcpServers'].items():
            print(name, 'enabled' if s.get('enabled',True) else 'disabled')
    elif a.action=='check':
        servers=load_servers()
        if a.name:
            name=next(key for key in servers if key.casefold()==a.name.casefold())
            servers={name:servers[name]}
        if not servers: print('No enabled MCP servers.'); return
        names=asyncio.run(discover(servers))
        print(f'MCP handshake OK; {len(names)} tools: '+', '.join(names))
    elif a.action=='remove':
        update(a.name,None); print('Removed. Restart the agent to unload its tools.')
    else:
        server=({'url':a.url,'transport':a.transport} if a.action=='add-http'
                else {'command':a.command,'args':a.args,'transport':'stdio'})
        update(a.name,server)
        print(f'Saved {a.name} in mcp.json. Not connected yet. Run mcp_setup.py check {a.name}. Restart the agent to load its tools.')


if __name__=='__main__':
    try: main()
    except Exception as e:
        # Do not echo validation values/HTTP headers that may contain credentials.
        print(f'MCP setup failed ({type(e).__name__}). Check config, environment and server availability.')
        raise SystemExit(1)
