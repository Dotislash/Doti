import { useCallback, useEffect, useState } from "react";
import { MoonStar, ShieldCheck, User, Zap } from "lucide-react";
import { useUiStore } from "@/state/uiStore";

type ThemeMode = "dark" | "light";
type Tab = "appearance" | "providers" | "profile" | "security";

type ProviderModel = {
  alias: string;
  id: string;
  thinking: { mode: string; style: string; default_budget: number; default_level: string };
};

type ProviderInfo = {
  name: string;
  api_base: string | null;
  api_key: string | null;
  model_count: number;
  models: ProviderModel[];
};

type ProfileRole = {
  model: string;
  thinking: { enabled: boolean; budget: number | null; level_openai: string | null };
  context: { max_tokens: number; compression_threshold: number };
};

type ProfileData = {
  name: string;
  description: string;
  primary: ProfileRole | null;
  long_context: ProfileRole | null;
  automation: ProfileRole | null;
};

type SecurityData = {
  tool_approval: string;
  tool_allowlist: string[];
  sandbox_runtime: string;
};

type ModelEntry = { provider: string; alias: string; id: string; ref: string };

const API = "/api/v1";

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = localStorage.getItem("doti-api-token");
  const headers: Record<string, string> = { ...extra };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function authFetch(url: string, init?: RequestInit): Promise<Response> {
  const headers = authHeaders(
    init?.headers ? Object.fromEntries(Object.entries(init.headers as Record<string, string>)) : undefined,
  );
  const res = await fetch(url, { ...init, headers });
  if (res.status === 401) throw new Error("Unauthorized — check API token");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res;
}

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: "appearance", label: "appearance", icon: <MoonStar className="h-4 w-4" /> },
  { key: "providers", label: "providers", icon: <Zap className="h-4 w-4" /> },
  { key: "profile", label: "profile", icon: <User className="h-4 w-4" /> },
  { key: "security", label: "security", icon: <ShieldCheck className="h-4 w-4" /> },
];

const inputCls = "w-full rounded-2xl border border-border bg-background px-4 py-2 text-sm text-foreground outline-none transition focus:border-primary/40 focus:ring-4 focus:ring-primary/10 placeholder:text-muted-foreground shadow-inner-pebble";
const btnPrimary = "rounded-2xl bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground shadow-pebble transition hover:opacity-90 active:scale-95";
const btnSecondary = "rounded-2xl border border-border bg-card px-5 py-2.5 text-sm font-medium text-secondary-foreground shadow-sm transition hover:bg-secondary active:scale-95";

function AppearanceTab() {
  const [theme, setTheme] = useState<ThemeMode>("dark");
  const [apiToken, setApiToken] = useState(localStorage.getItem("doti-api-token") ?? "");
  
  const chatSpacing = useUiStore((s) => s.chatSpacing);
  const setChatSpacing = useUiStore((s) => s.setChatSpacing);

  useEffect(() => {
    const saved = localStorage.getItem("doti-theme") as ThemeMode | null;
    if (saved === "light" || saved === "dark") setTheme(saved);
  }, []);

  const apply = (t: ThemeMode) => {
    setTheme(t);
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem("doti-theme", t);
  };

  const saveToken = (val: string) => {
    setApiToken(val);
    if (val) localStorage.setItem("doti-api-token", val);
    else localStorage.removeItem("doti-api-token");
  };

  return (
    <section className="space-y-8">
      <SectionTitle>appearance</SectionTitle>

      <div className="space-y-3">
        <Label>theme</Label>
        <div className="flex gap-2 p-1 bg-secondary/50 shadow-inner-pebble rounded-3xl w-fit border border-border/50">
          {(["dark", "light"] as const).map((t) => (
            <button
              key={t}
              onClick={() => apply(t)}
              className={`rounded-2xl px-6 py-2 text-sm font-medium transition-all ${
                theme === t
                  ? "bg-background text-primary shadow-pebble border border-border/50"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/80"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <Label>chat spacing</Label>
        <div className="flex gap-2 p-1 bg-secondary/50 shadow-inner-pebble rounded-3xl w-fit border border-border/50">
          {(["compact", "relaxed"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setChatSpacing(s)}
              className={`rounded-2xl px-6 py-2 text-sm font-medium transition-all ${
                chatSpacing === s
                  ? "bg-background text-primary shadow-pebble border border-border/50"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/80"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <Label>api token</Label>
        <p className="text-[12px] text-muted-foreground">required if DOTI_API_TOKEN is set on the server</p>
        <input type="password" placeholder="enter token..." value={apiToken} onChange={(e) => saveToken(e.target.value)} className={inputCls} />
      </div>
    </section>
  );
}

/* ── Providers ── */
function ProvidersTab() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ name: "", api_base: "", api_key: "" });
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ api_base: "", api_key: "" });
  const [addModelFor, setAddModelFor] = useState<string | null>(null);
  const [modelForm, setModelForm] = useState({ alias: "", id: "", thinking_mode: "none" });
  const [loadError, setLoadError] = useState<string | null>(null);
  const [opError, setOpError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const res = await fetch(`${API}/config/providers`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setProviders(data.providers ?? []);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "failed to load");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggle = (name: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const addProvider = async () => {
    if (!addForm.name.trim()) return;
    setOpError(null);
    try {
      await authFetch(`${API}/config/providers/${addForm.name}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_base: addForm.api_base || null, api_key: addForm.api_key || null }),
      });
      setAddForm({ name: "", api_base: "", api_key: "" });
      setShowAdd(false);
      await load();
    } catch (e) { setOpError(e instanceof Error ? e.message : "failed"); }
  };

  const deleteProvider = async (name: string) => {
    setOpError(null);
    try {
      await authFetch(`${API}/config/providers/${name}`, { method: "DELETE" });
      await load();
    } catch (e) { setOpError(e instanceof Error ? e.message : "failed"); }
  };

  const startEdit = (p: ProviderInfo) => {
    setEditingProvider(p.name);
    setEditForm({ api_base: p.api_base ?? "", api_key: "" });
  };

  const saveEdit = async (name: string) => {
    const body: Record<string, unknown> = {};
    if (editForm.api_base) body.api_base = editForm.api_base;
    if (editForm.api_key) body.api_key = editForm.api_key;
    await authFetch(`${API}/config/providers/${name}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setEditingProvider(null);
    await load();
  };

  const addModel = async (provider: string) => {
    if (!modelForm.alias.trim() || !modelForm.id.trim()) return;
    await authFetch(`${API}/config/providers/${provider}/models/${modelForm.alias}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: modelForm.id,
        thinking: { mode: modelForm.thinking_mode, style: "budget", default_budget: 10000, default_level: "medium" },
      }),
    });
    setModelForm({ alias: "", id: "", thinking_mode: "none" });
    setAddModelFor(null);
    await load();
  };

  const deleteModel = async (provider: string, alias: string) => {
    await authFetch(`${API}/config/providers/${provider}/models/${alias}`, { method: "DELETE" });
    await load();
  };

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between">
        <SectionTitle>providers</SectionTitle>
        <button onClick={() => setShowAdd(!showAdd)} className={btnPrimary}>+ add</button>
      </div>

      {showAdd && (
        <Card>
          <input placeholder="name" value={addForm.name} onChange={(e) => setAddForm({ ...addForm, name: e.target.value })} className={inputCls} />
          <input placeholder="api base url" value={addForm.api_base} onChange={(e) => setAddForm({ ...addForm, api_base: e.target.value })} className={inputCls} />
          <input placeholder="api key" type="password" value={addForm.api_key} onChange={(e) => setAddForm({ ...addForm, api_key: e.target.value })} className={inputCls} />
          <div className="flex gap-2">
            <button onClick={addProvider} className={btnPrimary}>save</button>
            <button onClick={() => setShowAdd(false)} className={btnSecondary}>cancel</button>
          </div>
        </Card>
      )}

      {providers.map((p) => (
        <div key={p.name} className="rounded-3xl border border-border bg-card shadow-sm transition-all hover:shadow-md overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 bg-secondary/30">
            <button onClick={() => toggle(p.name)} className="flex flex-1 items-center gap-4 text-left group">
              <div className={`flex items-center justify-center w-8 h-8 rounded-full bg-background border border-border transition-all ${expanded.has(p.name) ? "rotate-90 shadow-inner-pebble" : "group-hover:shadow-pebble"}`}>
                <svg className="h-4 w-4 text-muted-foreground" viewBox="0 0 12 12" fill="none">
                  <path d="M4 2l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div>
                <p className="text-base font-medium text-foreground">{p.name}</p>
                <p className="text-xs text-muted-foreground">{p.api_base || "no base url"} · {p.model_count} model(s)</p>
              </div>
            </button>
            <div className="flex gap-2">
              <button onClick={() => startEdit(p)} className="rounded-full px-3 py-1.5 text-xs font-medium text-foreground bg-secondary hover:bg-primary/10 transition">edit</button>
              <button onClick={() => deleteProvider(p.name)} className="rounded-full px-3 py-1.5 text-xs font-medium text-destructive bg-destructive/10 hover:bg-destructive hover:text-destructive-foreground transition">delete</button>
            </div>
          </div>

          {editingProvider === p.name && (
            <div className="space-y-3 border-t border-border px-6 py-5 bg-card">
              <input placeholder="api base url" value={editForm.api_base} onChange={(e) => setEditForm({ ...editForm, api_base: e.target.value })} className={inputCls} />
              <input placeholder="new api key (optional)" type="password" value={editForm.api_key} onChange={(e) => setEditForm({ ...editForm, api_key: e.target.value })} className={inputCls} />
              <div className="flex gap-2 pt-2">
                <button onClick={() => saveEdit(p.name)} className={btnPrimary}>save changes</button>
                <button onClick={() => setEditingProvider(null)} className={btnSecondary}>cancel</button>
              </div>
            </div>
          )}

          {expanded.has(p.name) && (
            <div className="border-t border-border px-6 py-5">
              <div className="space-y-3">
                {p.models.map((m) => (
                  <div key={m.alias} className="flex items-center justify-between rounded-2xl border border-border bg-background px-4 py-3 shadow-inner-pebble group">
                    <div>
                      <p className="text-sm font-medium text-foreground flex items-center gap-2">
                        <span className="bg-primary/10 text-primary px-2 py-0.5 rounded-full text-xs">{m.alias}</span>
                        <span className="text-muted-foreground">→</span>
                        <span className="text-secondary-foreground">{m.id}</span>
                      </p>
                      <p className="text-xs text-muted-foreground mt-1 ml-1">thinking: {m.thinking.mode}</p>
                    </div>
                    <button onClick={() => deleteModel(p.name, m.alias)} className="opacity-0 group-hover:opacity-100 rounded-full h-8 w-8 flex items-center justify-center text-destructive hover:bg-destructive hover:text-destructive-foreground transition-all">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path></svg>
                    </button>
                  </div>
                ))}

                {addModelFor === p.name ? (
                  <Card dashed>
                    <input placeholder="alias (e.g. fast)" value={modelForm.alias} onChange={(e) => setModelForm({ ...modelForm, alias: e.target.value })} className={inputCls} />
                    <input placeholder="model id (e.g. gpt-4o)" value={modelForm.id} onChange={(e) => setModelForm({ ...modelForm, id: e.target.value })} className={inputCls} />
                    <select value={modelForm.thinking_mode} onChange={(e) => setModelForm({ ...modelForm, thinking_mode: e.target.value })} className={inputCls}>
                      <option value="none">thinking: none</option>
                      <option value="mandatory">thinking: mandatory</option>
                      <option value="budget">thinking: budget</option>
                    </select>
                    <div className="flex gap-2 pt-2">
                      <button onClick={() => addModel(p.name)} className={btnPrimary}>add model</button>
                      <button onClick={() => setAddModelFor(null)} className={btnSecondary}>cancel</button>
                    </div>
                  </Card>
                ) : (
                  <button onClick={() => setAddModelFor(p.name)} className="w-full rounded-2xl border border-dashed border-border px-4 py-3 text-sm font-medium text-muted-foreground transition hover:border-primary/30 hover:bg-primary/5 hover:text-primary">
                    + add model
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      ))}

      {(loadError || opError) && <ErrorBox>{loadError || opError}</ErrorBox>}
      {providers.length === 0 && !loadError && (
        <p className="font-mono text-sm text-[var(--fg-3)]">no providers configured.</p>
      )}
    </section>
  );
}

/* ── Profile ── */
function ProfileTab() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [pRes, mRes] = await Promise.all([fetch(`${API}/config/profile`), fetch(`${API}/config/models`)]);
        if (pRes.ok) setProfile(await pRes.json());
        if (mRes.ok) { const data = await mRes.json(); setModels(data.models ?? []); }
      } catch { /* ignore */ }
    };
    load();
  }, []);

  const save = async () => {
    if (!profile) return;
    setSaving(true);
    setSaveError(null);
    try {
      const res = await authFetch(`${API}/config/profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      setProfile(await res.json());
    } catch (e) { setSaveError(e instanceof Error ? e.message : "failed"); }
    setSaving(false);
  };

  const updateRole = (role: "primary" | "long_context" | "automation", field: string, value: unknown) => {
    if (!profile) return;
    const current = profile[role] ?? {
      model: "", thinking: { enabled: false, budget: null, level_openai: null },
      context: { max_tokens: 200000, compression_threshold: 0.6 },
    };
    const updated = { ...current };
    if (field === "model") updated.model = value as string;
    else if (field === "thinking.enabled") updated.thinking = { ...updated.thinking, enabled: value as boolean };
    else if (field === "thinking.budget") updated.thinking = { ...updated.thinking, budget: value as number };
    else if (field === "context.max_tokens") updated.context = { ...updated.context, max_tokens: value as number };
    setProfile({ ...profile, [role]: updated });
  };

  if (!profile) return <p className="font-mono text-sm text-[var(--fg-3)]">loading...</p>;

  const roleSection = (label: string, role: "primary" | "long_context" | "automation") => {
    const r = profile[role];
    return (
      <div className="space-y-4 rounded-3xl border border-border bg-card p-6 shadow-sm">
        <h3 className="text-base font-medium text-foreground">{label}</h3>
        <div className="space-y-2">
          <Label>model</Label>
          <select value={r?.model ?? ""} onChange={(e) => updateRole(role, "model", e.target.value)} className={inputCls}>
            <option value="">select...</option>
            {models.map((m) => <option key={m.ref} value={m.ref}>{m.ref} ({m.id})</option>)}
          </select>
        </div>
        <div className="flex items-center gap-4 py-1.5">
          <label className="flex items-center gap-3 text-sm font-medium text-muted-foreground group">
            <input type="checkbox" checked={r?.thinking?.enabled ?? false} onChange={(e) => updateRole(role, "thinking.enabled", e.target.checked)} className="peer appearance-none h-5 w-5 rounded border-2 border-border bg-background checked:bg-primary checked:border-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20" />
            <span className="group-hover:text-foreground transition-colors">thinking</span>
          </label>
          {r?.thinking?.enabled && (
            <input type="number" placeholder="budget" value={r?.thinking?.budget ?? 10000} onChange={(e) => updateRole(role, "thinking.budget", Number(e.target.value))} className="w-28 rounded-xl border border-border bg-background px-3 py-1.5 text-sm text-foreground outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10 shadow-inner-pebble" />
          )}
        </div>
        <div className="space-y-1">
          <Label>max tokens</Label>
          <input type="number" value={r?.context?.max_tokens ?? 4096} onChange={(e) => updateRole(role, "context.max_tokens", Number(e.target.value))} className={inputCls} />
        </div>
      </div>
    );
  };

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between">
        <SectionTitle>profile</SectionTitle>
        <button onClick={save} disabled={saving} className={`${btnPrimary} disabled:opacity-50`}>
          {saving ? "saving..." : "save"}
        </button>
      </div>
      {saveError && <ErrorBox>{saveError}</ErrorBox>}

      <div className="space-y-3">
        <div className="space-y-1"><Label>name</Label><input value={profile.name ?? ""} onChange={(e) => setProfile({ ...profile, name: e.target.value })} className={inputCls} /></div>
        <div className="space-y-1"><Label>description</Label><input value={profile.description ?? ""} onChange={(e) => setProfile({ ...profile, description: e.target.value })} className={inputCls} /></div>
      </div>

      {roleSection("primary", "primary")}
      {roleSection("long context", "long_context")}
      {roleSection("automation", "automation")}
    </section>
  );
}

/* ── Security ── */
function SecurityTab() {
  const [security, setSecurity] = useState<SecurityData | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch(`${API}/config/security`);
        if (res.ok) setSecurity(await res.json());
      } catch { /* ignore */ }
    };
    load();
  }, []);

  const save = async () => {
    if (!security) return;
    setSaving(true);
    try {
      await authFetch(`${API}/config/security`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(security),
      });
    } catch { /* ignore */ }
    setSaving(false);
  };

  if (!security) return <p className="font-mono text-sm text-[var(--fg-3)]">loading...</p>;

  const policies = ["ask_first", "auto", "auto_with_allowlist"] as const;

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between">
        <SectionTitle>security</SectionTitle>
        <button onClick={save} disabled={saving} className={`${btnPrimary} disabled:opacity-50`}>
          {saving ? "saving..." : "save"}
        </button>
      </div>

      <div className="space-y-4 rounded-3xl border border-border bg-card p-6 shadow-sm">
        <p className="text-base font-medium text-foreground">tool approval policy</p>
        <div className="space-y-2">
          {policies.map((p) => (
            <label key={p} className="flex items-center gap-3 text-sm font-medium text-muted-foreground group">
              <input type="radio" name="tool_approval" checked={security.tool_approval === p} onChange={() => setSecurity({ ...security, tool_approval: p })} className="peer appearance-none h-5 w-5 rounded-full border-2 border-border bg-background checked:border-primary checked:border-[6px] transition-all focus:outline-none focus:ring-2 focus:ring-primary/20" />
              <span className="group-hover:text-foreground transition-colors">{p.replace(/_/g, " ")}</span>
            </label>
          ))}
        </div>
      </div>

      {security.tool_approval === "auto_with_allowlist" && (
        <div className="space-y-3 rounded-3xl border border-border bg-card p-6 shadow-sm">
          <p className="text-base font-medium text-foreground">tool allowlist</p>
          <p className="text-[12px] text-muted-foreground">comma-separated tool names</p>
          <input
            value={(security.tool_allowlist ?? []).join(", ")}
            onChange={(e) => setSecurity({ ...security, tool_allowlist: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
            className={inputCls}
          />
        </div>
      )}
    </section>
  );
}

/* ── Shared Components ── */
function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-xl font-medium tracking-tight text-foreground">{children}</h2>;
}

function Label({ children }: { children: React.ReactNode }) {
  return <p className="text-sm font-medium text-foreground">{children}</p>;
}

function Card({ children, dashed }: { children: React.ReactNode; dashed?: boolean }) {
  return (
    <div className={`space-y-3 rounded-xl ${dashed ? "border-dashed" : ""} border border-border/40 bg-card p-5`}>
      {children}
    </div>
  );
}

function ErrorBox({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm font-medium text-destructive shadow-sm">
      {children}
    </p>
  );
}

/* ── Main Settings Page ── */
export function SettingsPage({ onBack }: { onBack: () => void }) {
  const [tab, setTab] = useState<Tab>("appearance");

  return (
    <div className="flex h-screen w-full bg-background">
      {/* ── Nav ── */}
      <nav className="flex w-60 flex-col border-r border-border/30 bg-card">
        <div className="flex items-center gap-3 border-b border-border/30 px-5 py-5">
          <button
            onClick={onBack}
            className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground transition hover:bg-secondary hover:text-foreground active:scale-95"
          >
            <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none">
              <path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <span className="text-base font-medium text-foreground tracking-tight">settings</span>
        </div>

        <div className="flex-1 space-y-1 px-3 py-5">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                tab === t.key
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
              }`}
            >
              <div className={`p-1 rounded-lg transition-colors ${
                tab === t.key 
                  ? "text-primary" 
                  : "text-muted-foreground"
              }`}>
                {t.icon}
              </div>
              {t.label}
            </button>
          ))}
        </div>

        <div className="border-t border-border/30 px-5 py-4">
          <p className="text-xs text-muted-foreground">doti v0.1.0</p>
        </div>
      </nav>

      {/* ── Content ── */}
      <main className="scroll-thin flex-1 overflow-y-auto px-10 py-10">
        <div className="mx-auto max-w-2xl">
          {tab === "appearance" && <AppearanceTab />}
          {tab === "providers" && <ProvidersTab />}
          {tab === "profile" && <ProfileTab />}
          {tab === "security" && <SecurityTab />}
        </div>
      </main>
    </div>
  );
}
