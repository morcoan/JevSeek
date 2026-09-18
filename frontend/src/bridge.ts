import type { Bootstrap, BridgeMethods } from './types';

export async function call<K extends keyof BridgeMethods>(method: K, ...args: Parameters<BridgeMethods[K]>): Promise<Extract<Awaited<ReturnType<BridgeMethods[K]>>, { ok: true }>['data']> {
  const bridge = window.pywebview?.api;
  if (!bridge) throw new Error('This is a browser preview. Open the desktop app to run the agent.');
  const fn = bridge[method] as (...values: Parameters<BridgeMethods[K]>) => ReturnType<BridgeMethods[K]>;
  const result = await fn(...args);
  if (!result.ok) throw new Error(result.error);
  return result.data as Extract<Awaited<ReturnType<BridgeMethods[K]>>, { ok: true }>['data'];
}

export async function connect(): Promise<Bootstrap> {
  if (!window.pywebview?.api) {
    await new Promise<void>(resolve => {
      const done = () => { clearTimeout(timer); window.removeEventListener('pywebviewready', done); resolve(); };
      const timer = window.setTimeout(done, 1400);
      window.addEventListener('pywebviewready', done, { once: true });
    });
  }
  if (window.pywebview?.api) return call('bootstrap');
  return {
    desktop: false, sessions: [], unreadable: 0, active: null, cursor: 0,
    preferences: { theme: 'system', workspace: '', use_mcp: true },
    providers: { deepseek: false, jev: false },
    key_setup: { supported: false, storage: 'Unavailable', sources: { deepseek: 'missing', jev: 'missing' }, error: null },
  };
}

export async function copyText(text: string) {
  if (navigator.clipboard?.writeText) {
    try { await navigator.clipboard.writeText(text); return; } catch { /* Native engines can restrict clipboard. */ }
  }
  const input = document.createElement('textarea');
  input.value = text; input.style.position = 'fixed'; input.style.opacity = '0';
  document.body.append(input); input.select();
  const copied = document.execCommand('copy'); input.remove();
  if (!copied) throw new Error('Could not copy. Select the text and copy it manually.');
}
