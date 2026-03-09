import { create } from "zustand";

import { DotiWsClient } from "@/lib/ws/client";
import type { ClientMessage, RunState, ServerMessage, ThreadInfoPayload } from "@/lib/ws/types";

export type ChatItem =
  | { kind: "message"; id: string; role: "user" | "assistant"; content: string }
  | { kind: "tool_request"; id: string; tool_name: string; arguments: Record<string, unknown>; risk_level: string; approval_id: string }
  | { kind: "tool_result"; id: string; tool_name: string; result: string; is_error: boolean };

type ThreadInfo = {
  thread_id: string;
  title: string | null;
  thread_type: string;
  status: string;
  created_at: string;
};

type ChatStore = {
  activeConversation: string;
  messages: ChatItem[];
  streamingContent: string;
  isStreaming: boolean;
  runState: RunState | null;
  error: string | null;
  threads: ThreadInfo[];
  connect: () => void;
  sendMessage: (content: string) => void;
  switchConversation: (id: string) => void;
  createThread: (title?: string, type?: "task" | "focus") => void;
  deleteThread: (threadId: string) => void;
  refreshThreads: () => void;
  handleServerMessage: (msg: ServerMessage) => void;
  client: DotiWsClient | null;
};

const WS_URL = "ws://localhost:5173/ws";

function createId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  activeConversation: "main",
  messages: [],
  streamingContent: "",
  isStreaming: false,
  runState: null,
  error: null,
  threads: [],
  client: null,

  connect: () => {
    let client = get().client;
    if (!client) {
      client = new DotiWsClient(WS_URL);
      client.onMessage(get().handleServerMessage);
      set({ client });
    }
    client.connect();
  },

  sendMessage: (content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    get().connect();
    const client = get().client!;
    const cid = get().activeConversation;

    const userMessage: ChatItem = {
      kind: "message",
      id: createId(),
      role: "user",
      content: trimmed,
    };

    const outbound: ClientMessage = {
      type: "chat.send",
      event_id: createId(),
      ts: Date.now(),
      payload: {
        conversation_id: cid,
        content: trimmed,
        client_msg_id: userMessage.id,
      },
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      isStreaming: true,
      streamingContent: "",
      error: null,
    }));

    client.send(outbound);
  },

  switchConversation: (id: string) => {
    set({
      activeConversation: id,
      messages: [],
      streamingContent: "",
      isStreaming: false,
      error: null,
    });
    const client = get().client;
    if (!client) return;
    if (id !== "main") {
      fetch(`/api/v1/threads/${id}/messages?limit=50`)
        .then((r) => r.json())
        .then((data) => {
          if (get().activeConversation !== id) return;
          const msgs: ChatItem[] = (data.messages || []).map((m: { id: string; role: "user" | "assistant"; content: string }) => ({
            kind: "message" as const,
            id: m.id,
            role: m.role,
            content: m.content,
          }));
          set({ messages: msgs });
        })
        .catch(() => {});
    }
  },

  createThread: (title?: string, type?: "task" | "focus") => {
    get().connect();
    const client = get().client!;
    client.send({
      type: "thread.create",
      event_id: createId(),
      ts: Date.now(),
      payload: { title, thread_type: type || "task" },
    });
  },

  deleteThread: (threadId: string) => {
    get().connect();
    const client = get().client!;
    client.send({
      type: "thread.delete",
      event_id: createId(),
      ts: Date.now(),
      payload: { thread_id: threadId },
    });
    if (get().activeConversation === threadId) {
      get().switchConversation("main");
    }
  },

  refreshThreads: () => {
    get().connect();
    const client = get().client!;
    client.send({
      type: "thread.list",
      event_id: createId(),
      ts: Date.now(),
      payload: {},
    });
  },

  handleServerMessage: (msg: ServerMessage) => {
    switch (msg.type) {
      case "chat.delta": {
        set((state) => ({
          streamingContent: state.streamingContent + msg.payload.delta,
        }));
        return;
      }

      case "chat.final": {
        set((state) => ({
          messages: [
            ...state.messages,
            { kind: "message", id: msg.payload.message_id, role: "assistant", content: msg.payload.content },
          ],
          streamingContent: "",
          isStreaming: false,
          error: null,
        }));
        return;
      }

      case "run.state": {
        set({ runState: msg.payload.state });
        return;
      }

      case "error": {
        set({ error: msg.payload.message, isStreaming: false, streamingContent: "" });
        return;
      }

      case "history.sync": {
        const historyMessages: ChatItem[] = msg.payload.messages.map((m) => ({
          kind: "message" as const,
          id: m.id,
          role: m.role,
          content: m.content,
        }));
        set({ messages: historyMessages });
        return;
      }

      case "tool.request": {
        set((state) => ({
          messages: [
            ...state.messages,
            {
              kind: "tool_request",
              id: msg.payload.approval_id,
              tool_name: msg.payload.tool_name,
              arguments: msg.payload.arguments,
              risk_level: msg.payload.risk_level,
              approval_id: msg.payload.approval_id,
            },
          ],
        }));
        return;
      }

      case "tool.result": {
        set((state) => ({
          messages: [
            ...state.messages,
            {
              kind: "tool_result",
              id: createId(),
              tool_name: msg.payload.tool_name,
              result: msg.payload.result,
              is_error: msg.payload.is_error,
            },
          ],
        }));
        return;
      }

      case "thread.created": {
        set((state) => ({
          threads: [...state.threads, {
            thread_id: msg.payload.thread_id,
            title: msg.payload.title,
            thread_type: msg.payload.thread_type,
            status: msg.payload.status,
            created_at: msg.payload.created_at,
          }],
        }));
        return;
      }

      case "thread.list_result": {
        set({
          threads: msg.payload.threads.map((t: ThreadInfoPayload) => ({
            thread_id: t.thread_id,
            title: t.title,
            thread_type: t.thread_type,
            status: t.status,
            created_at: t.created_at,
          })),
        });
        return;
      }

      case "thread.updated": {
        if (msg.payload.status === "deleted") {
          set((state) => ({
            threads: state.threads.filter((t) => t.thread_id !== msg.payload.thread_id),
          }));
        } else {
          set((state) => ({
            threads: state.threads.map((t) => {
              if (t.thread_id !== msg.payload.thread_id) return t;
              return {
                ...t,
                ...(msg.payload.title !== undefined && msg.payload.title !== null && { title: msg.payload.title }),
                ...(msg.payload.status !== undefined && msg.payload.status !== null && { status: msg.payload.status }),
              };
            }),
          }));
        }
        return;
      }

      case "server.hello": {
        get().refreshThreads();
        return;
      }
    }
  },
}));
