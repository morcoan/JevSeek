import { useEffect, useRef, useState } from 'react';
import { Activity, ArrowLeft, ArrowUpRight, Check, ChevronRight, FileText, Folder, HardDrive, Monitor, Moon, Search, Settings2, ShieldCheck, Sun, TriangleAlert } from 'lucide-react';
import { call } from './bridge';
import { LocalModelSetup } from './LocalModel';
import { CopyButton, Dialog, EmptyState, StatusBadge, ToolWindow } from './components';
import { basename, bytesLabel, dateLabel, turnsFrom } from './state';
import type { Artifact, ArtifactContent, BackendEvent, Bootstrap, Preferences, SessionMeta, Theme } from './types';

export function ActivityView({ sessions, selected, events, meta, active, onSelect, onBack, onChat, onError }: {
  sessions: SessionMeta[]; selected: string | null; events: BackendEvent[]; meta: SessionMeta | null; active: boolean;
  onSelect: (id: string) => void; onBack: () => void; onChat: () => void; onError: (error: string) => void;
}) {
  const [query, setQuery] = useState('');
  const filtered = sessions.filter(s => `${s.title} ${s.workspace}`.toLowerCase().includes(query.toLowerCase()));
  const turns = turnsFrom(events);
  return <div className="page-content">
    <header className="page-heading"><div className="eyebrow">THE WORK, RECORDED</div><h1>Activity</h1><p>See what ran. Look a little closer when you need to.</p></header>
    {selected && meta ? <>
      <div className="section-toolbar"><button className="quiet-button" onClick={onBack}><ArrowLeft size={15} />All conversations</button><button className="quiet-button" onClick={onChat}>Open conversation<ArrowUpRight size={15} /></button></div>
      <div className="activity-heading"><h2>{meta.title}</h2><StatusBadge status={active ? 'running' : meta.status} /></div><p className="technical muted break-word">{meta.workspace}</p>
      <div className="activity-detail">{turns.map((turn, index) => <section className="activity-turn" key={turn.key}>
        {turn.user && <h3>{turn.user.data.text}</h3>}
        <ToolWindow events={turn.events} active={active && index === turns.length - 1} defaultOpen />
        {turn.events.filter(e => ['compaction', 'error', 'tool_uncertain'].includes(e.kind)).map((e, i) => <div className={`event-line ${e.kind === 'error' ? 'error-text' : 'muted'}`} key={i}>
          {e.kind === 'error' ? <TriangleAlert size={15} /> : <FileText size={15} />}<div><span>{e.kind === 'compaction' ? `Factual context compacted · ${e.data.audience}` : e.kind === 'tool_uncertain' ? 'Interrupted effects acknowledged' : e.data.message || e.data.error}</span><time>{dateLabel(e.time)}</time></div>
        </div>)}
        {turn.answer && <div className="event-line"><Check size={15} /><span>{turn.answer.data.status === 'completed' ? 'Response saved' : 'Run paused'} · {dateLabel(turn.answer.time)}</span></div>}
      </section>)}</div>
      <div className="local-note"><ShieldCheck size={16} /><p>These are recorded observations, not a guarantee of correctness. Inspect tool output and verify important changes independently.</p></div>
      <CopyButton text={meta.session_id} label="Copy session ID" onError={onError} />
    </> : <>
      <label className="search-field page-search"><Search size={16} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Find a conversation…" aria-label="Find a conversation" /></label>
      {filtered.length ? <div className="activity-list">{filtered.map(s => <button key={s.session_id} className="activity-item" onClick={() => onSelect(s.session_id)}>
        <span className="row-icon"><Activity size={18} /></span><span className="activity-item-content"><strong>{s.title}</strong><span className="caption">{basename(s.workspace)}<span className="dot-separator">·</span>{dateLabel(s.updated)}</span></span><StatusBadge status={s.status} /><ChevronRight size={16} />
      </button>)}</div> : <EmptyState icon={<Activity size={24} />} title={query ? 'No matching conversations' : 'Nothing has run yet'}>{query ? 'Try another title or workspace name.' : 'Start a conversation. Real tool calls and outcomes will appear here.'}</EmptyState>}
    </>}
  </div>;
}

export function FilesView({ selected, sessions, onSelect, events, onError }: { selected: string | null; sessions: SessionMeta[]; onSelect: (id: string) => void; events: BackendEvent[]; onError: (message: string) => void }) {
  const [files, setFiles] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all');
  const [content, setContent] = useState<ArtifactContent | null>(null);
  const [reading, setReading] = useState<string | null>(null);
  const selectedRef = useRef(selected); selectedRef.current = selected;
  useEffect(() => { setFiles([]); setContent(null); setReading(null); }, [selected]);
  const watermark = events.filter(e => ['tool_started', 'tool_finished', 'compaction'].includes(e.kind)).length;
  useEffect(() => {
    let alive = true;
    if (!selected) { setLoading(false); return; }
    setLoading(true);
    call('list_artifacts', selected).then(data => { if (alive) setFiles(data); }).catch(e => { if (alive) onError(String(e)); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [selected, watermark, onError]);
  const filtered = files.filter(f => filter === 'all' || f.kind === filter);
  return <div className="page-content">
    <header className="page-heading"><div className="eyebrow">A LOCAL PAPER TRAIL</div><h1>Files</h1><p>Saved tool inputs, outputs, and context snapshots.</p></header>
    <div className="files-toolbar"><label className="select-field"><span className="caption">Conversation</span><select aria-label="Files conversation" value={selected || ''} onChange={e => onSelect(e.target.value)}><option value="" disabled>Choose a conversation</option>{sessions.map(s => <option key={s.session_id} value={s.session_id}>{s.title}</option>)}</select></label><label className="select-field"><span className="caption">Show</span><select aria-label="File type" value={filter} onChange={e => setFilter(e.target.value)}>{['all', 'Tool output', 'Tool input', 'Tool record', 'Context checkpoint'].map(k => <option value={k} key={k}>{k === 'all' ? 'All files' : k}</option>)}</select></label></div>
    {loading ? <p className="loading-line" role="status">Reading local artifacts…</p> : filtered.length ? <div className="file-list">
      <div className="file-list-heading technical"><span>FILE / SOURCE</span><span>SIZE</span></div>
      {filtered.map(file => <button className="file-row" key={file.id} disabled={reading !== null} onClick={async () => {
        if (!selected) return;
        const requestedSession = selected;
        setReading(file.id);
        try { const result = await call('read_artifact', requestedSession, file.id); if (selectedRef.current === requestedSession) setContent(result); }
        catch (e) { if (selectedRef.current === requestedSession) onError(String(e)); }
        finally { if (selectedRef.current === requestedSession) setReading(null); }
      }}><FileText size={19} /><span className="file-description"><strong>{file.kind}<span className="dot-separator">·</span><code>{file.tool}</code></strong><span className="caption mono">{file.name}</span></span><span className="caption mono">{reading === file.id ? 'Opening…' : bytesLabel(file.bytes)}</span><ArrowUpRight size={15} /></button>)}
    </div> : <EmptyState icon={<Folder size={25} />} title={!selected ? 'Choose a conversation' : 'No saved files here yet'}>{!selected ? 'Each conversation keeps its own inspectable record of the work.' : 'Artifacts appear when tools run or context is compacted. Try another file type if a filter is selected.'}</EmptyState>}
    <div className="local-note"><HardDrive size={16} /><p>Read-only session artifacts, not a workspace file explorer. Files stay on this computer and may contain private code. Previews are limited to 64 KB.</p></div>
    {content && <Dialog title={content.name} onClose={() => setContent(null)} wide><div className="artifact-toolbar"><span className="technical muted">{bytesLabel(content.bytes)} · READ ONLY</span><CopyButton text={content.text} label="Copy file preview" onError={onError} /></div>{content.truncated && <p className="inline-warning">Preview truncated at 64 KB. The complete file remains in the session’s artifacts directory.</p>}<pre className="artifact-content" tabIndex={0}>{content.text || '(Empty file)'}</pre></Dialog>}
  </div>;
}

export function SettingsView({ boot, active, onSave, onError, onKeys, onTerms }: { boot: Bootstrap; active: boolean; onSave: (preferences: Preferences) => Promise<Preferences>; onError: (message: string) => void; onKeys: () => void; onTerms: () => void }) {
  const [workspace, setWorkspace] = useState(boot.preferences.workspace);
  const [saved, setSaved] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { setWorkspace(boot.preferences.workspace); }, [boot.preferences.workspace]);
  useEffect(() => { if (saved) { const timer = setTimeout(() => setSaved(''), 3500); return () => clearTimeout(timer); } }, [saved]);
  const save = async (prefs: Preferences, section: string) => {
    setBusy(true); try { await onSave(prefs); setSaved(section); } catch (e) { onError(String(e)); } finally { setBusy(false); }
  };
  const choices: { value: Theme; label: string; icon: typeof Sun }[] = [{ value: 'light', label: 'Light', icon: Sun }, { value: 'dark', label: 'Dark', icon: Moon }, { value: 'system', label: 'System', icon: Monitor }];
  return <div className="page-content settings-content">
    <header className="page-heading"><div className="eyebrow">MAKE YOURSELF AT HOME</div><h1>Settings</h1><p>A few things to make this space yours.</p></header>
    <section className="settings-section"><div className="settings-label"><h2>Appearance</h2><p>Easy on the eyes, day or night.</p></div><fieldset className="theme-options"><legend className="sr-only">Appearance</legend>{choices.map(({ value, label, icon: Icon }) => <label className={`theme-choice ${boot.preferences.theme === value ? 'is-selected' : ''}`} key={value}><input type="radio" name="theme" value={value} checked={boot.preferences.theme === value} disabled={busy} onChange={() => void save({ ...boot.preferences, theme: value }, 'appearance')} /><span className={`theme-swatch swatch-${value}`} aria-hidden="true"><i /><span><b /><b /><b /></span></span><span><Icon size={15} />{label}{boot.preferences.theme === value && <Check size={14} />}</span></label>)}</fieldset>{saved === 'appearance' && <p className="save-feedback" role="status"><Check size={14} />{boot.desktop ? 'Appearance saved' : 'Preview appearance changed'}</p>}</section>
    <section className="settings-section"><div className="settings-label"><h2>Workspace</h2><p>The starting folder for new conversations. Existing conversations keep their original folder.</p></div><label className="sr-only" htmlFor="workspace-path">Default workspace folder</label><div className="workspace-field"><input id="workspace-path" value={workspace} onChange={e => setWorkspace(e.target.value)} className="text-input mono" placeholder="Choose a local folder" disabled={!boot.desktop} /><button className="button" disabled={!boot.desktop || busy} onClick={async () => { try { const path = await call('choose_workspace'); if (path) setWorkspace(path); } catch (e) { onError(String(e)); } }}><Folder size={16} />Browse</button></div><div className="settings-actions"><button className="button" disabled={!boot.desktop || busy || workspace === boot.preferences.workspace} onClick={() => void save({ ...boot.preferences, workspace }, 'workspace')}>Save folder</button>{saved === 'workspace' && <span className="save-feedback" role="status"><Check size={14} />Folder saved</span>}</div></section>
    <section className="settings-section"><div className="settings-label"><h2>Tools & connections</h2><p>Native file editing and terminal tools are always available.</p></div><label className="switch-row"><span><strong>MCP tools</strong><span>Load your configured MCP servers at the next run.</span></span><input className="switch-input" type="checkbox" role="switch" checked={boot.preferences.use_mcp} disabled={!boot.desktop || busy} onChange={e => void save({ ...boot.preferences, use_mcp: e.target.checked }, 'tools')} /><span className="switch-track" aria-hidden="true" /></label>{saved === 'tools' && <p className="save-feedback" role="status"><Check size={14} />Saved for the next run</p>}<p className="caption settings-explanation">To add a server, ask JevSeek to install a trusted MCP endpoint. Configuration is read at run startup, never reloaded in the middle of a task. Turn this off to recover from an unavailable server.</p></section>
    <LocalModelSetup boot={boot} active={active} onError={onError} />
    <section className="settings-section"><div className="settings-label"><h2>The engine</h2><p>Plain generation. One action at a time.</p></div><div className="engine-window"><div className="engine-title technical"><Settings2 size={14} />BACKEND / V1</div><div className="engine-row"><div><strong>DeepSeek Flash</strong><span>{boot.local_model && boot.local_model.selected !== 'deepseek' ? 'Inactive · Bonsai supplies generation' : 'Argument generation · thinking disabled'}</span></div><span className={`config-state ${boot.providers.deepseek || (boot.local_model && boot.local_model.selected !== 'deepseek') ? 'success' : 'warning'}`}>{boot.providers.deepseek || (boot.local_model && boot.local_model.selected !== 'deepseek') ? <Check size={14} /> : <TriangleAlert size={14} />}{boot.local_model && boot.local_model.selected !== 'deepseek' ? 'Not required' : boot.providers.deepseek ? 'Key configured' : 'Key missing'}</span></div><div className="engine-row"><div><strong>Jev JIT</strong><span>Routes the next action from actual results</span></div><span className={`config-state ${boot.providers.jev ? 'success' : 'warning'}`}>{boot.providers.jev ? <Check size={14} /> : <TriangleAlert size={14} />}{boot.providers.jev ? 'Key configured' : 'Key missing'}</span></div></div><div className="settings-actions"><button className="button" onClick={onKeys} disabled={!boot.desktop}><ShieldCheck size={15} />Manage API keys</button></div><p className="caption settings-explanation">Set up or replace keys securely in Windows Credential Manager. No restart is needed. Saved app keys take precedence over environment keys. Configured means present, not verified; stored values are never shown.</p></section>
    <section className="settings-section"><div className="settings-label"><h2>Runtime & privacy</h2><p>The Windows EXE includes Microsoft WebView2 and its own Python runtime.</p></div><p className="caption">Microsoft Defender SmartScreen is enabled and collects and sends information to Microsoft under its Privacy Statement and Edge Privacy Whitepaper. The bundled browser does not auto-update; install new JevSeek releases for runtime security updates.</p><div className="settings-actions"><button className="button" onClick={onTerms}>Microsoft terms & privacy</button></div></section>
    <div className="local-note"><ShieldCheck size={18} /><p><strong>Local, not sandboxed.</strong> Tools have your account’s permissions. Selected task context is sent to Jev and enabled MCP services, and to DeepSeek only when cloud generation is selected. Session history is saved locally; redaction is best-effort.</p></div>
  </div>;
}
