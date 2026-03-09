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

  const status = error ? "Error" : runState ? `Connected - ${runState}` : "Connected";

  return (
    <div className="flex h-screen min-h-screen flex-col bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <header className="flex h-[52px] items-center justify-between border-b border-[var(--border)] bg-[var(--bg-secondary)] px-4 sm:px-6">
        <h1 className="text-sm font-semibold tracking-[0.2em] text-[var(--text-primary)]">DOTI</h1>
        <p className="text-xs text-[var(--text-secondary)]">{status}</p>
      </header>

      <main className="min-h-0 flex-1">
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
