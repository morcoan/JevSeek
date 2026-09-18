"""Separate immutable application resources from writable personal state."""
from __future__ import annotations
import os
from pathlib import Path
import sys


def is_frozen(): return bool(getattr(sys, 'frozen', False))


def resource_root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1])).resolve()


def state_home():
    override = os.getenv('JEVSEEK_DATA_DIR')
    if override: return Path(override).expanduser().resolve()
    if is_frozen():
        return Path(os.getenv('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local') / 'JevSeek'
    return resource_root() / '.jevseek'


def mcp_config():
    if is_frozen() or os.getenv('JEVSEEK_DATA_DIR'): return state_home() / 'mcp.json'
    return resource_root() / 'mcp.json'


def default_workspace():
    if not is_frozen(): return resource_root()
    workspace = state_home() / 'workspaces' / 'default'
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace
