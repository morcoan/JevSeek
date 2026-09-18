export type Status = 'ready' | 'running' | 'stopping' | 'completed' | 'needs_input' | 'blocked' | 'cancelled';
export type Theme = 'system' | 'light' | 'dark';
export type View = 'chat' | 'activity' | 'files' | 'settings';
export interface Preferences { theme: Theme; workspace: string; use_mcp: boolean }
export interface SessionMeta {
  session_id: string; title: string; workspace: string; status: Status;
  updated: number; pending: boolean; trailing: boolean;
}
// The v1 contract deliberately permits future event kinds and optional fields.
export interface BackendEvent {
  version: number; session_id: string; seq: number | null; time?: number;
  kind: string; data: Record<string, any>;
}
export interface Active { session_id: string; stopping: boolean; started: number }
export interface Snapshot { meta: SessionMeta; events: BackendEvent[]; pending: BackendEvent[] }
export interface KeyStatus {
  providers: { deepseek: boolean; jev: boolean };
  key_setup: {
    supported: boolean; storage: string;
    sources: Record<'deepseek' | 'jev', 'vault' | 'environment' | 'missing'>;
    error: string | null;
  };
}
export interface RuntimeTerms { required: boolean; accepted: boolean; version: string }
export interface Bootstrap extends KeyStatus {
  runtime_terms?: RuntimeTerms;
  sessions: SessionMeta[]; unreadable: number; preferences: Preferences;
  active: Active | null; cursor: number; desktop: boolean;
}
export interface Poll { cursor: number; active: Active | null; reset: boolean; events: BackendEvent[] }
export interface Artifact { id: string; name: string; kind: string; tool: string; time: number; bytes: number }
export interface ArtifactContent { name: string; text: string; truncated: boolean; bytes: number }
export type Envelope<T> = { ok: true; data: T } | { ok: false; error: string };
export interface BridgeMethods {
  bootstrap(): Promise<Envelope<Bootstrap>>;
  get_key_status(): Promise<Envelope<KeyStatus>>;
  accept_runtime_terms(accepted: boolean): Promise<Envelope<RuntimeTerms>>;
  close_app(): Promise<Envelope<boolean>>;
  save_keys(deepseek: string, jev: string): Promise<Envelope<KeyStatus>>;
  remove_key(provider: 'deepseek' | 'jev'): Promise<Envelope<KeyStatus>>;
  list_sessions(): Promise<Envelope<{ sessions: SessionMeta[]; unreadable: number }>>;
  get_session(id: string): Promise<Envelope<Snapshot>>;
  poll(cursor: number): Promise<Envelope<Poll>>;
  save_preferences(preferences: Preferences): Promise<Envelope<Preferences>>;
  choose_workspace(): Promise<Envelope<string | null>>;
  start_run(id: string | null, prompt: string | null, acknowledge: boolean): Promise<Envelope<{ session_id: string }>>;
  cancel_run(): Promise<Envelope<{ active: Active | null }>>;
  compact_session(id: string): Promise<Envelope<{ message: string }>>;
  list_artifacts(id: string): Promise<Envelope<Artifact[]>>;
  read_artifact(id: string, artifact: string): Promise<Envelope<ArtifactContent>>;
  open_external(url: string): Promise<Envelope<boolean>>;
}
declare global { interface Window { pywebview?: { api: BridgeMethods } } }
