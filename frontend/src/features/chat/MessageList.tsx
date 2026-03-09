import { useEffect, useMemo, useRef } from "react";

import { Markdown } from "@/features/chat/Markdown";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type MessageListProps = {
  messages: ChatMessage[];
  streamingContent: string;
  isStreaming: boolean;
};

export function MessageList({ messages, streamingContent, isStreaming }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const items = useMemo(() => {
    if (!isStreaming || !streamingContent) return messages;
    return [
      ...messages,
      { id: "streaming", role: "assistant" as const, content: streamingContent },
    ];
  }, [isStreaming, messages, streamingContent]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [items]);

  const showThinking = isStreaming && !streamingContent;
  const showEmpty = messages.length === 0 && !showThinking;

  return (
    <div className="chat-scroll h-full overflow-y-auto px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-[720px] flex-col gap-5">
        {showEmpty && (
          <div className="flex min-h-[50vh] items-center justify-center">
            <div className="text-center">
              <p className="text-2xl font-medium tracking-tight text-[var(--text-primary)]">
                What can I help you with?
              </p>
              <p className="mt-2 text-sm text-[var(--text-muted)]">
                Send a message to start.
              </p>
            </div>
          </div>
        )}

        {items.map((msg, i) => {
          const isUser = msg.role === "user";
          const isStreamingRow = isStreaming && i === items.length - 1 && !!streamingContent;

          if (isUser) {
            return (
              <div key={msg.id} className="animate-message-in flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md bg-[var(--accent)] px-4 py-2.5 text-[15px] leading-relaxed text-white shadow-md">
                  {msg.content}
                </div>
              </div>
            );
          }

          return (
            <div key={msg.id} className="animate-message-in">
              <div className="mb-1.5 flex items-center gap-1.5">
                <span className="text-xs text-[var(--accent)]">✦</span>
                <span className="text-[11px] font-medium uppercase tracking-widest text-[var(--text-muted)]">
                  DOTI
                </span>
              </div>
              <div className="text-[15px] leading-[1.75] text-[var(--text-primary)]">
                <Markdown content={msg.content} />
                {isStreamingRow && (
                  <span className="animate-cursor-pulse text-[var(--accent)]">▍</span>
                )}
              </div>
            </div>
          );
        })}

        {showThinking && (
          <div className="animate-message-in">
            <div className="mb-1.5 flex items-center gap-1.5">
              <span className="text-xs text-[var(--accent)]">✦</span>
              <span className="text-[11px] font-medium uppercase tracking-widest text-[var(--text-muted)]">
                DOTI
              </span>
            </div>
            <p className="animate-thinking text-[15px] text-[var(--text-muted)]">
              Thinking...
            </p>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
