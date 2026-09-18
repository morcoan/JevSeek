import type { BackendEvent, Status } from './types';

export function mergeEvents(existing: BackendEvent[], incoming: BackendEvent[]): BackendEvent[] {
  const next = [...existing];
  const seen = new Set(existing.filter(e => e.seq !== null).map(e => `${e.session_id}:${e.seq}`));
  for (const event of incoming) {
    if (event.version !== 1) throw new Error('Incompatible backend event version. Update the desktop app.');
    const key = `${event.session_id}:${event.seq}`;
    if (event.seq !== null && seen.has(key)) continue;
    // Progress is ephemeral: keep just the latest count, never generated arguments.
    if (event.kind === 'model_progress') {
      const old = next.findIndex(e => e.kind === 'model_progress' && e.session_id === event.session_id);
      if (old >= 0) next.splice(old, 1);
    }
    next.push(event);
    if (event.seq !== null) seen.add(key);
  }
  return next;
}

export interface ToolAction { id: string; tool: string; target: string; status: 'running' | 'ok' | 'error' | 'uncertain'; start?: BackendEvent; end?: BackendEvent }
export function actionsFrom(events: BackendEvent[]): ToolAction[] {
  const actions = new Map<string, ToolAction>();
  for (const e of events) {
    if (!['tool_started', 'tool_finished', 'tool_uncertain'].includes(e.kind)) continue;
    const d = e.data;
    const action: ToolAction = actions.get(d.call_id) ?? { id: d.call_id, tool: d.tool, target: d.target ?? '', status: 'running' };
    if (e.kind === 'tool_started') action.start = e;
    else { action.end = e; action.target = d.target || action.target;
      action.status = e.kind === 'tool_uncertain' || d.status === 'running' ? 'uncertain' : d.status === 'ok' ? 'ok' : 'error'; }
    actions.set(d.call_id, action);
  }
  return [...actions.values()];
}

export interface Turn { key: string; user?: BackendEvent; events: BackendEvent[]; answer?: BackendEvent }
export function turnsFrom(events: BackendEvent[]): Turn[] {
  const turns: Turn[] = [];
  let turn: Turn = { key: 'initial', events: [] };
  for (const e of events) {
    if (e.kind === 'user') {
      if (turn.user || turn.events.length) turns.push(turn);
      turn = { key: String(e.seq), user: e, events: [] };
    } else if (e.kind !== 'session') {
      turn.events.push(e);
      if (e.kind === 'run_started') turn.answer = undefined;
      if (e.kind === 'final' || e.kind === 'result') turn.answer = e;
    }
  }
  if (turn.user || turn.events.length) turns.push(turn);
  return turns;
}

export const statusLabels: Record<Status, string> = {
  ready: 'Ready', running: 'Running', stopping: 'Stopping', completed: 'Completed',
  needs_input: 'Needs your review', blocked: 'Blocked', cancelled: 'Stopped',
};
export function basename(path: string) { return path.replace(/[\\/]+$/, '').split(/[\\/]/).pop() || 'Choose workspace'; }
export function dateLabel(time?: number) { return time ? new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(time * 1000) : ''; }
export function bytesLabel(bytes: number) { return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`; }
export function progressLabel(events: BackendEvent[]) {
  const last = [...events].reverse().find(e => ['tool_started', 'tool_finished', 'model_started', 'model_progress', 'run_started'].includes(e.kind));
  if (!last) return 'Starting the agent';
  if (last.kind === 'tool_started') return `Running ${last.data.tool}`;
  if (last.data.stage === 'summary') return 'Writing the response';
  if (last.data.stage === 'arguments') return 'Preparing tool arguments';
  return 'Choosing the next action';
}
