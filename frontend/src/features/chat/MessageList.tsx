import { useEffect, useMemo, useRef } from "react";

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
    if (!isStreaming || !streamingContent) {
      return messages;
    }

    return [
      ...messages,
      {
        id: "streaming-preview",
        role: "assistant" as const,
        content: streamingContent,
      },
    ];
  }, [isStreaming, messages, streamingContent]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [items]);

  const showThinking = isStreaming && !streamingContent;
  const showEmpty = messages.length === 0 && !showThinking;

  return (
    <div className="chat-scroll h-full overflow-y-auto px-4 pb-6 pt-5 sm:px-7 sm:pt-7">
      <div className="mx-auto flex w-full max-w-[720px] flex-col gap-4">
        {showEmpty ? (
          <div className="flex min-h-[50vh] items-center justify-center px-4">
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--glass)] px-8 py-7 text-center shadow-[0_18px_60px_rgba(7,12,24,0.42)] backdrop-blur-xl">
              <p className="text-xl font-medium tracking-tight text-[var(--text-primary)] sm:text-2xl">
                What can I help you with?
              </p>
              <p className="mt-2 text-sm text-[var(--text-muted)]">Ask anything to start the conversation.</p>
            </div>
          </div>
        ) : null}

        {items.map((message, index) => {
          const isStreamingRow = isStreaming && index === items.length - 1 && !!streamingContent;
          const isUser = message.role === "user";

          return (
            <article key={message.id} className={`animate-message-in flex ${isUser ? "justify-end" : "justify-start"}`}>
              <div
                className={[
                  "w-full rounded-2xl border px-4 py-3.5 shadow-[0_8px_34px_rgba(5,8,20,0.32)] backdrop-blur-lg sm:px-5",
                  isUser
                    ? "max-w-[88%] border-[rgba(133,169,255,0.26)] bg-[var(--user-bg)]"
                    : "max-w-full border-[var(--border)] bg-[var(--assistant-bg)]",
                ].join(" ")}
              >
                <p className="mb-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--text-secondary)]">
                  {isUser ? "👤 User" : "✦ Assistant"}
                </p>
                <p
                  className={[
                    "whitespace-pre-wrap text-[15px] leading-[1.7] text-[var(--text-primary)]",
                    !isUser ? "sm:text-base" : "",
                  ].join(" ")}
                >
                  {message.content}
                  {isStreamingRow ? <span className="ml-1 animate-cursor-pulse text-[var(--accent)]">▍</span> : null}
                </p>
              </div>
            </article>
          );
        })}

        {showThinking ? (
          <article className="animate-message-in flex justify-start">
            <div className="w-full rounded-2xl border border-[var(--border)] bg-[var(--assistant-bg)] px-4 py-3.5 shadow-[0_8px_34px_rgba(5,8,20,0.32)] backdrop-blur-lg sm:px-5">
              <p className="mb-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--text-secondary)]">
                ✦ Assistant
              </p>
              <p className="animate-thinking text-[15px] leading-[1.7] text-[var(--text-secondary)] sm:text-base">
                Thinking...
              </p>
            </div>
          </article>
        ) : null}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
