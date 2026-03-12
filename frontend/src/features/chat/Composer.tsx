import { type FormEvent, type KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

type SlashCommand = { command: string; description: string; needsArgs: boolean };

const SLASH_COMMANDS: SlashCommand[] = [
  { command: "/model", description: "switch model", needsArgs: true },
  { command: "/think", description: "toggle thinking", needsArgs: false },
  { command: "/executor", description: "manage executor", needsArgs: true },
  { command: "/thread", description: "create thread", needsArgs: true },
  { command: "/clear", description: "clear display", needsArgs: false },
  { command: "/help", description: "show commands", needsArgs: false },
];

type ModelEntry = { ref: string; provider: string; alias: string; id: string };
type ExecutorInfo = { id: string; status: string };

type ComposerProps = {
  onSend: (content: string) => void;
  onSlashCommand?: (command: string, args: string) => void;
  onModelChange?: (modelRef: string) => void;
  onThinkingToggle?: (enabled: boolean) => void;
  onExecutorClick?: () => void;
  activeExecutor?: ExecutorInfo | null;
  thinkingEnabled?: boolean;
  disabled?: boolean;
};

export function Composer({
  onSend,
  onSlashCommand,
  onModelChange,
  onThinkingToggle,
  onExecutorClick,
  activeExecutor = null,
  thinkingEnabled = false,
  disabled = false,
}: ComposerProps) {
  const [value, setValue] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  const [slashDismissed, setSlashDismissed] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  // Models
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [showSettings, setShowSettings] = useState(false);

  const loadModels = useCallback(async () => {
    try {
      const token = localStorage.getItem("doti-api-token");
      const res = await fetch("/api/v1/config/models", {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!res.ok) return;
      const data = (await res.json()) as { models?: ModelEntry[] };
      const next = data.models ?? [];
      setModels(next);
      if (next.length > 0) setSelectedModel((p) => p || next[0]?.ref || "");
    } catch {
      setModels([]);
    }
  }, []);

  useEffect(() => { void loadModels(); }, [loadModels]);

  const handleModelChange = useCallback((ref: string) => {
    setSelectedModel(ref);
    onModelChange?.(ref);
  }, [onModelChange]);

  // Slash commands
  const isSlash = value.startsWith("/");
  const token = isSlash ? (value.slice(1).split(/\s+/, 1)[0] ?? "").toLowerCase() : "";
  const filtered = SLASH_COMMANDS.filter((c) => c.command.slice(1).startsWith(token));
  const paletteOpen = isSlash && !slashDismissed && filtered.length > 0;
  const canSend = !disabled && value.trim().length > 0;

  // Auto-resize textarea
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  useEffect(() => { if (!value.startsWith("/")) setSlashDismissed(false); }, [value]);
  useEffect(() => { setActiveIdx(0); }, [token]);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    if (trimmed.startsWith("/") && onSlashCommand) {
      const [cmd = "", ...rest] = trimmed.split(/\s+/);
      onSlashCommand(cmd, rest.join(" "));
      setValue("");
      setSlashDismissed(false);
      return;
    }
    onSend(trimmed);
    setValue("");
    setSlashDismissed(false);
  };

  const selectCommand = (item: SlashCommand) => {
    if (!onSlashCommand || item.needsArgs) {
      setValue(`${item.command} `);
      setActiveIdx(0);
      return;
    }
    onSlashCommand(item.command, "");
    setValue("");
    setSlashDismissed(false);
    setActiveIdx(0);
  };

  const handleSubmit = (e: FormEvent) => { e.preventDefault(); submit(); };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Escape" && paletteOpen) { e.preventDefault(); setSlashDismissed(true); return; }
    if (paletteOpen && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      e.preventDefault();
      setActiveIdx((p) => (p + (e.key === "ArrowDown" ? 1 : -1) + filtered.length) % filtered.length);
      return;
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (paletteOpen) {
        const sel = filtered[activeIdx];
        if (sel) { selectCommand(sel); return; }
      }
      if (canSend) submit();
    }
  };

  const hasExec = !!activeExecutor;
  const execDot = !hasExec ? "bg-muted-foreground" : activeExecutor.status === "running" ? "bg-green-500" : "bg-primary";

  return (
    <form onSubmit={handleSubmit} className="shrink-0 px-5 pb-5 pt-2 w-full">
      <div className="relative mx-auto max-w-3xl rounded-2xl border border-border/40 bg-card shadow-pebble transition-all focus-within:border-primary/30 focus-within:ring-2 focus-within:ring-primary/10">

        {/* ── Slash palette ── */}
        {paletteOpen && (
          <div className="absolute bottom-full left-0 right-0 z-20 mb-2 max-h-64 overflow-y-auto scroll-thin rounded-xl border border-border/40 bg-popover p-1.5 shadow-pebble-lg">
            {filtered.map((item, idx) => (
              <button
                key={item.command}
                type="button"
                onMouseDown={(e) => { e.preventDefault(); selectCommand(item); }}
                className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-all ${
                  idx === activeIdx
                    ? "bg-primary text-primary-foreground"
                    : "text-foreground hover:bg-secondary/60"
                }`}
              >
                <span className="font-medium">{item.command}</span>
                <span className={`text-xs ${idx === activeIdx ? "text-primary-foreground/80" : "text-muted-foreground"}`}>{item.description}</span>
              </button>
            ))}
          </div>
        )}

        {/* ── Toolbar ── */}
        <div className="flex items-center gap-2 border-b border-border/20 px-4 py-2 relative">
          
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className={`flex items-center gap-2 rounded-2xl px-3 py-1.5 text-xs font-medium transition-all ${
                showSettings 
                  ? "bg-primary text-primary-foreground shadow-pebble" 
                  : "bg-background text-muted-foreground hover:bg-secondary hover:text-foreground shadow-sm"
              }`}
            >
              <span className="truncate max-w-[140px]">
                {models.find(m => m.ref === selectedModel)?.alias || "select model"}
              </span>
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none" className={`transition-transform duration-300 ${showSettings ? 'rotate-180' : ''}`}>
                <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>

            <AnimatePresence>
              {showSettings && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  className="absolute bottom-[calc(100%+12px)] left-0 z-30 w-64 rounded-[1.5rem] border border-border bg-card p-2 shadow-2xl flex flex-col gap-1"
                >
                  <div className="px-2 py-1.5 overflow-hidden">
                    <p className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">model</p>
                    <div className="max-h-40 overflow-y-auto scroll-thin space-y-0.5">
                      {models.length === 0 ? (
                        <p className="text-xs text-muted-foreground p-2">no models available</p>
                      ) : (
                        models.map((m) => (
                          <button
                            key={m.ref}
                            type="button"
                            onClick={() => { handleModelChange(m.ref); setShowSettings(false); }}
                            className={`w-full text-left flex items-center gap-2 rounded-xl px-2.5 py-2 text-xs font-medium transition-all ${
                              selectedModel === m.ref
                                ? "bg-primary/10 text-primary shadow-sm ring-1 ring-primary/20"
                                : "text-foreground hover:bg-secondary"
                            }`}
                          >
                            <span className={`block h-1.5 w-1.5 rounded-full ${selectedModel === m.ref ? "bg-primary" : "bg-transparent"}`} />
                            <span className="truncate">{m.alias}</span>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                  
                  <div className="mx-2 my-1 border-t border-border/50" />

                  <div className="px-2 py-1.5">
                    <p className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">capabilities</p>
                    <button
                      type="button"
                      aria-pressed={thinkingEnabled}
                      onClick={() => onThinkingToggle?.(!thinkingEnabled)}
                      className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-xs font-medium transition-all ${
                        thinkingEnabled
                          ? "bg-primary text-primary-foreground shadow-pebble"
                          : "text-foreground hover:bg-secondary shadow-sm bg-background border border-border/50"
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" />
                          <path d="M6 6.5a2 2 0 1 1 2.5 1.94V10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                          <circle cx="8.5" cy="11.5" r="0.6" fill="currentColor" />
                        </svg>
                        thinking mode
                      </span>
                      <div className={`h-3 w-6 rounded-full transition-colors flex items-center px-[2px] ${thinkingEnabled ? 'bg-primary-foreground/20' : 'bg-muted'}`}>
                        <div className={`h-2 w-2 rounded-full bg-current transition-transform ${thinkingEnabled ? 'translate-x-[12px]' : 'translate-x-0'}`} />
                      </div>
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              onClick={onExecutorClick}
              disabled={!onExecutorClick}
              className="flex h-7 items-center gap-2 rounded-full px-3 text-xs font-medium text-muted-foreground transition hover:bg-background hover:text-foreground hover:shadow-sm border border-transparent hover:border-border disabled:cursor-default disabled:opacity-50"
            >
              <span className={`h-2 w-2 rounded-full ${execDot} shadow-sm`} />
              {hasExec ? activeExecutor.id : "no exec"}
            </button>
          </div>
        </div>

        {/* ── Input ── */}
        <div className="flex items-end gap-2 px-4 py-3">
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => {
              if (!e.target.value.startsWith("/")) setSlashDismissed(false);
              setValue(e.target.value);
            }}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? "waiting..." : "message doti... (try /)"}
            disabled={disabled}
            rows={1}
            className="scroll-thin max-h-[200px] min-h-[40px] flex-1 resize-none bg-transparent text-sm leading-relaxed text-foreground outline-none placeholder:text-muted-foreground/50 disabled:cursor-not-allowed disabled:opacity-40 py-2"
          />
          <button
            type="submit"
            disabled={!canSend}
            className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition-all hover:opacity-90 active:scale-95 disabled:bg-muted disabled:text-muted-foreground"
            aria-label="Send"
          >
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
              <path d="M2 8h12M9 3l5 5-5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>

      <p className="mt-2 text-center text-[11px] text-muted-foreground/40">
        enter to send · shift+enter newline · / for commands
      </p>
    </form>
  );
}
