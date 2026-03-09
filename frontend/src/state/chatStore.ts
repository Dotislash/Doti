import { create } from "zustand";

import { DotiWsClient } from "@/lib/ws/client";
import type { ClientMessage, RunState, ServerMessage } from "@/lib/ws/types";

type ChatItem = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type ChatStore = {
  messages: ChatItem[];
  streamingContent: string;
  isStreaming: boolean;
  runState: RunState | null;
  error: string | null;
  connect: () => void;
  sendMessage: (content: string) => void;
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
  messages: [],
  streamingContent: "",
  isStreaming: false,
  runState: null,
  error: null,
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
    if (!trimmed) {
      return;
    }

    // Ensure connected
    get().connect();
    const client = get().client!;

    const userMessage: ChatItem = {
      id: createId(),
      role: "user",
      content: trimmed,
    };

    const outbound: ClientMessage = {
      type: "chat.send",
      event_id: createId(),
      ts: Date.now(),
      payload: {
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
            {
              id: msg.payload.message_id,
              role: "assistant",
              content: msg.payload.content,
            },
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
        set({
          error: msg.payload.message,
          isStreaming: false,
          streamingContent: "",
        });
        return;
      }

      case "server.hello": {
        return;
      }
    }
  },
}));
