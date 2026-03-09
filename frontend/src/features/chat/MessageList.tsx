import { useEffect, useMemo, useRef, useState } from "react";

import { Markdown } from "@/features/chat/Markdown";
import { useChatStore } from "@/state/chatStore";
import type { ChatItem } from "@/state/chatStore";

type MessageListProps = {
  messages: ChatItem[];
  streamingContent: string;
  isStreaming: boolean;
};

/* ── Thinking bubble ── */
function ThinkingCard({ item }: { item: Extract<ChatItem, { kind: "thinking" }> }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="animate-message-in my-1">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-left transition hover:border-[var(--accent)]/30"
      >
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--accent)]/15 text-[10px] text-[var(--accent)]">
          {item.iteration}
        </span>
        <span className="text-xs text-[var(--text-muted)]">Thinking...</span>
        <svg
          className={`ml-auto h-3 w-3 text-[var(--text-muted)] transition-transform ${expanded ? "rotate-180" : ""}`}
          viewBox="0 0 12 12" fill="none"
        >
          <path d="M3 4.5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
      {expanded && (
        <div className="mt-1 rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] px-3 py-2 text-[13px] leading-relaxed text-[var(--text-secondary)]">
          <Markdown content={item.content} />
        </div>
      )}
    </div>
  );
}

/* ── Tool call group (request + result pair) ── */
function ToolRequestCard({ item }: { item: Extract<ChatItem, { kind: "tool_request" }> }) {
  const [expanded, setExpanded] = useState(false);
  const [approved, setApproved] = useState<boolean | null>(null);
  const requiresApproval = item.risk_level === "high" || item.risk_level === "critical";
  const riskColors: Record<string, string> = {
    low: "text-emerald-400 bg-emerald-500/10",
    medium: "text-blue-400 bg-blue-500/10",
    high: "text-amber-400 bg-amber-500/10",
    critical: "text-rose-400 bg-rose-500/10",
  };
  const riskStyle = riskColors[item.risk_level] || riskColors.high;

  const toolIcons: Record<string, string> = {
    read_file: "📄",
    write_file: "✏️",
    list_directory: "📁",
    shell_exec: "⚡",
  };
  const icon = toolIcons[item.tool_name] || "🔧";

  const onApprove = () => {
    useChatStore.getState().approveToolCall(item.approval_id, true);
    setApproved(true);
  };

  const onDeny = () => {
    useChatStore.getState().approveToolCall(item.approval_id, false);
    setApproved(false);
  };

  return (
    <div className="animate-message-in my-0.5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2.5 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-left transition hover:border-[var(--accent)]/30"
      >
        <span className="text-sm">{icon}</span>
        <span className="font-mono text-xs text-[var(--text-primary)]">{item.tool_name}</span>
        <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${riskStyle}`}>
          {item.risk_level}
        </span>
        <span className="ml-auto text-[10px] text-[var(--text-muted)]">
          {_summarizeArgs(item.arguments)}
        </span>
        <svg
          className={`h-3 w-3 shrink-0 text-[var(--text-muted)] transition-transform ${expanded ? "rotate-180" : ""}`}
          viewBox="0 0 12 12" fill="none"
        >
          <path d="M3 4.5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
      {expanded && (
        <div className="mt-0.5 rounded-lg border border-[var(--border)] bg-[#080e1e] px-3 py-2">
          <pre className="overflow-x-auto text-[12px] leading-5 text-[var(--text-secondary)]">
            {JSON.stringify(item.arguments, null, 2)}
          </pre>
        </div>
      )}
      {requiresApproval && approved === null && (
        <div className="mt-1 flex items-center gap-2">
          <button
            type="button"
            onClick={onApprove}
            className="rounded-md border border-[var(--border)] bg-[var(--bg-secondary)] px-2.5 py-1 text-xs font-medium text-emerald-300 transition hover:border-emerald-400/60 hover:bg-emerald-500/15"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={onDeny}
            className="rounded-md border border-[var(--border)] bg-[var(--bg-secondary)] px-2.5 py-1 text-xs font-medium text-rose-300 transition hover:border-rose-400/60 hover:bg-rose-500/15"
          >
            Deny
          </button>
        </div>
      )}
      {requiresApproval && approved === true && (
        <div className="mt-1">
          <span className="inline-flex rounded-full border border-[var(--border)] bg-[var(--bg-secondary)] px-2 py-0.5 text-[10px] font-medium text-emerald-300">
            Approved
          </span>
        </div>
      )}
      {requiresApproval && approved === false && (
        <div className="mt-1">
          <span className="inline-flex rounded-full border border-[var(--border)] bg-[var(--bg-secondary)] px-2 py-0.5 text-[10px] font-medium text-rose-300">
            Denied
          </span>
        </div>
      )}
    </div>
  );
}

function ToolResultCard({ item }: { item: Extract<ChatItem, { kind: "tool_result" }> }) {
  const [expanded, setExpanded] = useState(false);
  const isError = item.is_error;
  const statusColor = isError ? "text-rose-400" : "text-emerald-400";
  const statusIcon = isError ? "✗" : "✓";

  // Truncate long results for the summary line
  const preview = item.result.length > 80
    ? item.result.slice(0, 80).replace(/\n/g, " ") + "…"
    : item.result.replace(/\n/g, " ");

  return (
    <div className="animate-message-in my-0.5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2.5 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-left transition hover:border-[var(--accent)]/30"
      >
        <span className={`text-xs font-bold ${statusColor}`}>{statusIcon}</span>
        <span className="font-mono text-xs text-[var(--text-muted)]">{item.tool_name}</span>
        <span className="min-w-0 flex-1 truncate text-[11px] text-[var(--text-muted)]">
          {preview}
        </span>
        <svg
          className={`h-3 w-3 shrink-0 text-[var(--text-muted)] transition-transform ${expanded ? "rotate-180" : ""}`}
          viewBox="0 0 12 12" fill="none"
        >
          <path d="M3 4.5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
      {expanded && (
        <div className="mt-0.5 rounded-lg border border-[var(--border)] bg-[#080e1e] px-3 py-2">
          <pre className="chat-scroll max-h-[300px] overflow-auto text-[12px] leading-5 text-[var(--text-secondary)]">
            {item.result}
          </pre>
        </div>
      )}
    </div>
  );
}

function _summarizeArgs(args: Record<string, unknown>): string {
  const path = args.path ?? args.command;
  if (typeof path === "string") {
    return path.length > 40 ? path.slice(0, 40) + "…" : path;
  }
  const keys = Object.keys(args);
  if (keys.length === 0) return "";
  return keys.join(", ");
}

/* ── Main list ── */
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

  const showThinking = isStreaming && !streamingContent && !messages.some(
    (m) => m.kind === "tool_request" || m.kind === "tool_result" || m.kind === "thinking",
  );
  const showEmpty = messages.length === 0 && !showThinking && !isStreaming;

  return (
    <div className="chat-scroll h-full overflow-y-auto px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-[720px] flex-col gap-3">
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
          if (item.kind === "thinking") {
            return <ThinkingCard key={item.id} item={item} />;
          }

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

        {/* Show a working indicator when agent is processing tools */}
        {isStreaming && !streamingContent && messages.length > 0 && (
          <div className="animate-message-in flex items-center gap-2 py-1">
            <div className="flex gap-1">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--accent)]/60" style={{ animationDelay: "0ms" }} />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--accent)]/60" style={{ animationDelay: "150ms" }} />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--accent)]/60" style={{ animationDelay: "300ms" }} />
            </div>
            <span className="text-xs text-[var(--text-muted)]">Working...</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
