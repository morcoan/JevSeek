import { useState } from 'react';
import { ArrowUpRight, Check, KeyRound, LoaderCircle, ShieldCheck, Trash2, TriangleAlert } from 'lucide-react';
import { call } from './bridge';
import type { KeyStatus } from './types';

type Provider = 'deepseek' | 'jev';
const providers: { id: Provider; label: string; url: string }[] = [
  { id: 'deepseek', label: 'DeepSeek', url: 'https://platform.deepseek.com/api_keys' },
  { id: 'jev', label: 'TypeSafe / Jev', url: 'https://console.typesafe.ai/' },
];

export function KeySetup({ status, active, onChange, onDone }: {
  status: KeyStatus; active: boolean; onChange: (status: KeyStatus) => void; onDone: () => void;
}) {
  // Entered values exist only for this form submission. Never use localStorage,
  // drafts, query strings, logs or a read-back bridge method for credentials.
  const [deepseek, setDeepseek] = useState('');
  const [jev, setJev] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [remove, setRemove] = useState<Provider | null>(null);
  const disabled = active || busy || !status.key_setup.supported;
  const submit = async () => {
    const enteredDS = deepseek; const enteredJev = jev;
    setDeepseek(''); setJev(''); setError(''); setMessage(''); setBusy(true);
    try {
      const next = await call('save_keys', enteredDS, enteredJev);
      onChange(next);
      setMessage('Saved securely. Keys are available for your next run; no provider request was made.');
    } catch (e) { setError(String(e).replace(/^Error: /, '')); }
    finally { setBusy(false); }
  };
  return <div className="dialog-body key-setup">
    <div className="key-intro"><span className="key-icon"><KeyRound size={22} /></span><p>Bring your own DeepSeek and TypeSafe keys. No terminal setup or <code>.env</code> editing needed.</p></div>
    <div className="local-note key-security-note"><ShieldCheck size={18} /><p>Saved in <strong>Windows Credential Manager</strong> for your Windows account, not in the project or chat history. Existing keys are never sent back to this form.</p></div>
    {active && <p className="inline-warning">A run is active. Stop it before changing keys.</p>}
    {!status.key_setup.supported && <p className="inline-warning">Secure storage is unavailable here. Open the Windows desktop app to set up keys. No plaintext fallback is used.</p>}
    {(error || status.key_setup.error) && <p className="key-error" role="alert"><TriangleAlert size={16} />{error || status.key_setup.error}</p>}
    <form onSubmit={e => { e.preventDefault(); if (!disabled) void submit(); }} autoComplete="off">
      {providers.map(({ id, label, url }) => <div className="key-field" key={id}>
        <div className="key-field-heading"><label htmlFor={`key-${id}`}>{label} API key</label><button type="button" className="quiet-button" onClick={() => { call('open_external', url).catch(() => setError('Could not open the provider website. Try your browser.')); }}>Get a key<ArrowUpRight size={13} /></button></div>
        <input id={`key-${id}`} type="password" value={id === 'deepseek' ? deepseek : jev}
          onChange={e => id === 'deepseek' ? setDeepseek(e.target.value) : setJev(e.target.value)}
          className="text-input" placeholder={status.providers[id] ? 'Configured · paste a replacement, or leave blank' : 'Paste your API key'}
          autoComplete="off" autoCapitalize="none" spellCheck={false} minLength={8} maxLength={512}
          disabled={disabled} aria-describedby={`key-status-${id}`} />
        <div className="key-field-status" id={`key-status-${id}`}>
          <span className={status.providers[id] ? 'success' : 'muted'}>{status.providers[id] ? <Check size={13} /> : <KeyRound size={13} />}{status.key_setup.sources[id] === 'vault' ? 'Saved in Windows' : status.key_setup.sources[id] === 'environment' ? 'Using an environment key' : 'Not configured'}</span>
          {status.key_setup.sources[id] === 'vault' && <button type="button" className="quiet-button" disabled={disabled} onClick={() => setRemove(id)} aria-label={`Remove saved ${label} key`}><Trash2 size={13} />Remove</button>}
        </div>
      </div>)}
      {remove && <div className="key-removal" role="alert"><p>Remove the saved {remove === 'jev' ? 'TypeSafe / Jev' : 'DeepSeek'} key from this app? This does not revoke it at the provider. An environment key, if present, will still be available.</p><div className="dialog-actions"><button type="button" className="button" onClick={() => setRemove(null)}>Keep key</button><button type="button" className="button" disabled={disabled} onClick={async () => {
        setBusy(true); setError(''); setMessage('');
        try { onChange(await call('remove_key', remove)); setMessage('Saved key removed.'); setRemove(null); }
        catch (e) { setError(String(e).replace(/^Error: /, '')); }
        finally { setBusy(false); }
      }}>Remove saved key</button></div></div>}
      <p className="caption">Blank fields keep existing keys. Saving does not verify access or spend API credits. Your providers bill for requests when you run a task.</p>
      {message && <p className="save-feedback" role="status"><Check size={15} />{message}</p>}
      <div className="dialog-actions"><button type="button" className="button" onClick={onDone}>{status.providers.deepseek && status.providers.jev ? 'Done' : 'Set up later'}</button><button type="submit" className="button primary-button" disabled={disabled || (!deepseek.trim() && !jev.trim())}>{busy ? <LoaderCircle size={15} className="spin" /> : <ShieldCheck size={15} />}{busy ? 'Saving…' : 'Save keys securely'}</button></div>
    </form>
  </div>;
}
