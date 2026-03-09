import { useEffect, useMemo, useRef } from "react";

import { Markdown } from "@/features/chat/Markdown";
import type { ChatItem } from "@/state/chatStore";

type MessageListProps = {
  messages: ChatItem[];
  streamingContent: string;
  isStreaming: boolean;
};

function ToolRequestCard({ item }: { item: Extract<ChatItem, { kind: "tool_request" }> }) {
  return (
    <div className="animate-message-in my-1">
      <div className="rounded-lg border border-amber-500/20 bg-amber-950/20 px-3 py-2">
        <div className="flex items-center gap-2 text-xs">
          <span className="rounded bg-amber-500/20 px-1.5 py-0.5 font-mono text-amber-300">
            {item.tool_name}
          </span>
          <span className="text-amber-400/60">{item.risk_level}</span>
        </div>
        <pre className="mt-1.5 overflow-x-auto text-[12px] leading-5 text-[var(--text-muted)]">
          {JSON.stringify(item.arguments, null, 2)}
        </pre>
      </div>
    </div>
  );
}

function ToolResultCard({ item }: { item: Extract<ChatItem, { kind: "tool_result" }> }) {
  const borderColor = item.is_error ? "border-rose-500/20" : "border-emerald-500/20";
  const bgColor = item.is_error ? "bg-rose-950/20" : "bg-emerald-950/20";
  const labelColor = item.is_error ? "text-rose-300" : "text-emerald-300";
  const labelBg = item.is_error ? "bg-rose-500/20" : "bg-emerald-500/20";

  return (
    <div className="animate-message-in my-1">
      <div className={`rounded-lg border ${borderColor} ${bgColor} px-3 py-2`}>
        <div className="flex items-center gap-2 text-xs">
          <span className={`rounded ${labelBg} px-1.5 py-0.5 font-mono ${labelColor}`}>
            {item.tool_name}
          </span>
          <span className={labelColor}>{item.is_error ? "error" : "result"}</span>
        </div>
        <pre className="chat-scroll mt-1.5 max-h-[200px] overflow-auto text-[12px] leading-5 text-[var(--text-secondary)]">
          {item.result}
        </pre>
      </div>
    </div>
  );
}

export function MessageList({ messages, streamingContent, isStreaming }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const items = useMemo(() => {
    if (!isStreaming || !streamingContent) return messages;
    return [
      ...messages,
      { kind: "message" as const, id: "streaming", role: "assistant" as const, content: streamingContent },
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

        {items.map((item, i) => {
          if (item.kind === "tool_request") {
            return <ToolRequestCard key={item.id} item={item} />;
          }

          if (item.kind === "tool_result") {
            return <ToolResultCard key={item.id} item={item} />;
          }

          // kind === "message"
          const isUser = item.role === "user";
          const isStreamingRow = isStreaming && i === items.length - 1 && !!streamingContent;

          if (isUser) {
            return (
              <div key={item.id} className="animate-message-in flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md bg-[var(--accent)] px-4 py-2.5 text-[15px] leading-relaxed text-white shadow-md">
                  {item.content}
                </div>
              </div>
            );
          }

          return (
            <div key={item.id} className="animate-message-in">
              <div className="mb-1.5 flex items-center gap-1.5">
                <span className="text-xs text-[var(--accent)]">✦</span>
                <span className="text-[11px] font-medium uppercase tracking-widest text-[var(--text-muted)]">
                  DOTI
                </span>
              </div>
              <div className="text-[15px] leading-[1.75] text-[var(--text-primary)]">
                <Markdown content={item.content} />
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
