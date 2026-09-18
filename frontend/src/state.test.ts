import { describe, expect, it } from 'vitest';
import { actionsFrom, basename, mergeEvents, progressLabel, turnsFrom } from './state';
import type { BackendEvent } from './types';

const event = (seq: number | null, kind: string, data = {}): BackendEvent => ({ version: 1, session_id: 'one', seq, kind, data });

describe('v1 event projections', () => {
  it('deduplicates replayed persisted events, not different sessions', () => {
    const a = event(1, 'user', { text: 'hello' });
    expect(mergeEvents([a], [a])).toHaveLength(1);
    expect(mergeEvents([a], [{ ...a, session_id: 'two' }])).toHaveLength(2);
  });
  it('bounds transient progress without exposing a generated draft', () => {
    let events: BackendEvent[] = [];
    for (let i = 0; i < 100; i++) events = mergeEvents(events, [event(null, 'model_progress', { characters: i })]);
    expect(events).toHaveLength(1); expect(events[0].data.characters).toBe(99);
  });
  it('rejects incompatible event versions, accepts future kinds', () => {
    expect(() => mergeEvents([], [{ ...event(1, 'new-kind'), version: 2 }])).toThrow();
    expect(mergeEvents([], [event(1, 'new-kind')])).toHaveLength(1);
  });
  it('does not duplicate final + result as two assistant messages', () => {
    const events = [event(1, 'user', { text: 'a' }), event(2, 'final', { summary: 'Done', status: 'completed' }), event(null, 'result', { summary: 'Done', status: 'completed' }), event(3, 'user', { text: 'b' })];
    const turns = turnsFrom(events);
    expect(turns).toHaveLength(2); expect(turns[0].answer?.data.summary).toBe('Done'); expect(turns[1].answer).toBeUndefined();
  });
  it('does not show a stale stopped answer while a resumed attempt runs', () => {
    const events = [event(1, 'user', { text: 'Read a file' }), event(null, 'result', { status: 'cancelled', summary: 'Stopped' }), event(2, 'run_started')];
    expect(turnsFrom(events)[0].answer).toBeUndefined();
  });
  it('never claims unfinished or soft-timeout calls succeeded', () => {
    const events = [event(1, 'tool_started', { tool: 'bash', call_id: 'a' }), event(2, 'tool_finished', { tool: 'bash', call_id: 'a', status: 'running', exit_code: -1 })];
    expect(actionsFrom(events)[0].status).toBe('uncertain');
    expect(actionsFrom(events.slice(0, 1))[0].status).toBe('running');
  });
  it('preserves errors and acknowledgement instead of erasing failures', () => {
    const events = [event(1, 'tool_started', { tool: 'read', call_id: 'a' }), event(2, 'tool_finished', { tool: 'read', call_id: 'a', status: 'error', text: 'Missing' })];
    expect(actionsFrom(events)[0].status).toBe('error');
    events.push(event(3, 'tool_uncertain', { tool: 'read', call_id: 'a', note: 'Acknowledged' }));
    expect(actionsFrom(events)[0].status).toBe('uncertain');
  });
  it('uses factual model stages and handles cross-platform paths', () => {
    expect(progressLabel([event(1, 'model_started', { stage: 'summary' })])).toBe('Writing the response');
    expect(basename('C:\\Users\\dev\\project')).toBe('project');
    expect(basename('/home/dev/project/')).toBe('project');
  });
});
