import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Check, ChevronRight, Copy, LoaderCircle, Square, X, TriangleAlert, CircleCheck, CirclePause, ArrowUpRight, Terminal, FileText, Braces } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { call, copyText } from './bridge';
import { actionsFrom, statusLabels, type ToolAction } from './state';
import type { BackendEvent, Status } from './types';

export function BrandMark({ large = false }: { large?: boolean }) {
  return <svg className={large ? 'brand-mark large' : 'brand-mark'} viewBox="0 0 40 40" fill="none" aria-hidden="true">
    <rect x="1" y="1" width="38" height="38" rx="8" fill="var(--pink)" />
    <path d="M10 10h20v13h-7v7H10v-7h7v-6h-7z" fill="var(--on-pink)" /><path d="M10 10h7v7h-7z" fill="var(--canvas)" />
  </svg>;
}

export function StatusBadge({ status }: { status: Status }) {
  const Icon = status === 'completed' ? CircleCheck : status === 'running' || status === 'stopping' ? LoaderCircle : status === 'needs_input' || status === 'blocked' ? TriangleAlert : CirclePause;
  return <span className={`status status-${status}`}><Icon size={13} className={status === 'running' || status === 'stopping' ? 'spin' : ''} />{statusLabels[status] || status}</span>;
}

export function EmptyState({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon">{icon}</div><h2>{title}</h2><p>{children}</p></div>;
}

export function CopyButton({ text, label = 'Copy response', onError }: { text: string; label?: string; onError?: (message: string) => void }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  return <button className="quiet-button copy-button" aria-label={copied ? 'Copied' : label} onClick={async () => {
    try { await copyText(text); setCopied(true); timer.current = window.setTimeout(() => setCopied(false), 1800); }
    catch (e) { onError?.(String(e)); }
  }}>{copied ? <Check size={14} /> : <Copy size={14} />}<span>{copied ? 'Copied' : 'Copy'}</span></button>;
}

export function Markdown({ text, onError }: { text: string; onError: (message: string) => void }) {
  return <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml components={{
    a: ({ href, children }) => <a href={href} onClick={e => { e.preventDefault(); if (href) call('open_external', href).catch(err => onError(String(err))); }}>{children}<ArrowUpRight size={12} aria-hidden="true" /></a>,
    img: ({ alt }) => <span className="muted">[Image not loaded{alt ? `: ${alt}` : ''}]</span>,
    pre: ({ children }) => <pre tabIndex={0}>{children}</pre>,
    table: ({ children }) => <div className="table-scroll" tabIndex={0}><table>{children}</table></div>,
  }}>{text}</ReactMarkdown></div>;
}

const toolNames: Record<string, string> = { read: 'Reading a file', write: 'Writing a file', edit: 'Editing a file', bash: 'Running a command' };
function ActionRow({ action, active }: { action: ToolAction; active: boolean }) {
  const [open, setOpen] = useState(false);
  const uncertain = action.status === 'uncertain' || (action.status === 'running' && !active);
  const status = uncertain ? 'Review required' : action.status === 'ok' ? 'Completed' : action.status === 'error' ? 'Failed' : 'Running';
  const Icon = uncertain || action.status === 'error' ? TriangleAlert : action.status === 'ok' ? Check : LoaderCircle;
  const ToolIcon = action.tool === 'bash' ? Terminal : action.tool.startsWith('mcp.') ? Braces : FileText;
  return <div className={`tool-row ${uncertain || action.status === 'error' ? 'attention' : ''}`}>
    <button className="tool-row-button" aria-expanded={open} onClick={() => setOpen(!open)}>
      <ToolIcon size={16} className="muted" /><span className="tool-row-label"><span>{toolNames[action.tool] || action.tool}</span><code title={action.target}>{action.target || action.tool}</code></span>
      <span className={`tool-outcome ${uncertain ? 'warning' : action.status}`}><Icon size={13} className={status === 'Running' ? 'spin' : ''} /><span>{status}</span></span>
      <ChevronRight size={14} className={open ? 'rotate' : ''} />
    </button>
    {open && <div className="tool-detail">
      <div className="technical">{action.tool}{action.end?.data.exit_code != null ? ` · exit ${action.end.data.exit_code}` : ''}</div>
      {uncertain && <p className="warning">Effects may have occurred. Inspect the output and current workspace before continuing.</p>}
      <pre tabIndex={0}>{action.end?.data.text || action.end?.data.note || (active ? 'Waiting for the native tool to return. Stop is cooperative; tools may take time to finish.' : 'No completed output was recorded.')}</pre>
      {action.end?.data.arguments?.actual_argument_preview && <details><summary>Validated input</summary><pre tabIndex={0}>{action.end.data.arguments.actual_argument_preview}</pre></details>}
      <p className="caption">Recorded preview. Full saved inputs and outputs are available in Files.</p>
    </div>}
  </div>;
}

export function ToolWindow({ events, active = false, defaultOpen = false }: { events: BackendEvent[]; active?: boolean; defaultOpen?: boolean }) {
  const actions = actionsFrom(events);
  const attention = actions.some(a => ['error', 'uncertain'].includes(a.status) || (!active && a.status === 'running'));
  const [open, setOpen] = useState(defaultOpen);
  if (!actions.length) return null;
  return <section className={`tool-window ${attention ? 'has-attention' : ''}`} aria-label="Tool activity">
    <button className="tool-titlebar" onClick={() => setOpen(!open)} aria-expanded={open}>
      <span className="window-glyph" aria-hidden="true"><Square size={12} /></span><span>Workspace activity</span>
      <span className="tool-count">{actions.length} {actions.length === 1 ? 'action' : 'actions'}</span><ChevronRight size={14} className={open ? 'rotate' : ''} />
    </button>
    {!open && <div className="tool-collapsed"><span>{active ? 'Working in your workspace' : attention ? 'Some actions need your review' : 'Recorded tool calls'}</span>{attention ? <span className="warning"><TriangleAlert size={13} />Review required</span> : <span className="muted">{actions.filter(a => a.status === 'ok').length} completed</span>}</div>}
    {open && <div>{actions.map(action => <ActionRow key={action.id} action={action} active={active} />)}</div>}
  </section>;
}

export function Dialog({ title, children, onClose, wide = false }: { title: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const node = ref.current; const previous = document.activeElement as HTMLElement | null;
    node?.showModal();
    return () => { node?.close(); previous?.focus(); };
  }, []);
  return <dialog ref={ref} className={`dialog ${wide ? 'dialog-wide' : ''}`} aria-labelledby="dialog-title" onCancel={e => { e.preventDefault(); onClose(); }} onClick={e => { if (e.target === e.currentTarget) onClose(); }} onKeyDown={e => {
    if (e.key !== 'Tab') return;
    const items = [...e.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], summary, [tabindex]:not([tabindex="-1"])')].filter(el => el.offsetParent !== null);
    const first = items[0]; const last = items.at(-1);
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
    if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
  }}>
    <div className="dialog-heading"><h2 id="dialog-title">{title}</h2><button autoFocus className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={18} /></button></div>
    {children}
  </dialog>;
}
