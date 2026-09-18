import { useEffect, useMemo, useRef, useState } from 'react';
import { Activity, ArrowDown, ArrowRight, Braces, Bug, Check, ChevronDown, ChevronRight, CircleHelp, FileCode2, Folder, HardDrive, LoaderCircle, Menu, MessageSquare, MoreHorizontal, PanelLeftClose, Plus, Search, Settings2, ShieldCheck, TriangleAlert, X } from 'lucide-react';
import { call } from './bridge';
import { BrandMark, CopyButton, Dialog, Markdown, StatusBadge, ToolWindow } from './components';
import { Composer } from './Composer';
import { KeySetup } from './KeySetup';
import { RuntimeTerms } from './RuntimeTerms';
import { ActivityView, FilesView, SettingsView } from './Views';
import { useDesktop } from './useDesktop';
import { basename, dateLabel, progressLabel, turnsFrom } from './state';
import type { View } from './types';

const starters = [
  { icon: FileCode2, title: 'Explore a project', hint: 'Get the lay of the land', prompt: 'Explore this workspace and explain how the project is organized. Read only; don’t change any files.' },
  { icon: Bug, title: 'Find & fix a bug', hint: 'Turn a snag into progress', prompt: 'Help me investigate a bug in this workspace. First, ask me what is going wrong.' },
  { icon: Braces, title: 'Build something', hint: 'Start with a small idea', prompt: 'I’d like to build something in this workspace. Help me clarify the requirements before making changes.' },
];

export default function App() {
  const app = useDesktop();
  const [view, setView] = useState<View>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [narrow, setNarrow] = useState(() => window.matchMedia('(max-width: 719px)').matches);
  const [search, setSearch] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);
  const [review, setReview] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [keySetupOpen, setKeySetupOpen] = useState(false);
  const [termsOpen, setTermsOpen] = useState(false);
  const offeredKeySetup = useRef(false);
  const [showJump, setShowJump] = useState(false);
  const [activityDetail, setActivityDetail] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const atBottom = useRef(true);
  const scrollPositions = useRef<Record<string, number>>({});
  const [compacting, setCompacting] = useState(false);
  const boot = app.boot;
  const key = app.selected || 'new';
  const draft = drafts[key] || '';
  const isRunning = Boolean(app.active && app.active.session_id === app.selected);
  const workspace = app.meta?.workspace || boot?.preferences.workspace || '';
  const turns = useMemo(() => turnsFrom(app.events), [app.events]);
  const welcome = !app.selected;
  const needsKeys = Boolean(boot?.desktop && (((!boot.local_model || boot.local_model.selected === 'deepseek') && !boot.providers.deepseek) || !boot.providers.jev));
  const needsTerms = Boolean(boot?.runtime_terms?.required && !boot.runtime_terms.accepted);

  useEffect(() => {
    if (boot?.desktop && boot.key_setup.supported && needsKeys && !needsTerms && !offeredKeySetup.current) {
      offeredKeySetup.current = true; setKeySetupOpen(true);
    }
  }, [boot?.desktop, boot?.key_setup.supported, needsKeys, needsTerms]);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 719px)');
    const changed = () => { setNarrow(media.matches); if (!media.matches) setMobileOpen(false); };
    media.addEventListener('change', changed);
    return () => media.removeEventListener('change', changed);
  }, []);

  useEffect(() => {
    const mode = boot?.preferences.theme || 'system';
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const apply = () => { document.documentElement.dataset.theme = mode === 'system' ? media.matches ? 'dark' : 'light' : mode; };
    apply(); media.addEventListener('change', apply); return () => media.removeEventListener('change', apply);
  }, [boot?.preferences.theme]);

  const newConversation = () => { setView('chat'); setMobileOpen(false); void app.load(null); requestAnimationFrame(() => inputRef.current?.focus()); };
  const navigate = (next: View) => { setView(next); setMobileOpen(false); if (next === 'activity') setActivityDetail(false); };
  const setDraft = (value: string) => setDrafts(old => ({ ...old, [key]: value }));

  useEffect(() => {
    const keyboard = (e: KeyboardEvent) => {
      if (document.querySelector('dialog[open]')) return;
      if (e.ctrlKey || e.metaKey) {
        if (e.key.toLowerCase() === 'n') { e.preventDefault(); newConversation(); }
        if (e.key === ',') { e.preventDefault(); navigate('settings'); }
        if (e.key.toLowerCase() === 'k') { e.preventDefault(); setSidebarOpen(true); setMobileOpen(true); setSearchOpen(true); }
      }
      if (e.key === 'Escape') setMobileOpen(false);
    };
    window.addEventListener('keydown', keyboard); return () => window.removeEventListener('keydown', keyboard);
  });

  useEffect(() => {
    const sidebar = sidebarRef.current;
    if (!mobileOpen || !narrow || !sidebar) return;
    const previous = document.activeElement as HTMLElement | null;
    sidebar.querySelector<HTMLElement>('button')?.focus();
    const trap = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      const items = [...sidebar.querySelectorAll<HTMLElement>('button:not(:disabled), input, a[href]')].filter(el => el.offsetParent !== null);
      const first = items[0]; const last = items.at(-1);
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    };
    sidebar.addEventListener('keydown', trap);
    return () => { sidebar.removeEventListener('keydown', trap); previous?.focus(); };
  }, [mobileOpen, narrow]);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node || view !== 'chat') return;
    if (atBottom.current) node.scrollTop = node.scrollHeight;
    else setShowJump(true);
  }, [app.events, view, app.loading]);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    const positionKey = `${view}:${key}`;
    const saved = scrollPositions.current[positionKey];
    node.scrollTop = saved ?? (view === 'chat' && app.selected ? node.scrollHeight : 0);
    atBottom.current = saved == null || node.scrollHeight - node.scrollTop - node.clientHeight < 100;
    setShowJump(false);
  }, [key, view, app.selected]);

  useEffect(() => {
    if (!app.notice) return;
    const timer = setTimeout(() => app.setNotice(''), 6500); return () => clearTimeout(timer);
  }, [app.notice, app.setNotice]);

  const submit = async (ack = false, resume = false) => {
    if (sending || app.active || (!resume && !draft.trim())) return;
    if (needsKeys && boot?.key_setup.supported) { setKeySetupOpen(true); return; }
    if (app.meta?.pending && !ack) { setAcknowledged(false); setReview(true); return; }
    const sentDraft = draft; const sentKey = key;
    setSending(true); app.clearError(); setReview(false);
    try {
      await app.start(resume ? null : sentDraft, ack);
      setDrafts(old => old[sentKey] === sentDraft ? { ...old, [sentKey]: '' } : old);
      setView('chat'); atBottom.current = true;
    } catch (e) { app.showError(String(e)); }
    finally { setSending(false); }
  };

  const chooseWorkspace = async () => {
    if (app.selected || !boot?.desktop) { navigate('settings'); return; }
    try { const path = await call('choose_workspace'); if (path) await app.save({ ...boot.preferences, workspace: path }); }
    catch (e) { app.showError(String(e)); }
  };

  const openSession = (id: string) => { setView('chat'); setMobileOpen(false); void app.load(id); };
  const reviewActivity = () => { setActivityDetail(true); setView('activity'); };
  const stop = () => { void app.cancel(); };
  const compact = async () => {
    if (!app.selected) return;
    setCompacting(true);
    try { const r = await call('compact_session', app.selected); app.setNotice(r.message); }
    catch (e) { app.showError(String(e)); }
    finally { setCompacting(false); }
  };

  const composer = <Composer value={draft} onChange={setDraft} onSend={() => void submit()} onStop={stop} running={isRunning} stopping={Boolean(app.active?.stopping)} busy={sending || Boolean(app.active) || app.loading} desktop={Boolean(boot?.desktop)} workspace={workspace} mcp={boot?.preferences.use_mcp ?? true} onWorkspace={() => void chooseWorkspace()} onSettings={() => navigate('settings')} welcome={welcome} inputRef={inputRef} />;

  if (!boot && !app.error) return <div className="boot-screen"><BrandMark large /><span className="technical">Opening your workspace…</span><LoaderCircle size={18} className="spin" /></div>;

  return <div className={`app-shell ${sidebarOpen ? '' : 'sidebar-collapsed'} ${mobileOpen ? 'mobile-nav-open' : ''}`}>
    <a href="#main-content" className="skip-link">Skip to content</a>
    {mobileOpen && <button className="sidebar-scrim" onClick={() => setMobileOpen(false)} aria-label="Close navigation" tabIndex={-1} />}
    <aside className="sidebar" ref={sidebarRef} aria-label="Main navigation">
      <div className="sidebar-brand"><button className="brand-button" onClick={newConversation} aria-label="JevSeek home"><BrandMark /><span>JevSeek<span className="brand-period">.</span></span></button><button className="icon-button close-sidebar" aria-label="Collapse navigation" onClick={() => { setSidebarOpen(false); setMobileOpen(false); }}><PanelLeftClose size={17} /></button></div>
      <button className="new-conversation" onClick={newConversation}><Plus size={17} /><span>New conversation</span><kbd>Ctrl N</kbd></button>
      <nav className="primary-nav" aria-label="Workspace"><button className={`nav-item ${view === 'chat' ? 'selected' : ''}`} onClick={() => navigate('chat')} aria-current={view === 'chat' ? 'page' : undefined}><MessageSquare size={17} />Conversation</button><button className={`nav-item ${view === 'activity' ? 'selected' : ''}`} onClick={() => navigate('activity')} aria-current={view === 'activity' ? 'page' : undefined}><Activity size={17} />Activity</button><button className={`nav-item ${view === 'files' ? 'selected' : ''}`} onClick={() => navigate('files')} aria-current={view === 'files' ? 'page' : undefined}><Folder size={17} />Files</button></nav>
      <section className="history-section" aria-label="Saved conversations"><div className="history-heading"><span className="technical">RECENT</span><button className="icon-button" aria-label={searchOpen ? 'Close conversation search' : 'Search conversations'} onClick={() => { setSearchOpen(!searchOpen); setSearch(''); }}><Search size={15} /></button></div>
        {searchOpen && <label className="search-field sidebar-search"><Search size={14} /><input autoFocus aria-label="Search saved conversations" placeholder="Search conversations" value={search} onChange={e => setSearch(e.target.value)} /></label>}
        <div className="history-list">{app.sessions.filter(s => s.title.toLowerCase().includes(search.toLowerCase())).map(s => <button key={s.session_id} className={`history-item ${app.selected === s.session_id ? 'current' : ''}`} title={s.title} onClick={() => openSession(s.session_id)} aria-current={app.selected === s.session_id ? 'true' : undefined}><span>{s.title}</span>{app.active?.session_id === s.session_id && <LoaderCircle size={12} className="spin" />}</button>)}
          {!app.sessions.length && <div className="history-empty"><span>Your next idea starts here.</span><p>Conversations are saved on this computer.</p></div>}
          {search && !app.sessions.some(s => s.title.toLowerCase().includes(search.toLowerCase())) && <p className="history-empty">No conversations found.</p>}
        </div>
      </section>
      <div className="sidebar-bottom"><button className="workspace-switch" onClick={() => void chooseWorkspace()} title={workspace}><span className="workspace-icon"><Folder size={17} /></span><span><span className="caption">Local workspace</span><strong>{basename(workspace)}</strong></span><ChevronDown size={14} /></button><button className={`nav-item ${view === 'settings' ? 'selected' : ''}`} onClick={() => navigate('settings')} aria-current={view === 'settings' ? 'page' : undefined}><Settings2 size={17} />Settings<span className="shortcut">Ctrl ,</span></button></div>
    </aside>
    <div className="main-shell" inert={mobileOpen && narrow ? true : undefined}>
      <header className="topbar"><div className="topbar-left"><button className="icon-button open-sidebar" aria-label="Open navigation" onClick={() => { setSidebarOpen(true); setMobileOpen(true); }}><Menu size={19} /></button><span className="topbar-workspace"><Folder size={14} />{basename(workspace)}</span><ChevronRight size={12} className="breadcrumb-divider" /><span className="topbar-title">{view === 'chat' ? app.meta?.title || 'New conversation' : view[0].toUpperCase() + view.slice(1)}</span></div><div className="topbar-right"><span className="local-indicator"><span />{boot?.desktop ? 'Local workspace' : 'Interface preview'}</span><button className="icon-button" aria-label="Help and keyboard shortcuts" onClick={() => setHelpOpen(true)}><CircleHelp size={17} /></button>{app.selected && <details className="session-menu"><summary className="icon-button" aria-label="Conversation options"><MoreHorizontal size={19} /></summary><div className="menu-panel"><button disabled={!!app.active || compacting} onClick={() => void compact()}><Braces size={15} />{compacting ? 'Compacting…' : 'Compact history'}</button><CopyButton text={app.selected} label="Copy session ID" onError={app.showError} /></div></details>}</div></header>
      {!boot?.desktop && <div className="preview-banner"><span>Browser preview</span> The interface is live; messages do not run a model. Launch <code>python desktop.py</code> to connect.</div>}
      {boot?.unreadable ? <div className="inline-warning">{boot.unreadable} saved {boot.unreadable === 1 ? 'session could' : 'sessions could'} not be read. Damaged logs are never replayed.</div> : null}
      {app.active && !isRunning && <button className="global-run" onClick={() => openSession(app.active!.session_id)}><LoaderCircle size={14} className="spin" /><span>A conversation is {app.active.stopping ? 'stopping' : 'running'} in the background</span><span>View<ArrowRight size={14} /></span></button>}
      {needsKeys && boot?.key_setup.supported && <div className="key-setup-banner"><KeySetupIcon /><span>Add your provider keys to start working. Saved conversations remain available offline.</span><button className="button" onClick={() => setKeySetupOpen(true)}>Set up API keys</button></div>}
      {app.error && <div className="error-banner" role="alert"><TriangleAlert size={17} /><span>{app.error}</span><button className="icon-button" onClick={app.clearError} aria-label="Dismiss error"><X size={16} /></button></div>}
      <main id="main-content" tabIndex={-1} className={`main-content view-${view}`}>
        <div className="content-scroll" ref={scrollRef} onScroll={e => { const el = e.currentTarget; atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100; scrollPositions.current[`${view}:${key}`] = el.scrollTop; if (atBottom.current) setShowJump(false); }}>
          {view === 'chat' && (welcome ? <div className="welcome"><div className="welcome-atmosphere" aria-hidden="true" /><div className="welcome-heading"><div className="welcome-emblem"><BrandMark large /><span className="emblem-spark" aria-hidden="true">+</span></div><div className="eyebrow">A LITTLE SPACE TO MAKE THINGS</div><h1>What would you like<br />to work on?</h1><p>A question, a tricky bug, or your next good idea.</p></div>{composer}<div className="starter-grid">{starters.map(({ icon: Icon, title, hint, prompt }) => <button className="starter" key={title} onClick={() => { setDraft(prompt); inputRef.current?.focus(); }}><Icon size={18} /><strong>{title}</strong><span>{hint}</span><ArrowUpRightSmall /></button>)}</div><div className="welcome-note"><HardDrive size={13} /><span>Your workspace. Your files. A little help along the way.</span></div></div> : <div className="conversation reading-column" aria-busy={app.loading}>
            {app.loading && <div className="loading-line" role="status"><LoaderCircle size={17} className="spin" />Opening saved conversation…</div>}
            {!app.loading && <>
              <div className="conversation-start"><span>LOCAL CONVERSATION</span><span>{dateLabel(app.events[0]?.time)}</span></div>
              {turns.map((turn, index) => {
                const live = isRunning && index === turns.length - 1;
                const errors = turn.events.filter(e => e.kind === 'error');
                return <section className="conversation-turn" key={turn.key}>
                  {turn.user && <div className="user-turn"><div className="message-byline"><span>You</span><time>{dateLabel(turn.user.time)}</time></div><div className="user-message">{turn.user.data.text}</div></div>}
                  <div className="assistant-turn"><div className="assistant-byline"><BrandMark /><strong>JevSeek</strong>{live && <span className="caption">at work</span>}</div>
                    <ToolWindow events={turn.events} active={live} defaultOpen={live} />
                    {turn.events.some(e => e.kind === 'compaction') && <div className="compaction-note"><Braces size={12} />Factual history compacted · original outputs kept in Files</div>}
                    {turn.answer ? <><Markdown text={turn.answer.data.summary || ''} onError={app.showError} /><div className="response-actions"><CopyButton text={turn.answer.data.summary || ''} onError={app.showError} /><button className="quiet-button" onClick={reviewActivity}><Activity size={14} />View activity</button><StatusBadge status={turn.answer.data.status} /></div></> : !live && errors.length > 0 ? <div className="run-error"><TriangleAlert size={17} /><div><strong>{errors.at(-1)?.data.stage === 'cancelled' ? 'Run stopped' : 'This run needs attention'}</strong><p>{errors.at(-1)?.data.message || errors.at(-1)?.data.error}</p><span className="caption">The session is saved. No tool was automatically replayed.</span></div></div> : null}
                    {live && <div className="live-progress" role="status"><span className="progress-pixels" aria-hidden="true"><i /><i /><i /></span><span>{app.active?.stopping ? 'Stopping safely — waiting for the current call' : progressLabel(turn.events)}</span></div>}
                  </div>
                </section>;
              })}
              {isRunning && !turns.length && <p className="loading-line" role="status"><LoaderCircle size={16} className="spin" />Starting the agent…</p>}
              {app.meta?.pending && !isRunning && <div className="review-banner"><TriangleAlert size={19} /><div><strong>An interrupted tool needs your review</strong><p>Its effects may already have happened. Inspect activity and the workspace, then send a follow-up. You’ll be asked to acknowledge this uncertainty.</p><button className="button" onClick={reviewActivity}>Review activity<ArrowRight size={15} /></button></div></div>}
              {!isRunning && !app.meta?.pending && ['blocked', 'cancelled'].includes(app.meta?.status || '') && <div className="resume-row"><span className="caption">Resolve the issue, then continue from saved facts.</span><button className="button" disabled={sending || !!app.active} onClick={() => void submit(false, true)}>Resume run<ArrowRight size={15} /></button></div>}
              {app.meta?.status === 'needs_input' && !isRunning && !app.meta.pending && <div className="needs-input-note"><TriangleAlert size={15} />Needs your review. Send a follow-up to continue.</div>}
            </>}
          </div>)}
          {view === 'activity' && <ActivityView sessions={app.sessions} selected={activityDetail ? app.selected : null} events={app.events} meta={app.meta} active={isRunning} onSelect={id => { void app.load(id); setActivityDetail(true); }} onBack={() => setActivityDetail(false)} onChat={() => setView('chat')} onError={app.showError} />}
          {view === 'files' && <FilesView selected={app.selected} sessions={app.sessions} onSelect={id => void app.load(id)} events={app.events} onError={app.showError} />}
          {view === 'settings' && boot && <SettingsView boot={boot} active={Boolean(app.active)} onSave={app.save} onError={app.showError} onKeys={() => setKeySetupOpen(true)} onTerms={() => setTermsOpen(true)} />}
        </div>
        {view === 'chat' && !welcome && <div className="composer-dock">{showJump && <button className="jump-button button" onClick={() => { const el = scrollRef.current; if (el) el.scrollTop = el.scrollHeight; atBottom.current = true; setShowJump(false); }}><ArrowDown size={14} />Latest activity</button>}{composer}</div>}
      </main>
      <footer className="statusbar"><span><ShieldCheck size={12} />{boot?.desktop ? 'Saved on this computer' : 'Preview only · no backend connected'}</span><span className="engine-label">{boot?.local_model && boot.local_model.selected !== 'deepseek' ? 'Bonsai · local' : 'DeepSeek Flash'}<span>×</span>Jev JIT</span></footer>
    </div>
    {app.notice && <div className="toast" role="status"><Check size={16} /><span>{app.notice}</span><button className="icon-button" onClick={() => app.setNotice('')} aria-label="Dismiss notification"><X size={15} /></button></div>}
    {review && <Dialog title="Continue after interruption?" onClose={() => setReview(false)}><div className="dialog-body"><div className="review-icon"><TriangleAlert size={24} /></div><p>The last tool may have changed files or a connected application before it stopped. Acknowledging does not undo or verify those effects.</p><label className="check-row"><input type="checkbox" checked={acknowledged} onChange={e => setAcknowledged(e.target.checked)} />I inspected the activity and current workspace, and understand the outcome may be uncertain.</label><p className="caption">Your follow-up will be sent with this acknowledgement. The backend will decide the next action from the saved facts.</p><div className="dialog-actions"><button className="button" onClick={() => setReview(false)}>Go back</button><button className="button primary-button" disabled={!acknowledged || sending || !!app.active} onClick={() => void submit(true)}>Acknowledge & send<ArrowRight size={15} /></button></div></div></Dialog>}
    {(termsOpen || needsTerms) && <Dialog title="Microsoft runtime terms" onClose={() => { if (needsTerms) void call('close_app').catch(e => app.showError(String(e))); else setTermsOpen(false); }} wide><RuntimeTerms required={needsTerms} onAccept={terms => { app.updateRuntimeTerms(terms); setTermsOpen(false); }} onClose={() => { if (needsTerms) void call('close_app').catch(e => app.showError(String(e))); else setTermsOpen(false); }} /></Dialog>}
    {keySetupOpen && boot && <Dialog title="Connect your providers" onClose={() => setKeySetupOpen(false)}><KeySetup status={boot} active={Boolean(app.active)} onChange={app.updateKeyStatus} onDone={() => setKeySetupOpen(false)} onLocal={() => { setKeySetupOpen(false); navigate('settings'); }} /></Dialog>}
    {helpOpen && <Dialog title="A quieter way to work" onClose={() => setHelpOpen(false)}><div className="dialog-body"><p>Choose a workspace, describe what you need, and follow the actual tool activity. JevSeek can read, edit, and run code with your account’s permissions.</p><div className="shortcut-list"><span>New conversation<kbd>Ctrl / ⌘ N</kbd></span><span>Find a conversation<kbd>Ctrl / ⌘ K</kbd></span><span>Settings<kbd>Ctrl / ⌘ ,</kbd></span><span>Send a message<kbd>Enter</kbd></span><span>New line<kbd>Shift Enter</kbd></span></div><p className="caption">Stop is cooperative. Native calls may take time to finish. Closing during a run requests a safe stop; close again once it has stopped. Drafts stay in memory while you navigate and are cleared when the app closes.</p><div className="local-note"><ShieldCheck size={17} /><p>No thinking mode or hidden planning layer. Model progress shows stages, not private reasoning or incomplete tool arguments.</p></div></div></Dialog>}
  </div>;
}

function KeySetupIcon() { return <ShieldCheck size={17} aria-hidden="true" />; }
function ArrowUpRightSmall() { return <span className="starter-arrow" aria-hidden="true"><ArrowRight size={14} /></span>; }
