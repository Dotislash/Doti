export type RunState = "queued" | "running" | "completed" | "failed" | "cancelled";

export type ErrorCode =
  | "invalid_message"
  | "conversation_busy"
  | "internal_error"
  | "provider_error";

type Envelope<TType extends string, TPayload> = {
  type: TType;
  event_id: string;
  ts: number;
  payload: TPayload;
};

export type ClientHelloPayload = {
  protocol_version: string;
  client_id?: string;
};

export type ChatSendPayload = {
  conversation_id?: string;
  content: string;
  client_msg_id: string;
};

export type ServerHelloPayload = {
  protocol_version: string;
  server_id: string;
};

export type ChatDeltaPayload = {
  conversation_id: string;
  run_id: string;
  seq: number;
  delta: string;
};

export type ChatFinalPayload = {
  conversation_id: string;
  run_id: string;
  message_id: string;
  content: string;
};

export type RunStatePayload = {
  run_id: string;
  conversation_id: string;
  state: RunState;
};

export type ErrorPayload = {
  code: ErrorCode;
  message: string;
  run_id?: string;
};

export type ClientHelloMessage = Envelope<"client.hello", ClientHelloPayload>;
export type ChatSendMessage = Envelope<"chat.send", ChatSendPayload>;

export type ServerHelloMessage = Envelope<"server.hello", ServerHelloPayload>;
export type ChatDeltaMessage = Envelope<"chat.delta", ChatDeltaPayload>;
export type ChatFinalMessage = Envelope<"chat.final", ChatFinalPayload>;
export type RunStateMessage = Envelope<"run.state", RunStatePayload>;
export type ErrorMessage = Envelope<"error", ErrorPayload>;

export type ClientMessage = ClientHelloMessage | ChatSendMessage;

export type ServerMessage =
  | ServerHelloMessage
  | ChatDeltaMessage
  | ChatFinalMessage
  | RunStateMessage
  | ErrorMessage;

export function parseServerMessage(data: string): ServerMessage {
  return JSON.parse(data) as ServerMessage;
}
