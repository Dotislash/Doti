export type RunState = "queued" | "running" | "completed" | "failed" | "cancelled";

export type ErrorCode =
  | "invalid_message"
  | "conversation_busy"
  | "internal_error"
  | "provider_error"
  | "thread_not_found"
  | "executor_not_found"
  | "executor_error";

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

export type HistoryMessagePayload = {
  id: string;
  role: "user" | "assistant";
  content: string;
  ts: number;
};

export type HistorySyncPayload = {
  conversation_id: string;
  messages: HistoryMessagePayload[];
  items?: Record<string, unknown>[];
  has_more: boolean;
};

// Thread types
export type ThreadCreatePayload = {
  title?: string;
  executor?: string;
  thread_type?: "task" | "focus";
};

export type ThreadListPayload = Record<string, never>;

export type ThreadDeletePayload = {
  thread_id: string;
};

export type ThreadInfoPayload = {
  thread_id: string;
  title: string | null;
  executor?: string | null;
  thread_type: string;
  status: string;
  created_at: string;
};

export type ThreadListResultPayload = {
  threads: ThreadInfoPayload[];
};

export type ThreadUpdatedPayload = {
  thread_id: string;
  title?: string | null;
  executor?: string | null;
  status?: string | null;
};

// Agent thinking
export type AgentThinkingPayload = {
  conversation_id: string;
  run_id: string;
  content: string;
  iteration: number;
};

// Tool types
export type ToolRequestPayload = {
  approval_id: string;
  conversation_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  risk_level: string;
};

export type ToolResultPayload = {
  conversation_id: string;
  tool_name: string;
  result: string;
  is_error: boolean;
};

export type ToolApprovePayload = {
  approval_id: string;
  approved: boolean;
};

// Executor types
export type ExecutorListPayload = Record<string, never>;

export type ExecutorStatusPayload = {
  executor_id: string;
};

export type ExecutorAttachPayload = {
  executor_id: string;
};

export type ExecutorDetachPayload = Record<string, never>;

export type ExecutorListResultPayload = {
  executors: Array<{
    id: string;
    workspace: string;
    image: string;
    status: string;
    last_activity: number | null;
  }>;
};

export type ExecutorStatusResultPayload = {
  executor_id: string;
  status: string;
  endpoint?: string | null;
};

export type ErrorPayload = {
  code: ErrorCode;
  message: string;
  run_id?: string;
};

// Client messages
export type ClientHelloMessage = Envelope<"client.hello", ClientHelloPayload>;
export type ChatSendMessage = Envelope<"chat.send", ChatSendPayload>;
export type ThreadCreateMessage = Envelope<"thread.create", ThreadCreatePayload>;
export type ThreadListMessage = Envelope<"thread.list", ThreadListPayload>;
export type ThreadDeleteMessage = Envelope<"thread.delete", ThreadDeletePayload>;
export type ToolApproveMessage = Envelope<"tool.approve", ToolApprovePayload>;
export type ExecutorListMessage = Envelope<"executor.list", ExecutorListPayload>;
export type ExecutorStatusMessage = Envelope<"executor.status", ExecutorStatusPayload>;
export type ExecutorAttachMessage = Envelope<"executor.attach", ExecutorAttachPayload>;
export type ExecutorDetachMessage = Envelope<"executor.detach", ExecutorDetachPayload>;

// Server messages
export type ServerHelloMessage = Envelope<"server.hello", ServerHelloPayload>;
export type ChatDeltaMessage = Envelope<"chat.delta", ChatDeltaPayload>;
export type ChatFinalMessage = Envelope<"chat.final", ChatFinalPayload>;
export type RunStateMessage = Envelope<"run.state", RunStatePayload>;
export type HistorySyncMessage = Envelope<"history.sync", HistorySyncPayload>;
export type ThreadCreatedMessage = Envelope<"thread.created", ThreadInfoPayload>;
export type ThreadListResultMessage = Envelope<"thread.list_result", ThreadListResultPayload>;
export type ThreadUpdatedMessage = Envelope<"thread.updated", ThreadUpdatedPayload>;
export type AgentThinkingMessage = Envelope<"agent.thinking", AgentThinkingPayload>;
export type ToolRequestMessage = Envelope<"tool.request", ToolRequestPayload>;
export type ToolResultMessage = Envelope<"tool.result", ToolResultPayload>;
export type ExecutorListResultMessage = Envelope<"executor.list_result", ExecutorListResultPayload>;
export type ExecutorStatusResultMessage = Envelope<"executor.status_result", ExecutorStatusResultPayload>;
export type ErrorMessage = Envelope<"error", ErrorPayload>;

export type ClientMessage =
  | ClientHelloMessage
  | ChatSendMessage
  | ThreadCreateMessage
  | ThreadListMessage
  | ThreadDeleteMessage
  | ToolApproveMessage
  | ExecutorListMessage
  | ExecutorStatusMessage
  | ExecutorAttachMessage
  | ExecutorDetachMessage;

export type ServerMessage =
  | ServerHelloMessage
  | ChatDeltaMessage
  | ChatFinalMessage
  | RunStateMessage
  | HistorySyncMessage
  | ThreadCreatedMessage
  | ThreadListResultMessage
  | ThreadUpdatedMessage
  | AgentThinkingMessage
  | ToolRequestMessage
  | ToolResultMessage
  | ExecutorListResultMessage
  | ExecutorStatusResultMessage
  | ErrorMessage;

export function parseServerMessage(data: string): ServerMessage {
  return JSON.parse(data) as ServerMessage;
}
