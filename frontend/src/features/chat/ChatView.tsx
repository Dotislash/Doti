import { useMemo, useState } from "react";

import { Composer } from "@/features/chat/Composer";
import { MessageList } from "@/features/chat/MessageList";
import { useChatStore } from "@/state/chatStore";

export function ChatView() {
  const messages = useChatStore((s) => s.messages);
  const streamingContent = useChatStore((s) => s.streamingContent);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const error = useChatStore((s) => s.error);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const activeConversation = useChatStore((s) => s.activeConversation);
  const threads = useChatStore((s) => s.threads);

  const [dismissedError, setDismissedError] = useState<string | null>(null);
  const visibleError = error && error !== dismissedError ? error : null;

  const headerTitle = useMemo(() => {
    if (activeConversation === "main") return null;
    const thread = threads.find((t) => t.thread_id === activeConversation);
    return thread?.title || "Thread";
  }, [activeConversation, threads]);

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <header className="flex h-12 shrink-0 items-center border-b border-[var(--border)] px-5">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-semibold tracking-[0.2em] text-[var(--text-primary)]">
            DOTI<span className="text-[var(--accent)]">.</span>
          </h1>
          {headerTitle && (
            <span className="text-xs text-[var(--text-muted)]">/ {headerTitle}</span>
          )}
        </div>
      </header>

      {/* Error banner */}
      {visibleError && (
        <div className="border-b border-rose-500/20 bg-rose-950/30 px-5 py-2 text-sm text-rose-200">
          <div className="mx-auto flex max-w-[720px] items-center justify-between">
            <span>{visibleError}</span>
            <button
              onClick={() => setDismissedError(visibleError)}
              className="ml-3 text-xs text-rose-300 hover:text-white"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Messages */}
      <main className="min-h-0 flex-1">
        <MessageList
          messages={messages}
          streamingContent={streamingContent}
          isStreaming={isStreaming}
        />
      </main>

      {/* Composer */}
      <Composer onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
