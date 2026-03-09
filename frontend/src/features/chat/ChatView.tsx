import { useEffect, useMemo, useState } from "react";

import { Composer } from "@/features/chat/Composer";
import { MessageList } from "@/features/chat/MessageList";
import { useChatStore } from "@/state/chatStore";

export function ChatView() {
  const messages = useChatStore((state) => state.messages);
  const streamingContent = useChatStore((state) => state.streamingContent);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const runState = useChatStore((state) => state.runState);
  const error = useChatStore((state) => state.error);
  const sendMessage = useChatStore((state) => state.sendMessage);

  const [dismissedError, setDismissedError] = useState<string | null>(null);

  useEffect(() => {
    if (error && error !== dismissedError) {
      setDismissedError(null);
    }
  }, [dismissedError, error]);

  const visibleError = error && error !== dismissedError ? error : null;

  const status = useMemo(() => {
    if (error) {
      return { label: "Disconnected", tone: "bg-rose-400" };
    }

    if (runState === "queued" || runState === "running") {
      return { label: `Busy - ${runState}`, tone: "bg-amber-300" };
    }

    return { label: "Connected", tone: "bg-emerald-400" };
  }, [error, runState]);

  return (
    <div className="relative flex h-screen min-h-screen flex-col text-[var(--text-primary)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_8%,rgba(95,145,255,0.13),transparent_45%),radial-gradient(circle_at_80%_2%,rgba(75,191,176,0.09),transparent_38%)]" />

      <header className="relative z-10 px-4 pt-4 sm:px-7 sm:pt-6">
        <div className="mx-auto flex h-14 w-full max-w-[720px] items-center justify-between border-b border-transparent bg-[linear-gradient(90deg,rgba(131,160,236,0.4),rgba(131,160,236,0)_35%,rgba(131,160,236,0)_65%,rgba(131,160,236,0.26))] bg-[length:100%_1px] bg-no-repeat bg-bottom pb-3">
          <h1 className="text-sm font-semibold tracking-[0.26em] text-[var(--text-primary)]">
            DOTI<span className="ml-1 text-[var(--accent)]">.</span>
          </h1>
          <p className="inline-flex items-center gap-2 text-xs text-[var(--text-secondary)]">
            <span className={`h-2.5 w-2.5 rounded-full ${status.tone}`} />
            {status.label}
          </p>
        </div>
      </header>

      {visibleError ? (
        <div className="relative z-10 px-4 pb-1 pt-2 sm:px-7">
          <div className="mx-auto flex w-full max-w-[720px] items-center justify-between gap-3 rounded-xl border border-[rgba(255,120,120,0.32)] bg-[rgba(120,20,30,0.28)] px-3.5 py-2.5 text-sm text-rose-100">
            <span className="truncate">{visibleError}</span>
            <button
              type="button"
              onClick={() => setDismissedError(visibleError)}
              className="rounded-md px-2 py-1 text-xs font-medium text-rose-100/90 transition hover:bg-[rgba(255,255,255,0.1)]"
            >
              Dismiss
            </button>
          </div>
        </div>
      ) : null}

      <main className="relative z-10 min-h-0 flex-1">
        <MessageList
          messages={messages}
          streamingContent={streamingContent}
          isStreaming={isStreaming}
        />
      </main>

      <Composer onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
