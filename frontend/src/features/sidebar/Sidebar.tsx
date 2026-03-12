import { useEffect, useMemo, useState } from "react";

import { useChatStore } from "@/state/chatStore";

type SidebarProps = {
  onOpenSettings?: () => void;
};

export function Sidebar({ onOpenSettings }: SidebarProps) {
  const threads = useChatStore((s) => s.threads);
  const activeConversation = useChatStore((s) => s.activeConversation);
  const switchConversation = useChatStore((s) => s.switchConversation);
  const createThread = useChatStore((s) => s.createThread);
  const deleteThread = useChatStore((s) => s.deleteThread);
  const runState = useChatStore((s) => s.runState);
  const error = useChatStore((s) => s.error);
  const isStreaming = useChatStore((s) => s.isStreaming);

  const statusColor = useMemo(() => {
    if (error) return "bg-destructive";
    if (isStreaming || runState === "queued" || runState === "running") return "bg-primary anim-pulse-ring";
    return "bg-green-500";
  }, [error, isStreaming, runState]);

  const statusDot = useMemo(() => {
    if (error) return "bg-destructive";
    if (isStreaming || runState === "queued" || runState === "running") return "bg-primary";
    return "bg-green-500";
  }, [error, isStreaming, runState]);

  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("doti-theme");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  }, []);

  const handleCreate = () => {
    createThread(newTitle || undefined, "task");
    setNewTitle("");
    setShowCreate(false);
  };

  const activeThreads = threads.filter((t) => t.status === "active" || t.status === "paused");
  const archivedThreads = threads.filter((t) => t.status === "archived");

  return (
    <aside className="flex h-full w-64 flex-col bg-background">
      {/* ── Logo ── */}
      <div className="flex items-center gap-3 px-6 py-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 shadow-sm border border-primary/20">
          <span className="text-sm font-bold text-primary">do:</span>
        </div>
        <div>
          <p className="text-base font-semibold tracking-tight text-foreground">doti</p>
          <p className="text-xs font-medium text-muted-foreground/80">v0.1.0</p>
        </div>
      </div>

      {/* ── Divider ── */}
      <div className="mx-4 border-t border-border/50" />

      {/* ── Main ── */}

      <div className="p-3 pt-4">
        <button
          onClick={() => switchConversation("main")}
          className={`group flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition-all ${
            activeConversation === "main"
              ? "bg-primary/10 text-primary shadow-sm ring-1 ring-primary/20"
              : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
          }`}
        >
          <span className="relative flex h-2 w-2">
            {activeConversation === "main" && (
              <span className={`absolute inline-flex h-full w-full rounded-full opacity-40 ${statusColor}`} />
            )}
            <span className={`relative inline-flex h-2 w-2 rounded-full ${activeConversation === "main" ? statusDot : "bg-muted-foreground/50"}`} />
          </span>
          <span>~ main</span>
        </button>
      </div>

      {/* ── Thread list ── */}
      <div className="scroll-thin flex-1 overflow-y-auto px-3 pt-2">
        {activeThreads.length > 0 && (
          <div className="mb-4">
            <p className="mb-2 px-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground/60 select-none">
              active
            </p>
            {activeThreads.map((t) => (
              <div
                key={t.thread_id}
                className={`group flex items-center rounded-2xl transition-all ${
                  activeConversation === t.thread_id
                    ? "bg-primary/10 shadow-sm ring-1 ring-primary/20"
                    : "hover:bg-secondary/50"
                }`}
              >
                <button
                  onClick={() => switchConversation(t.thread_id)}
                  className={`flex flex-1 items-center gap-3 truncate px-4 py-2.5 text-sm font-medium ${
                    activeConversation === t.thread_id
                      ? "text-primary"
                      : "text-muted-foreground"
                  }`}
                >
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                    activeConversation === t.thread_id ? statusDot : "bg-muted-foreground/50"
                  }`} />
                  <span className="truncate">{t.title || "untitled"}</span>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteThread(t.thread_id); }}
                  className="mr-2 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-muted-foreground opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                  title="Delete"
                >
                  <svg width="12" height="12" viewBox="0 0 10 10" fill="none">
                    <path d="M2 2l6 6M8 2l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        {archivedThreads.length > 0 && (
          <div className="mb-4">
            <p className="mb-2 px-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground/60 select-none">
              archived
            </p>
            {archivedThreads.map((t) => (
              <button
                key={t.thread_id}
                onClick={() => switchConversation(t.thread_id)}
                className={`flex w-full items-center gap-3 truncate rounded-2xl px-4 py-2.5 text-sm font-medium transition-all ${
                  activeConversation === t.thread_id
                    ? "bg-primary/10 text-primary shadow-sm ring-1 ring-primary/20"
                    : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                }`}
              >
                <span className="truncate">{t.title || "untitled"}</span>
              </button>
            ))}
          </div>
        )}

        {/* ── New Thread Action ── */}
        <div className="mt-4 pb-4 px-1">
          {showCreate ? (
            <div className="rounded-xl border border-border/80 bg-card p-3 shadow-pebble">
              <input
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreate();
                  if (e.key === "Escape") { setShowCreate(false); setNewTitle(""); }
                }}
                placeholder="thread name..."
                autoFocus
                className="w-full rounded-lg border border-border bg-background px-2 py-1.5 text-xs text-foreground outline-none placeholder:text-muted-foreground/60 focus:ring-1 focus:ring-primary/30 transition-all"
              />
              <div className="mt-2 flex gap-1.5">
                <button
                  onClick={handleCreate}
                  className="flex-1 rounded-lg bg-primary px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-primary-foreground transition-all hover:bg-primary/90 shadow-sm"
                >
                  Create
                </button>
                <button
                  onClick={() => { setShowCreate(false); setNewTitle(""); }}
                  className="flex-1 rounded-lg border border-border bg-secondary px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-secondary-foreground transition-all hover:bg-secondary/80"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowCreate(true)}
              className="group flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-border/60 bg-transparent px-3 py-2 text-xs font-medium text-muted-foreground transition-all hover:border-primary/40 hover:bg-primary/5 hover:text-primary"
            >
              <span className="text-base leading-none mb-0.5">+</span>
              new thread
            </button>
          )}
        </div>
      </div>

      {/* ── Bottom bar ── */}
      <div className="p-4 pt-2">
        <button
          type="button"
          onClick={() => onOpenSettings?.()}
          className="flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium text-muted-foreground transition-all hover:bg-secondary/50 hover:text-foreground"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0">
            <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          settings
        </button>
      </div>
    </aside>
  );
}
