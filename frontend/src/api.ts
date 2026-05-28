const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export type HealthResponse = {
  status: string;
  service: string;
};

export type OperationSummary = {
  name: string;
  description: string;
  read_only: boolean;
  requires_confirmation: boolean;
  args_schema: Record<string, unknown>;
};

export type OperationsResponse = {
  operation_count: number;
  operations: OperationSummary[];
};

export type ToolError = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  retryable?: boolean;
};

export type ToolResult = {
  ok: boolean;
  data: unknown;
  summary: string;
  identifiers: Array<Record<string, unknown>>;
  error: ToolError | null;
};

export type ToolCallRecord = {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result: ToolResult | null;
  error: ToolError | null;
  read_only: boolean;
};

export type AgentTraceEvent = {
  event: string;
  turn: number;
  message: string;
  metadata: Record<string, unknown>;
};

export type LLMCallRecord = {
  turn: number;
  phase: string;
  compacted: boolean;
  tool_count: number;
  messages: Array<Record<string, unknown>>;
};

export type ChatResponse = {
  thread_id: string | null;
  run_id: string | null;
  answer: string;
  status: string;
  stop_reason: string;
  turns: number;
  data: unknown[];
  tool_calls: ToolCallRecord[];
  messages: Array<Record<string, unknown>>;
  warnings: string[];
  trace_events: AgentTraceEvent[];
  llm_calls: LLMCallRecord[];
};

export type RunSummary = {
  id: string;
  thread_id: string | null;
  user_id: string | null;
  created_at: string;
  finished_at: string;
  duration_ms: number;
  input_message: string;
  llm_model: string | null;
  llm_backend: string | null;
  status: string;
  stop_reason: string;
  turns: number;
  tool_call_count: number;
  warning_count: number;
  tags: Record<string, unknown>;
};

export type RunRecord = ChatResponse & {
  id: string;
  user_id: string | null;
  created_at: string;
  finished_at: string;
  duration_ms: number;
  input_message: string;
  llm_model: string | null;
  llm_backend: string | null;
  config_snapshot: Record<string, unknown>;
  tags: Record<string, unknown>;
};

export type RunListResponse = {
  runs: RunSummary[];
  total: number;
  limit: number;
  offset: number;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
};

type RequestOptions = {
  apiKey?: string;
};

export async function getHealth(options: RequestOptions = {}): Promise<HealthResponse> {
  return request<HealthResponse>("/health", { method: "GET" }, options);
}

export async function getOperations(options: RequestOptions = {}): Promise<OperationsResponse> {
  return request<OperationsResponse>("/v1/graph/operations", { method: "GET" }, options);
}

export async function sendChat(
  message: string,
  threadId: string | null,
  options: RequestOptions = {},
): Promise<ChatResponse> {
  return request<ChatResponse>(
    "/v1/graph/chat",
    {
      method: "POST",
      body: JSON.stringify({
        thread_id: threadId,
        messages: [{ role: "user", content: message }],
      }),
    },
    options,
  );
}

export async function listRuns(
  params: { status?: string; threadId?: string; limit?: number } = {},
  options: RequestOptions = {},
): Promise<RunListResponse> {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.threadId) search.set("thread_id", params.threadId);
  search.set("limit", String(params.limit ?? 50));
  const query = search.toString();
  return request<RunListResponse>(
    `/v1/runs${query ? `?${query}` : ""}`,
    { method: "GET" },
    options,
  );
}

export async function getRun(runId: string, options: RequestOptions = {}): Promise<RunRecord> {
  return request<RunRecord>(`/v1/runs/${encodeURIComponent(runId)}`, { method: "GET" }, options);
}

async function request<T>(
  path: string,
  init: RequestInit,
  options: RequestOptions,
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("content-type", "application/json");
  if (options.apiKey) {
    headers.set("x-api-key", options.apiKey);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : response.statusText;
    throw new Error(detail || "Request failed");
  }
  return payload as T;
}
