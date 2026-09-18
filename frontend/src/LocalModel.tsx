import { useState } from 'react';
import { Check, Download, HardDrive, LoaderCircle } from 'lucide-react';
import { call } from './bridge';
import { bytesLabel } from './state';
import type { Bootstrap } from './types';

export function LocalModelSetup({ boot, active, onError }: { boot: Bootstrap; active: boolean; onError: (message: string) => void }) {
  const [variant, setVariant] = useState('prism');
  const [pending, setPending] = useState(false);
  const local = boot.local_model;
  const busy = pending || Boolean(local?.busy);
  const run = async (action: 'setup' | 'cancel' | 'cloud') => {
    setPending(true);
    try {
      if (action === 'setup') await call('setup_local_model', variant);
      else if (action === 'cancel') await call('cancel_local_setup');
      else await call('use_deepseek');
    } catch (e) { onError(String(e)); }
    finally { setPending(false); }
  };
  const percent = local?.total ? Math.min(100, Math.floor(local.downloaded / local.total * 100)) : null;
  return <section className="settings-section">
    <div className="settings-label"><h2>Generation model</h2><p>Use DeepSeek in the cloud, or run Bonsai on this computer.</p></div>
    <div className="local-model-card">
      <div className="engine-row"><div><strong>{local?.selected === 'prism' ? 'Prism Bonsai 2' : local?.selected === 'crack' ? 'Bonsai 2 CRACK' : 'DeepSeek Flash'}</strong><span>Currently selected · {local?.selected && local.selected !== 'deepseek' ? 'local generation, no DeepSeek key needed' : 'cloud generation'}</span></div><Check size={18} /></div>
      <label className="select-field"><span className="caption">Local model · 27B native ternary</span><select aria-label="Local generation model" value={variant} onChange={e => setVariant(e.target.value)} disabled={busy || active}>
        <option value="prism">Prism Bonsai 2 · official (recommended)</option><option value="crack">Bonsai 2 CRACK · community variant</option>
      </select></label>
      <p className="caption">Downloads about 7.2 GB plus up to 536 MB of runtime files. Allow 10 GB free disk and at least 16 GB RAM. NVIDIA GPU acceleration is chosen when compatible and memory is available; otherwise CPU mode is slower. Existing verified Bonsai files are reused.</p>
      <p className="caption">Setup downloads from Hugging Face and GitHub, verifies SHA-256, starts a private localhost server, and checks tool calling before switching. Model licenses and behavior differ: review the chosen model card.</p>
      <div className="settings-actions"><button className="quiet-button" disabled={!boot.desktop} onClick={() => void call('open_external', variant === 'prism' ? 'https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf' : 'https://huggingface.co/dealignai/Bonsai-2-27B-Ternary-CRACK-GGUF').catch(e => onError(String(e)))}>Model card & license ↗</button></div>
      <div className="settings-actions">
        <button className="button primary-button" disabled={!boot.desktop || busy || active} onClick={() => void run('setup')}><Download size={16} />{local?.phase === 'error' || local?.phase === 'cancelled' ? 'Retry setup & use Bonsai' : 'Set up & use Bonsai'}</button>
        {local?.busy && <button className="button" disabled={pending} onClick={() => void run('cancel')}>Cancel setup</button>}
        {local?.selected !== 'deepseek' && local && <button className="button" disabled={busy || active} onClick={() => void run('cloud')}>Switch to DeepSeek</button>}
      </div>
      {local && <div className="local-model-progress">
        <p role="status">{local.busy ? <LoaderCircle size={15} className="spin" /> : <HardDrive size={15} />}{local.message}</p>
        {local.busy && <><progress aria-label="Local model setup progress" max={100} value={percent ?? undefined} /><span className="caption mono">{percent !== null ? `${percent}% · ${bytesLabel(local.downloaded)} / ${bytesLabel(local.total)}` : 'Preparing…'}{local.speed > 0 ? ` · ${bytesLabel(local.speed)}/s` : ''}</span></>}
      </div>}
    </div>
    <p className="caption settings-explanation"><strong>Not fully offline:</strong> Jev still needs its API key and receives task context for routing. Bonsai replaces DeepSeek only. No silent cloud fallback. Local generation can be less reliable; tool validation stays enabled.</p>
  </section>;
}
