import {
  parseServerMessage,
  type ClientMessage,
  type ServerMessage,
} from "@/lib/ws/types";

const DEFAULT_URL = "ws://localhost:5173/ws";
const HELLO_PROTOCOL_VERSION = "1.0";
const MAX_BACKOFF_MS = 10_000;

function createId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export class DotiWsClient {
  private readonly url: string;
  private socket: WebSocket | null = null;
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private shouldReconnect = true;
  private isConnecting = false;
  private readonly handlers = new Set<(msg: ServerMessage) => void>();

  constructor(url: string = DEFAULT_URL) {
    this.url = url;
  }

  get connected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  connect(): void {
    if (this.connected || this.isConnecting) {
      return;
    }

    if (
      this.socket &&
      (this.socket.readyState === WebSocket.CONNECTING ||
        this.socket.readyState === WebSocket.OPEN)
    ) {
      return;
    }

    this.clearReconnectTimer();
    this.shouldReconnect = true;
    this.isConnecting = true;

    const ws = new WebSocket(this.url);
    this.socket = ws;

    ws.onopen = () => {
      this.isConnecting = false;
      this.reconnectAttempt = 0;

      const hello: ClientMessage = {
        type: "client.hello",
        event_id: createId(),
        ts: Date.now(),
        payload: {
          protocol_version: HELLO_PROTOCOL_VERSION,
        },
      };

      ws.send(JSON.stringify(hello));
    };

    ws.onmessage = (event) => {
      if (typeof event.data !== "string") {
        return;
      }

      try {
        const parsed = parseServerMessage(event.data);
        for (const handler of this.handlers) {
          handler(parsed);
        }
      } catch {
        // Ignore malformed payloads.
      }
    };

    ws.onclose = () => {
      this.isConnecting = false;
      if (this.socket === ws) {
        this.socket = null;
      }

      if (!this.shouldReconnect) {
        return;
      }

      this.scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.isConnecting = false;
    this.clearReconnectTimer();

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  send(msg: ClientMessage): void {
    if (!this.connected || !this.socket) {
      return;
    }

    this.socket.send(JSON.stringify(msg));
  }

  onMessage(handler: (msg: ServerMessage) => void): void {
    this.handlers.add(handler);
  }

  private scheduleReconnect(): void {
    this.clearReconnectTimer();

    const delay = Math.min(1_000 * 2 ** this.reconnectAttempt, MAX_BACKOFF_MS);
    this.reconnectAttempt += 1;

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
