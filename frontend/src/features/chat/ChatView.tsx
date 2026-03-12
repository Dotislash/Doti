import { useMemo, useState } from "react";

import { Composer } from "@/features/chat/Composer";
import { MessageList } from "@/features/chat/MessageList";
import { useChatStore } from "@/state/chatStore";
import { useUiStore } from "@/state/uiStore";

export function ChatView() {
  const messages = useChatStore((s) => s.messages);
  const streamingContent = useChatStore((s) => s.streamingContent);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const error = useChatStore((s) => s.error);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const activeConversation = useChatStore((s) => s.activeConversation);
  const threads = useChatStore((s) => s.threads);
  const activeExecutor = useChatStore((s) => s.activeExecutor);
  const thinkingEnabled = useChatStore((s) => s.thinkingEnabled);
  const handleSlashCommand = useChatStore((s) => s.handleSlashCommand);
  const setModel = useChatStore((s) => s.setModel);
  const setThinkingEnabled = useChatStore((s) => s.setThinkingEnabled);

  const isSidebarOpen = useUiStore((s) => s.isSidebarOpen);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);

  const [dismissedError, setDismissedError] = useState<string | null>(null);
  const visibleError = error && error !== dismissedError ? error : null;

  const headerTitle = useMemo(() => {
    if (activeConversation === "main") return null;
    const thread = threads.find((t) => t.thread_id === activeConversation);
    return thread?.title || "thread";
  }, [activeConversation, threads]);

  return (
    <div className="flex h-full flex-col bg-card w-full rounded-[inherit] overflow-hidden">
      {/* ── Header ── */}
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-border/30 px-5 z-10">
        <div className="flex items-center gap-3 text-sm font-medium">
          <button
            onClick={toggleSidebar}
            className={`flex h-8 w-8 items-center justify-center rounded-xl transition-all ${
              !isSidebarOpen
                ? "bg-primary/10 text-primary hover:bg-primary/20 shadow-sm"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            }`}
            title="Toggle Sidebar"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="9" y1="3" x2="9" y2="21"></line>
            </svg>
          </button>
          
          <div className="w-px h-4 bg-border/50 mx-1"></div>
          {headerTitle ? (
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary group-hover:bg-primary/20 transition-colors">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
              </span>
              <span className="text-foreground tracking-tight">{headerTitle}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-secondary text-secondary-foreground transition-colors">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
              </span>
              <span className="text-foreground tracking-tight">main</span>
            </div>
          )}
        </div>
      </header>

      {/* ── Error ── */}
      {visibleError && (
        <div className="bg-destructive/5 px-6 py-3 border-b border-destructive/10">
          <div className="mx-auto flex max-w-3xl items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-destructive">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
              <span className="font-medium">{visibleError}</span>
            </div>
            <button
              onClick={() => setDismissedError(visibleError)}
              className="rounded-full hover:bg-destructive/10 p-1 text-destructive/70 transition hover:text-destructive"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>
        </div>
      )}

      {/* ── Messages ── */}
      <main className="min-h-0 flex-1">
        <MessageList
          messages={messages}
          streamingContent={streamingContent}
          isStreaming={isStreaming}
        />
      </main>

      {/* ── Composer ── */}
      <Composer
        onSend={sendMessage}
        onSlashCommand={handleSlashCommand}
        onModelChange={setModel}
        onThinkingToggle={setThinkingEnabled}
        onExecutorClick={() => handleSlashCommand("/executor", "")}
        activeExecutor={activeExecutor}
        thinkingEnabled={thinkingEnabled}
        disabled={isStreaming}
      />
    </div>
  );
}
