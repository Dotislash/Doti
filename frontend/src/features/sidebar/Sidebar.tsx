import { useEffect, useMemo, useState } from "react";

import { useChatStore } from "@/state/chatStore";
import { SettingsPanel } from "@/features/settings/SettingsPanel";

export function Sidebar() {
  const threads = useChatStore((s) => s.threads);
  const activeConversation = useChatStore((s) => s.activeConversation);
  const switchConversation = useChatStore((s) => s.switchConversation);
  const createThread = useChatStore((s) => s.createThread);
  const deleteThread = useChatStore((s) => s.deleteThread);
  const runState = useChatStore((s) => s.runState);
  const error = useChatStore((s) => s.error);
  const isStreaming = useChatStore((s) => s.isStreaming);

  const statusDot = useMemo(() => {
    if (error) return "bg-rose-400";
    if (isStreaming || runState === "queued" || runState === "running") return "bg-amber-300 animate-pulse";
    return "bg-emerald-400";
  }, [error, isStreaming, runState]);

  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [showSettings, setShowSettings] = useState(false);

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
    <aside className="flex h-full w-64 flex-col border-r border-[var(--border)] bg-[var(--bg-secondary)]">
      {/* Main button */}
      <div className="p-3">
        <button
          onClick={() => switchConversation("main")}
          className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
            activeConversation === "main"
              ? "bg-[var(--accent)]/15 text-[var(--accent)]"
              : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
          }`}
        >
          <span className={`h-2 w-2 shrink-0 rounded-full ${activeConversation === "main" ? statusDot : "bg-[var(--text-muted)]/30"}`} />
          Main
        </button>
      </div>

      {/* New Thread */}
      <div className="px-3 pb-2">
        {showCreate ? (
          <div className="flex flex-col gap-1.5">
            <input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              placeholder="Thread title..."
              autoFocus
              className="rounded-md border border-[var(--border)] bg-[var(--bg-primary)] px-2 py-1.5 text-xs text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]/50"
            />
            <div className="flex gap-1">
              <button
                onClick={handleCreate}
                className="flex-1 rounded-md bg-[var(--accent)] px-2 py-1 text-xs text-white hover:bg-[var(--accent-hover)]"
              >
                Create
              </button>
              <button
                onClick={() => { setShowCreate(false); setNewTitle(""); }}
                className="flex-1 rounded-md border border-[var(--border)] px-2 py-1 text-xs text-[var(--text-muted)] hover:bg-[var(--bg-tertiary)]"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowCreate(true)}
            className="flex w-full items-center gap-1.5 rounded-lg px-3 py-2 text-xs text-[var(--text-muted)] transition hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-secondary)]"
          >
            <span className="text-sm">+</span>
            New Thread
          </button>
        )}
      </div>

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto px-3">
        {activeThreads.length > 0 && (
          <div className="mb-3">
            <p className="mb-1 px-2 text-[10px] font-medium uppercase tracking-widest text-[var(--text-muted)]">
              Active
            </p>
            {activeThreads.map((t) => (
              <div
                key={t.thread_id}
                className={`group flex items-center justify-between rounded-lg px-3 py-1.5 text-sm transition ${
                  activeConversation === t.thread_id
                    ? "bg-[var(--accent)]/15 text-[var(--accent)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
                }`}
              >
                <button
                  onClick={() => switchConversation(t.thread_id)}
                  className="flex flex-1 items-center gap-2 truncate text-left"
                >
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${activeConversation === t.thread_id ? statusDot : "bg-[var(--text-muted)]/30"}`} />
                  {t.title || "Untitled"}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteThread(t.thread_id); }}
                  className="ml-1 hidden text-xs text-[var(--text-muted)] hover:text-rose-400 group-hover:block"
                  title="Delete"
                >
                  &#x2715;
                </button>
              </div>
            ))}
          </div>
        )}

        {archivedThreads.length > 0 && (
          <div>
            <p className="mb-1 px-2 text-[10px] font-medium uppercase tracking-widest text-[var(--text-muted)]">
              Archived
            </p>
            {archivedThreads.map((t) => (
              <button
                key={t.thread_id}
                onClick={() => switchConversation(t.thread_id)}
                className={`flex w-full items-center rounded-lg px-3 py-1.5 text-sm transition ${
                  activeConversation === t.thread_id
                    ? "bg-[var(--accent)]/15 text-[var(--accent)]"
                    : "text-[var(--text-muted)] hover:bg-[var(--bg-tertiary)]"
                }`}
              >
                <span className="truncate">{t.title || "Untitled"}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Version info */}
      <div className="border-t border-[var(--border)] p-3">
        <div className="flex items-center justify-between">
          <p className="text-[10px] text-[var(--text-muted)]">DOTI v0.1</p>
          <button
            type="button"
            onClick={() => setShowSettings(true)}
            className="rounded-md p-1 text-[var(--text-muted)] transition hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-secondary)]"
            aria-label="Open settings"
            title="Settings"
          >
            ⚙
          </button>
        </div>
      </div>

      <SettingsPanel isOpen={showSettings} onClose={() => setShowSettings(false)} />
    </aside>
  );
}
