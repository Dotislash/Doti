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

  return (
    <div className="h-full overflow-y-auto px-4 py-4 sm:px-6">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-3">
        {items.map((message, index) => {
          const isStreamingRow = isStreaming && index === items.length - 1 && !!streamingContent;
          return (
            <article
              key={message.id}
              className="rounded-md border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-3"
            >
              <p className="mb-1 text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                {message.role === "user" ? "User" : "Assistant"}
              </p>
              <p className="whitespace-pre-wrap text-sm leading-6 text-[var(--text-primary)]">
                {message.content}
                {isStreamingRow ? <span className="ml-1 animate-pulse text-[var(--accent)]">▍</span> : null}
              </p>
            </article>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
