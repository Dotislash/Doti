import { useEffect, useMemo, useState } from "react";

type ThemeMode = "dark" | "light";

type RuntimeConfig = {
  model: string;
  api_key: string;
  api_base: string;
  temperature: number;
  max_tokens: number;
};

type ModelsResponse = {
  models: string[];
};

type SettingsPanelProps = {
  isOpen: boolean;
  onClose: () => void;
};

const API_BASE = "/api/v1/config";

export function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const [theme, setTheme] = useState<ThemeMode>("dark");
  const [models, setModels] = useState<string[]>([]);
  const [config, setConfig] = useState<RuntimeConfig | null>(null);
  const [apiBaseInput, setApiBaseInput] = useState("");
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [isSavingApi, setIsSavingApi] = useState(false);

  const panelClasses = useMemo(
    () =>
      `absolute right-0 top-0 h-full w-full max-w-md transform border-l border-[var(--border)] bg-[var(--bg-secondary)] shadow-2xl transition-transform duration-300 ease-out ${
        isOpen ? "translate-x-0" : "translate-x-full"
      }`,
    [isOpen],
  );

  useEffect(() => {
    const savedTheme = localStorage.getItem("doti-theme") as ThemeMode | null;
    if (savedTheme === "light" || savedTheme === "dark") {
      setTheme(savedTheme);
      document.documentElement.setAttribute("data-theme", savedTheme);
      return;
    }

    document.documentElement.setAttribute("data-theme", "dark");
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    const loadSettings = async () => {
      try {
        const [configRes, modelsRes] = await Promise.all([
          fetch(API_BASE),
          fetch(`${API_BASE}/models`),
        ]);

        if (configRes.ok) {
          const nextConfig = (await configRes.json()) as RuntimeConfig;
          setConfig(nextConfig);
          setApiBaseInput(nextConfig.api_base ?? "");
          setApiKeyInput(nextConfig.api_key ?? "");
        }

        if (modelsRes.ok) {
          const modelPayload = (await modelsRes.json()) as ModelsResponse;
          setModels(modelPayload.models ?? []);
        }
      } catch {
        // Keep panel usable even if settings fetch fails.
      }
    };

    void loadSettings();
  }, [isOpen]);

  const applyTheme = (nextTheme: ThemeMode) => {
    setTheme(nextTheme);
    document.documentElement.setAttribute("data-theme", nextTheme);
    localStorage.setItem("doti-theme", nextTheme);
  };

  const patchConfig = async (partial: Partial<RuntimeConfig>) => {
    try {
      const response = await fetch(API_BASE, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(partial),
      });

      if (!response.ok) return;

      const updated = (await response.json()) as RuntimeConfig;
      setConfig(updated);
      setApiBaseInput(updated.api_base ?? "");
      setApiKeyInput(updated.api_key ?? "");
    } catch {
      // Ignore save errors for now and keep local values.
    }
  };

  const handleModelChange = (value: string) => {
    if (!config) return;
    const next = { ...config, model: value };
    setConfig(next);
    void patchConfig({ model: value });
  };

  const handleTemperatureChange = (value: number) => {
    if (!config) return;
    const next = { ...config, temperature: value };
    setConfig(next);
    void patchConfig({ temperature: value });
  };

  const handleMaxTokensBlur = () => {
    if (!config) return;
    void patchConfig({ max_tokens: config.max_tokens });
  };

  const handleApiSave = async () => {
    setIsSavingApi(true);
    await patchConfig({ api_base: apiBaseInput, api_key: apiKeyInput });
    setIsSavingApi(false);
  };

  return (
    <div
      className={`fixed inset-0 z-50 transition-opacity duration-300 ${
        isOpen ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
      }`}
      aria-hidden={!isOpen}
    >
      <button
        type="button"
        aria-label="Close settings"
        onClick={onClose}
        className={`absolute inset-0 bg-black/45 transition-opacity duration-300 ${
          isOpen ? "opacity-100" : "opacity-0"
        }`}
      />

      <section className={panelClasses} role="dialog" aria-modal="true" aria-label="Settings panel">
        <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
          <h2 className="text-sm font-semibold tracking-wide text-[var(--text-primary)]">Settings</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-[var(--text-muted)] transition hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
            aria-label="Close"
          >
            X
          </button>
        </div>

        <div className="h-[calc(100%-57px)] space-y-6 overflow-y-auto px-5 py-5">
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Appearance</h3>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => applyTheme("dark")}
                className={`rounded-md border px-3 py-2 text-sm transition ${
                  theme === "dark"
                    ? "border-[var(--accent)] bg-[var(--accent)]/20 text-[var(--text-primary)]"
                    : "border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
                }`}
              >
                Dark
              </button>
              <button
                type="button"
                onClick={() => applyTheme("light")}
                className={`rounded-md border px-3 py-2 text-sm transition ${
                  theme === "light"
                    ? "border-[var(--accent)] bg-[var(--accent)]/20 text-[var(--text-primary)]"
                    : "border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
                }`}
              >
                Light
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Model</h3>
            <select
              value={config?.model ?? ""}
              onChange={(e) => handleModelChange(e.target.value)}
              className="w-full rounded-md border border-[var(--border)] bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition focus:border-[var(--accent)]"
            >
              {!config?.model && <option value="">Loading models...</option>}
              {models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Parameters</h3>

            <div className="space-y-1.5">
              <label className="flex items-center justify-between text-sm text-[var(--text-secondary)]">
                <span>Temperature</span>
                <span className="text-[var(--text-primary)]">{(config?.temperature ?? 0).toFixed(1)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={config?.temperature ?? 0}
                onChange={(e) => handleTemperatureChange(Number(e.target.value))}
                className="w-full accent-[var(--accent)]"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm text-[var(--text-secondary)]">Max Tokens</label>
              <input
                type="number"
                min={1}
                value={config?.max_tokens ?? 0}
                onChange={(e) => {
                  if (!config) return;
                  setConfig({ ...config, max_tokens: Number(e.target.value) || 0 });
                }}
                onBlur={handleMaxTokensBlur}
                className="w-full rounded-md border border-[var(--border)] bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition focus:border-[var(--accent)]"
              />
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">API</h3>

            <div className="space-y-1.5">
              <label className="text-sm text-[var(--text-secondary)]">API Base</label>
              <input
                type="text"
                value={apiBaseInput}
                onChange={(e) => setApiBaseInput(e.target.value)}
                className="w-full rounded-md border border-[var(--border)] bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition focus:border-[var(--accent)]"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm text-[var(--text-secondary)]">API Key</label>
              <input
                type="password"
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                className="w-full rounded-md border border-[var(--border)] bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition focus:border-[var(--accent)]"
              />
            </div>

            <button
              type="button"
              onClick={handleApiSave}
              disabled={isSavingApi}
              className="w-full rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-medium text-white transition hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSavingApi ? "Saving..." : "Save API Settings"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
