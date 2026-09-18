import { useEffect, useRef } from 'react';
import { ArrowUp, Square, Folder, CornerDownLeft, Plug } from 'lucide-react';
import { basename } from './state';

interface Props {
  value: string; onChange: (value: string) => void; onSend: () => void; onStop: () => void;
  running: boolean; stopping: boolean; busy: boolean; desktop: boolean;
  workspace: string; mcp: boolean; onWorkspace: () => void; onSettings: () => void;
  welcome?: boolean; inputRef: React.RefObject<HTMLTextAreaElement | null>;
}
export function Composer({ value, onChange, onSend, onStop, running, stopping, busy, desktop, workspace, mcp, onWorkspace, onSettings, welcome, inputRef }: Props) {
  const formRef = useRef<HTMLFormElement>(null);
  useEffect(() => {
    const node = inputRef.current;
    if (node) { node.style.height = 'auto'; node.style.height = `${Math.min(node.scrollHeight, 200)}px`; }
  }, [value, inputRef]);
  return <div className={`composer-wrap ${welcome ? 'welcome-composer' : ''}`}>
    <form ref={formRef} className={`composer ${running ? 'composer-running' : ''}`} onSubmit={e => { e.preventDefault(); if (!busy && !running && desktop && value.trim()) onSend(); }}>
      <label className="sr-only" htmlFor="message">Message JevSeek</label>
      <textarea id="message" ref={inputRef} value={value} rows={welcome ? 3 : 2} placeholder={desktop ? 'Ask a question, or make something happen…' : 'Explore the interface. Open the desktop app to run a task.'}
        onChange={e => onChange(e.target.value)} onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); formRef.current?.requestSubmit(); }
        }} aria-describedby="composer-help" />
      <div className="composer-toolbar"><div className="composer-context">
        <button type="button" className="context-button" onClick={onWorkspace} title={workspace || 'Choose a workspace'}><Folder size={14} /><span>{basename(workspace)}</span></button>
        <button type="button" className={`context-button mcp-mode ${mcp ? 'selected-mode' : ''}`} onClick={onSettings} title="Configure MCP tools in Settings"><Plug size={13} /><span>MCP {mcp ? 'on' : 'off'}</span></button>
      </div>
      {running ? <button type="button" className="send-button stop-button" aria-label={stopping ? 'Stop requested' : 'Stop agent'} disabled={stopping} onClick={onStop}><Square size={15} fill="currentColor" /></button> :
        <button type="submit" className="send-button" aria-label="Send message" disabled={!desktop || busy || !value.trim()}><ArrowUp size={20} strokeWidth={2} /></button>}
      </div>
    </form>
    <div id="composer-help" className="composer-help"><span>{running ? stopping ? 'Stopping safely. Native calls may need time to return.' : 'Working locally. You can keep writing while the agent runs.' : !desktop ? 'Browser preview · messages do not run a model' : 'Tools run with your permissions. Review important changes.'}</span><span className="enter-hint"><CornerDownLeft size={12} /> Send <span className="help-separator">/</span> Shift + Enter for a new line</span></div>
  </div>;
}
