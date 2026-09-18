import { useEffect, useState } from 'react';
import { call } from './bridge';
import type { RuntimeTerms as TermsStatus } from './types';

export function RuntimeTerms({ required, onAccept, onClose }: { required: boolean; onAccept: (terms: TermsStatus) => void; onClose: () => void }) {
  const [text, setText] = useState('');
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch('./legal/Microsoft-WebView2-Fixed-Version.txt', { signal: controller.signal }).then(r => {
      if (!r.ok) throw new Error('Terms unavailable'); return r.text();
    }).then(setText).catch(e => { if (e.name !== 'AbortError') setError('The bundled runtime terms could not be loaded. Use a complete JevSeek build.'); });
    return () => controller.abort();
  }, []);
  const link = (url: string) => { call('open_external', url).catch(() => setError('Open the listed Microsoft address in your browser.')); };
  return <div className="dialog-body runtime-terms">
    <p>The standalone Windows build includes Microsoft’s Fixed Version WebView2 Runtime so no separate browser installation is needed. The Microsoft component is governed by the terms below, not a JevSeek open-source license.</p>
    <p className="caption">This software includes Microsoft Defender SmartScreen. It collects and sends end-user information to Microsoft as disclosed in <button className="text-link" onClick={() => link('https://aka.ms/privacy')}>Microsoft’s Privacy Statement</button> and the <button className="text-link" onClick={() => link('https://learn.microsoft.com/en-us/microsoft-edge/privacy-whitepaper#smartscreen')}>Microsoft Edge Privacy Whitepaper</button>. SmartScreen has not been disabled.</p>
    <pre className="runtime-license-text" tabIndex={0} aria-label="Microsoft Fixed Version Runtime license">{text || 'Loading the bundled license…'}</pre>
    {error && <p className="key-error" role="alert">{error}</p>}
    {required && <label className="check-row"><input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} />I have reviewed and agree to the Microsoft WebView2 Runtime terms.</label>}
    <div className="dialog-actions"><button className="button" onClick={onClose}>{required ? 'Exit app' : 'Close'}</button>{required && <button className="button primary-button" disabled={!checked || !text || busy || Boolean(error)} onClick={async () => {
      setBusy(true);
      try { onAccept(await call('accept_runtime_terms', true)); }
      catch { setError('Could not save your choice locally. Try reopening the app.'); }
      finally { setBusy(false); }
    }}>{busy ? 'Saving…' : 'Agree & continue'}</button>}</div>
  </div>;
}
