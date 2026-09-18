"""Four thin adapters to prebuilt OpenHands tools; MCP also uses its SDK.
No filesystem editing, shell implementation or MCP protocol is reimplemented here.
Local execution is TRUSTED, NOT an OS sandbox.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import platform

from jsonschema import validate
from jsonschema.exceptions import ValidationError
from openhands.tools.file_editor import FileEditorAction
from openhands.tools.file_editor.impl import FileEditorExecutor
from openhands.tools.terminal import TerminalAction
from openhands.tools.terminal.impl import TerminalExecutor
from openhands.tools.terminal.descriptions import UNIX_TOOL_DESCRIPTION, WINDOWS_TOOL_DESCRIPTION
from openhands.sdk.mcp import create_mcp_tools


def fields(action, names, required):
    source = action.model_json_schema()
    schema = {'type':'object', 'properties':{k:deepcopy(source['properties'][k]) for k in names},
              'required':required, 'additionalProperties':False}
    if '$defs' in source: schema['$defs']=source['$defs']
    return schema


class Tools:
    def __init__(self, workspace, artifact_dir, mcp_servers=None):
        self.workspace = Path(workspace).resolve()
        self.artifact_dir = Path(artifact_dir)
        self.editor = FileEditorExecutor(workspace_root=str(self.workspace))
        self.terminal = None
        self.mcp = None
        self.mcp_tools = {}
        self.schemas = {
            'read': fields(FileEditorAction,['path','view_range'],['path']),
            'write': fields(FileEditorAction,['path','file_text'],['path','file_text']),
            'edit': fields(FileEditorAction,['path','old_str','new_str'],['path','old_str','new_str']),
            'bash': fields(TerminalAction,['command','is_input','timeout','reset'],['command'])}
        self.descriptions = {
            'read': 'Inspect existing files/directories or archived output. Use view_range=[start,end] (1-based; -1 means end) for large files.',
            'write': 'Create a NEW file with complete file_text. Use edit for existing files.',
            'edit': 'Change existing file using exact old_str/new_str replacement. Read exact current source first; never use omitted text as an edit anchor.',
            'bash': 'Run commands, search files, git, and tests. '+('Uses PowerShell syntax on Windows, NOT bash syntax. ' if platform.system()=='Windows' else 'Uses the local shell. ')+
                    'exit_code=-1 means still running: command="" polls; is_input=true with command="C-c" interrupts. timeout is a soft wait; do not assume completion.'}
        for name in self.schemas:
            self.schemas[name]['description']=self.descriptions[name]
        self.schemas['bash']['description']=(WINDOWS_TOOL_DESCRIPTION if platform.system()=='Windows' else UNIX_TOOL_DESCRIPTION)
        if mcp_servers:
            try:
                self.mcp = create_mcp_tools(mcp_servers, timeout=20)
                for tool in self.mcp.tools:
                    name = 'mcp.' + tool.name
                    self.mcp_tools[name] = tool
                    self.descriptions[name] = tool.description
                    # SDK's OpenAI wrapper injects agent-only fields (e.g. summary) which
                    # action_from_arguments does NOT accept here. Use the authoritative server schema.
                    raw=deepcopy(getattr(tool.mcp_tool,'input_schema',None) or tool.mcp_tool.inputSchema)
                    raw['description']=tool.description
                    self.schemas[name]=raw
            except BaseException:
                self.close()
                raise

    def catalog(self):
        # Details are sent only after selection; do not flood Jev with every schema.
        return {**{name:description[:1600] for name,description in self.descriptions.items() if name.startswith('mcp.')},
                'read':'Inspect needed existing source, specification, tests or archived output. No changes.',
                'write':'Create a NEW file with complete content.',
                'edit':'Modify an existing file to implement or repair the user request, including a full rewrite.',
                'bash':'Run commands, install requested MCP configuration using the local helper, search, git or execute tests.'}

    def execute(self, name, args):
        try:
            validate(args, self.schemas[name])
        except ValidationError as exc:
            # The full schema dump is noise, not useful execution evidence.
            raise ValueError('Invalid tool arguments: '+exc.message) from None
        if name=='bash':
            if self.terminal is None:
                self.artifact_dir.mkdir(parents=True, exist_ok=True)
                self.terminal=TerminalExecutor(working_dir=str(self.workspace), full_output_save_dir=str(self.artifact_dir),
                                               no_change_timeout_seconds=30)
            args = dict(args)
            if args.get('timeout') is None: args['timeout']=60
            result=self.terminal(TerminalAction(**args))
        elif name in ('read','write','edit'):
            args=dict(args)
            args['path']=str((self.workspace/args['path']).resolve())
            action={'read':'view','write':'create','edit':'str_replace'}[name]
            if name=='write' and Path(args['path']).exists(): raise ValueError('File exists; select edit')
            result=self.editor(FileEditorAction(command=action, **args))
        else:
            tool=self.mcp_tools[name]
            result=tool(tool.action_from_arguments(args))
        text = '\n'.join(c.text for c in result.content if getattr(c,'type',None)=='text')
        other=[getattr(c,'type','unknown') for c in result.content if getattr(c,'type',None)!='text']
        if other: text+='\n[Non-text attachments retained by tool; this text-only agent cannot inspect: '+', '.join(other)+']'
        code=getattr(result,'exit_code',None)
        if name=='bash' and code is None: code=getattr(getattr(result,'metadata',None),'exit_code',None)
        if name=='bash':
            cwd=getattr(getattr(result,'metadata',None),'working_dir',None)
            text+=f'\n[Shell cwd: {cwd}; exit code: {code}]'
        return {'text':text,'is_error':bool(result.is_error),'exit_code':code,
                'target':getattr(result,'path',None),
                'still_running':name=='bash' and code==-1, 'raw':result.model_dump(mode='json')}

    def close(self):
        try:
            if self.terminal is not None:
                terminal=self.terminal; self.terminal=None; terminal.close()
        finally:
            if self.mcp is not None:
                client=self.mcp; self.mcp=None; client.sync_close()
