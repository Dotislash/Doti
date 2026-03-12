import { useEffect, useMemo, useRef, useState } from "react";

import { Markdown } from "@/features/chat/Markdown";
import { useChatStore } from "@/state/chatStore";
import type { ChatItem } from "@/state/chatStore";
import { useUiStore } from "@/state/uiStore";

type MessageListProps = {
  messages: ChatItem[];
  streamingContent: string;
  isStreaming: boolean;
};

/* ────────────────────────────────────────────
   Thinking Card
   ──────────────────────────────────────────── */
function ThinkingCard({ item }: { item: Extract<ChatItem, { kind: "thinking" }> }) {
  const [open, setOpen] = useState(false);
  const isCompact = useUiStore((s) => s.chatSpacing) === "compact";
  
  return (
    <div className="anim-fade-up">
      <button
        onClick={() => setOpen(!open)}
        className={`flex w-full items-center gap-3 rounded-2xl border border-border bg-card text-left transition-all hover:border-primary/30 hover:shadow-sm ${isCompact ? "px-3 py-2" : "px-4 py-3"}`}
      >
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
          {item.iteration}
        </span>
        <span className="text-sm font-medium text-muted-foreground">thinking</span>
        <Chevron open={open} />
      </button>
      {open && (
        <div className="mt-2 rounded-2xl border border-border bg-background p-5 text-sm leading-relaxed text-foreground shadow-inner-pebble">
          <Markdown content={item.content} />
        </div>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────
   Tool Request Card
   ──────────────────────────────────────────── */
function ToolRequestCard({ item }: { item: Extract<ChatItem, { kind: "tool_request" }> }) {
  const [open, setOpen] = useState(false);
  const [approved, setApproved] = useState<boolean | null>(null);
  const isCompact = useUiStore((s) => s.chatSpacing) === "compact";
  const needsApproval = item.risk_level === "high" || item.risk_level === "critical";

  const riskBadge: Record<string, string> = {
    low:      "text-green-600 bg-green-500/10",
    medium:   "text-blue-600 bg-blue-500/10",
    high:     "text-amber-600 bg-amber-500/10",
    critical: "text-destructive bg-destructive/10",
  };

  return (
    <div className="anim-fade-up">
      <button
        onClick={() => setOpen(!open)}
        className={`flex w-full items-center gap-3 rounded-2xl border border-border bg-card text-left transition-all hover:border-primary/30 hover:shadow-sm ${isCompact ? "px-3 py-2" : "px-4 py-3"}`}
      >
        <span className="text-sm font-semibold text-foreground tracking-tight">{item.tool_name}</span>
        <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${riskBadge[item.risk_level] ?? riskBadge.high}`}>
          {item.risk_level}
        </span>
        <span className="ml-auto max-w-[30%] truncate text-[13px] font-mono text-muted-foreground">
          {summarizeArgs(item.arguments)}
        </span>
        <Chevron open={open} />
      </button>

      {open && (
        <div className="mt-2 rounded-2xl border border-border bg-popover p-4 shadow-inner-pebble">
          <pre className="scroll-thin overflow-x-auto text-[13px] font-mono leading-relaxed text-foreground">
            {JSON.stringify(item.arguments, null, 2)}
          </pre>
        </div>
      )}

      {needsApproval && approved === null && (
        <div className="mt-2 flex gap-2">
          <button
            onClick={() => { useChatStore.getState().approveToolCall(item.approval_id, true); setApproved(true); }}
            className="rounded-md bg-[var(--green-dim)] px-3 py-1.5 font-mono text-xs font-medium text-[var(--green)] ring-1 ring-[var(--green)]/20 transition hover:bg-[var(--green)]/20"
          >
            approve
          </button>
          <button
            onClick={() => { useChatStore.getState().approveToolCall(item.approval_id, false); setApproved(false); }}
            className="rounded-md bg-[var(--red-dim)] px-3 py-1.5 font-mono text-xs font-medium text-[var(--red)] ring-1 ring-[var(--red)]/20 transition hover:bg-[var(--red)]/20"
          >
            deny
          </button>
        </div>
      )}

      {needsApproval && approved !== null && (
        <div className="mt-2">
          <span className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 font-mono text-[11px] font-medium ${
            approved
              ? "bg-[var(--green-dim)] text-[var(--green)]"
              : "bg-[var(--red-dim)] text-[var(--red)]"
          }`}>
            <span className={`h-1.5 w-1.5 rounded-full ${approved ? "bg-[var(--green)]" : "bg-[var(--red)]"}`} />
            {approved ? "approved" : "denied"}
          </span>
        </div>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────
   Tool Result Card
   ──────────────────────────────────────────── */
function ToolResultCard({ item }: { item: Extract<ChatItem, { kind: "tool_result" }> }) {
  const [open, setOpen] = useState(false);
  const isCompact = useUiStore((s) => s.chatSpacing) === "compact";
  const preview = item.result.length > 80
    ? item.result.slice(0, 80).replace(/\n/g, " ") + "…"
    : item.result.replace(/\n/g, " ");

  return (
    <div className="anim-fade-up">
      <button
        onClick={() => setOpen(!open)}
        className={`flex w-full items-center gap-3 rounded-2xl border border-border bg-card text-left transition-all hover:border-primary/30 hover:shadow-sm ${isCompact ? "px-3 py-2" : "px-4 py-3"}`}
      >
        <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
          item.is_error ? "bg-destructive/10 text-destructive" : "bg-green-500/10 text-green-600"
        }`}>
          {item.is_error ? "!" : "✓"}
        </span>
        <span className="text-sm font-semibold text-muted-foreground">{item.tool_name}</span>
        <span className="min-w-0 flex-1 truncate text-[13px] font-mono text-muted-foreground ml-2">{preview}</span>
        <Chevron open={open} />
      </button>
      {open && (
        <div className="mt-2 rounded-2xl border border-border bg-popover p-4 shadow-inner-pebble">
          <pre className="scroll-thin max-h-[300px] overflow-auto text-[13px] font-mono leading-relaxed text-foreground">
            {item.result}
          </pre>
        </div>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────
   Shared components
   ──────────────────────────────────────────── */
function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`ml-auto h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 ${open ? "rotate-180" : ""}`}
      viewBox="0 0 12 12" fill="none"
    >
      <path d="M3 4.5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function summarizeArgs(args: Record<string, unknown>): string {
  const path = args.path ?? args.command;
  if (typeof path === "string") return path.length > 40 ? path.slice(0, 40) + "…" : path;
  const keys = Object.keys(args);
  return keys.length === 0 ? "" : keys.join(", ");
}

/* ────────────────────────────────────────────
   Message List (main export)
   ──────────────────────────────────────────── */
export function MessageList({ messages, streamingContent, isStreaming }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const isCompact = useUiStore((s) => s.chatSpacing) === "compact";

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

  const showWorking = isStreaming && !streamingContent && !messages.some(
    (m) => m.kind === "tool_request" || m.kind === "tool_result" || m.kind === "thinking",
  );
  const showEmpty = messages.length === 0 && !showWorking && !isStreaming;

  return (
    <div className={`scroll-thin h-full overflow-y-auto ${isCompact ? "px-5 py-4" : "px-6 py-6"}`}>
      <div className={`mx-auto flex w-full max-w-3xl flex-col ${isCompact ? "gap-3" : "gap-5"}`}>

        {/* ── Empty state ── */}
        {showEmpty && (
          <div className="flex min-h-[60vh] items-center justify-center">
            <div className="max-w-md text-center">
              <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
                <span className="text-lg font-bold tracking-tighter text-primary">do:</span>
              </div>
              <h2 className="text-lg font-medium tracking-tight text-foreground">
                what can i help with?
              </h2>
              <p className="mt-1.5 text-sm text-muted-foreground">
                send a message or pick a starter below.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {[
                  "explain this project",
                  "write a function",
                  "debug an issue",
                ].map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => useChatStore.getState().sendMessage(prompt)}
                    className="rounded-xl border border-border/40 px-4 py-2 text-sm text-muted-foreground transition-all hover:border-primary/30 hover:text-primary active:scale-[0.98]"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── Messages ── */}
        {items.map((item, i) => {
          if (item.kind === "thinking") return <ThinkingCard key={item.id} item={item} />;
          if (item.kind === "tool_request") return <ToolRequestCard key={item.id} item={item} />;
          if (item.kind === "tool_result") return <ToolResultCard key={item.id} item={item} />;

          const isUser = item.role === "user";
          const isStreamingRow = isStreaming && i === items.length - 1 && !!streamingContent;

          if (isUser) {
            return (
              <div key={item.id} className="anim-fade-up flex justify-end">
                <div className={`max-w-[80%] rounded-2xl rounded-br-sm bg-primary text-primary-foreground leading-relaxed ${isCompact ? "px-4 py-2 text-[13.5px]" : "px-5 py-3 text-sm"}`}>
                  {item.content}
                </div>
              </div>
            );
          }

          return (
            <div key={item.id} className="anim-fade-up flex gap-3 max-w-[90%]">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-[10px] font-bold text-primary mt-0.5">
                d:
              </div>
              <div className={`flex-1 rounded-2xl rounded-tl-sm leading-relaxed text-foreground ${isCompact ? "py-2 text-[13.5px]" : "py-3 text-sm"}`}>
                <Markdown content={item.content} />
                {isStreamingRow && (
                  <span className="anim-cursor inline-block w-2 h-4 bg-primary align-middle ml-1 rounded-sm shadow-sm" />
                )}
              </div>
            </div>
          );
        })}

        {/* ── Working indicator ── */}
        {isStreaming && !streamingContent && messages.length > 0 && (
          <div className="anim-fade-up flex items-center gap-4 rounded-[2rem] border border-border bg-card px-5 py-3 w-fit shadow-sm">
            <span className="relative flex h-2.5 w-2.5">
              <span className="anim-pulse-ring absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
            </span>
            <span className="text-sm font-medium text-muted-foreground">processing...</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
