import { useCallback, useEffect, useRef, useState } from 'react';
import { call, connect } from './bridge';
import { mergeEvents } from './state';
import type { Active, BackendEvent, Bootstrap, KeyStatus, Preferences, RuntimeTerms, SessionMeta } from './types';

export function useDesktop() {
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const selectedRef = useRef(selected); selectedRef.current = selected;
  const [meta, setMeta] = useState<SessionMeta | null>(null);
  const [events, setEvents] = useState<BackendEvent[]>([]);
  const [active, setActive] = useState<Active | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const cursor = useRef(0);
  const loadId = useRef(0);
  const showError = useCallback((message: string) => setError(message.replace(/^Error: /, '')), []);

  const refreshSessions = useCallback(async () => {
    const response = await call('list_sessions');
    setSessions(response.sessions);
  }, []);

  const load = useCallback(async (id: string | null) => {
    const ticket = ++loadId.current;
    selectedRef.current = id; setSelected(id); setMeta(null); setEvents([]); setError('');
    if (!id) { setLoading(false); return; }
    setLoading(true);
    try {
      const snapshot = await call('get_session', id);
      if (ticket !== loadId.current) return;
      // A poll can deliver events while this snapshot is in flight. Merge, don't overwrite.
      setEvents(current => mergeEvents(snapshot.events, current)); setMeta(snapshot.meta);
    } catch (e) { if (ticket === loadId.current) showError(String(e)); }
    finally { if (ticket === loadId.current) setLoading(false); }
  }, [showError]);

  useEffect(() => {
    let alive = true;
    const init = async () => {
      try {
        const data = await connect(); if (!alive) return;
        setBoot(data); setSessions(data.sessions); setActive(data.active); cursor.current = data.cursor;
      } catch (e) { if (alive) showError(String(e)); }
    };
    void init();
    const lateConnect = () => { void init(); };
    window.addEventListener('pywebviewready', lateConnect);
    return () => { alive = false; window.removeEventListener('pywebviewready', lateConnect); };
  }, [showError]);

  useEffect(() => {
    if (!boot?.desktop) return;
    let alive = true; let timer: number;
    const poll = async () => {
      try {
        const response = await call('poll', cursor.current); if (!alive) return;
        cursor.current = response.cursor; setActive(response.active);
        const incoming = response.events.filter(e => e.session_id === selectedRef.current);
        if (incoming.length) {
          // Validate outside the state updater so protocol errors can be displayed.
          if (incoming.some(e => e.version !== 1)) throw new Error('Incompatible backend event version. Update the desktop app.');
          setEvents(old => mergeEvents(old, incoming));
        }
        for (const e of response.events) {
          if (e.kind === 'desktop_notice') setNotice(e.data.message);
        }
        if (response.reset) {
          setNotice('Reconnected. Reloaded the saved conversation; no tools were replayed.');
          if (selectedRef.current) await load(selectedRef.current);
        }
        if (response.events.some(e => ['user', 'desktop_idle'].includes(e.kind))) {
          await refreshSessions();
          const id = selectedRef.current;
          if (id) {
            const snapshot = await call('get_session', id);
            if (alive && selectedRef.current === id) setMeta(snapshot.meta);
          }
        }
      } catch (e) { if (alive) showError(String(e)); }
      finally { if (alive) timer = window.setTimeout(poll, document.hidden ? 1600 : 500); }
    };
    void poll();
    return () => { alive = false; clearTimeout(timer); };
  }, [boot?.desktop, load, refreshSessions, showError]);

  const save = useCallback(async (prefs: Preferences) => {
    const previous = boot?.preferences;
    setBoot(old => old ? { ...old, preferences: prefs } : old);
    try {
      const saved = boot?.desktop ? await call('save_preferences', prefs) : prefs;
      setBoot(old => old ? { ...old, preferences: saved } : old);
      return saved;
    } catch (error) {
      if (previous) setBoot(old => old ? { ...old, preferences: previous } : old);
      throw error;
    }
  }, [boot?.desktop, boot?.preferences]);

  const start = async (prompt: string | null, acknowledge = false) => {
    const result = await call('start_run', selectedRef.current, prompt, acknowledge);
    setActive({ session_id: result.session_id, stopping: false, started: Date.now() / 1000 });
    await load(result.session_id);
    await refreshSessions();
    return result.session_id;
  };

  return { boot, sessions, selected, meta, events, active, loading, error, notice, load, save, start,
    showError, setNotice, clearError: () => setError(''),
    cancel: async () => { try { const r = await call('cancel_run'); setActive(r.active); } catch (e) { showError(String(e)); } },
    refreshSessions,
    updateKeyStatus: (status: KeyStatus) => setBoot(old => old ? { ...old, ...status } : old),
    updateRuntimeTerms: (terms: RuntimeTerms) => setBoot(old => old ? { ...old, runtime_terms: terms } : old),
  };
}
