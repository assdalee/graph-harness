import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  History,
  KeyRound,
  Loader2,
  RefreshCw,
  Search,
  Send,
  Server,
  ShieldCheck,
  Sparkles,
  Users,
  Bell,
  KeySquare,
  UserSearch,
  Wrench,
  X,
  XCircle,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AgentTraceEvent,
  ChatMessage,
  ChatResponse,
  OperationSummary,
  RunSummary as RunRow,
  getHealth,
  getOperations,
  getRun,
  listRuns,
  sendChat,
} from "./api";

const EXAMPLES: Array<{ label: string; icon: typeof Users }> = [
  { label: "List users", icon: Users },
  { label: "Find Sarah Chen", icon: UserSearch },
  { label: "List high severity alerts", icon: Bell },
  { label: "Show OAuth grants", icon: KeySquare },
];

export function App() {
  const [apiKey, setApiKey] = useState("");
  const [health, setHealth] = useState<"checking" | "healthy" | "offline">("checking");
  const [serviceName, setServiceName] = useState("GraphHarness");
  const [operations, setOperations] = useState<OperationSummary[]>([]);
  const [operationFilter, setOperationFilter] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState(EXAMPLES[0].label);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [selectedResponse, setSelectedResponse] = useState<ChatResponse | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runsOpen, setRunsOpen] = useState(false);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [runsError, setRunsError] = useState<string | null>(null);
  const [runsAvailable, setRunsAvailable] = useState(true);

  async function refreshMetadata() {
    setHealth("checking");
    try {
      const [healthResponse, operationResponse] = await Promise.all([
        getHealth({ apiKey }),
        getOperations({ apiKey }),
      ]);
      setServiceName(healthResponse.service);
      setOperations(operationResponse.operations);
      setHealth("healthy");
    } catch (caught) {
      setHealth("offline");
      setError(caught instanceof Error ? caught.message : "Unable to reach backend");
    }
  }

  useEffect(() => {
    void refreshMetadata();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredOperations = useMemo(() => {
    const query = operationFilter.trim().toLowerCase();
    if (!query) return operations;
    return operations.filter((operation) => {
      return (
        operation.name.toLowerCase().includes(query) ||
        operation.description.toLowerCase().includes(query)
      );
    });
  }, [operationFilter, operations]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isSending) return;

    setError(null);
    setIsSending(true);
    setInput("");
    setMessages((current) => [...current, { role: "user", content: trimmed }]);

    try {
      const response = await sendChat(trimmed, threadId, { apiKey });
      setThreadId(response.thread_id);
      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: response.answer,
        response,
      };
      setMessages((current) => [...current, assistantMessage]);
      setSelectedResponse(response);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Request failed";
      setError(message);
      setMessages((current) => [...current, { role: "assistant", content: message }]);
    } finally {
      setIsSending(false);
    }
  }

  function resetThread() {
    setThreadId(null);
    setMessages([]);
    setSelectedResponse(null);
    setError(null);
  }

  async function loadRuns() {
    setRunsLoading(true);
    setRunsError(null);
    try {
      const response = await listRuns({ limit: 50 }, { apiKey });
      setRuns(response.runs);
      setRunsAvailable(true);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Failed to load runs";
      setRunsError(message);
      if (/404|Not Found/i.test(message)) {
        setRunsAvailable(false);
      }
    } finally {
      setRunsLoading(false);
    }
  }

  function openRuns() {
    setRunsOpen(true);
    void loadRuns();
  }

  async function selectRun(runId: string) {
    setRunsError(null);
    try {
      const record = await getRun(runId, { apiKey });
      const synthetic: ChatResponse = {
        thread_id: record.thread_id,
        run_id: record.id,
        answer: record.answer,
        status: record.status,
        stop_reason: record.stop_reason,
        turns: record.turns,
        data: record.data,
        tool_calls: record.tool_calls,
        messages: record.messages,
        warnings: record.warnings,
        trace_events: record.trace_events,
      };
      setSelectedResponse(synthetic);
      setMessages([
        { role: "user", content: record.input_message || "(no input)" },
        { role: "assistant", content: record.answer, response: synthetic },
      ]);
      setThreadId(record.thread_id ?? null);
      setRunsOpen(false);
    } catch (caught) {
      setRunsError(caught instanceof Error ? caught.message : "Failed to open run");
    }
  }

  const latestResponse = selectedResponse ?? [...messages].reverse().find((m) => m.response)?.response ?? null;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <ShieldCheck size={22} aria-hidden="true" />
          </div>
          <div>
            <h1>GraphHarness</h1>
            <p>{serviceName}</p>
          </div>
        </div>

        <div className="connection-row">
          <HealthBadge status={health} />
          <button className="icon-button" onClick={() => void refreshMetadata()} title="Refresh">
            <RefreshCw size={16} aria-hidden="true" />
          </button>
        </div>

        <label className="input-label" htmlFor="api-key">
          API key
        </label>
        <div className="api-key">
          <KeyRound size={16} aria-hidden="true" />
          <input
            id="api-key"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="optional"
            type="password"
          />
        </div>

        <div className="section-heading">
          <Wrench size={16} aria-hidden="true" />
          <span>Operations</span>
          <strong>{operations.length}</strong>
        </div>

        <div className="search-box">
          <Search size={16} aria-hidden="true" />
          <input
            value={operationFilter}
            onChange={(event) => setOperationFilter(event.target.value)}
            placeholder="Filter"
          />
        </div>

        <div className="operation-list" aria-label="Operations">
          {filteredOperations.map((operation) => (
            <button
              key={operation.name}
              className="operation-item"
              onClick={() => setInput(operation.name.replaceAll("_", " "))}
              title={operation.description}
            >
              <span>{operation.name}</span>
              <small className={`tag ${operation.read_only ? "tag-read" : "tag-write"}`}>
                {operation.read_only ? "read" : "write"}
              </small>
            </button>
          ))}
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h2>Agent Console</h2>
            <p>{threadId ? `thread ${threadId}` : "new thread"}</p>
          </div>
          <div className="topbar-actions">
            <button className="secondary-button" onClick={openRuns} title="View past runs">
              <History size={14} aria-hidden="true" />
              History
            </button>
            <button className="secondary-button" onClick={resetThread}>
              <RefreshCw size={14} aria-hidden="true" />
              New thread
            </button>
          </div>
        </header>

        {error ? (
          <div className="alert" role="alert">
            <AlertTriangle size={18} aria-hidden="true" />
            <span>{error}</span>
          </div>
        ) : null}

        <section className="chat-panel" aria-label="Conversation">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-card">
                <span className="empty-state-eyebrow">
                  <Sparkles size={12} aria-hidden="true" />
                  Get started
                </span>
                <h3>Talk to the graph</h3>
                <p>
                  Ask the agent to query Microsoft Graph through typed tool contracts. Every run is
                  traced — tool calls, status, and trace events appear in the inspector on the right.
                </p>
                <div className="empty-state-grid">
                  {EXAMPLES.map(({ label, icon: Icon }) => (
                    <button key={label} onClick={() => setInput(label)}>
                      <Icon size={16} aria-hidden="true" />
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, index) => (
                <button
                  key={`${message.role}-${index}`}
                  className={`message message-${message.role}`}
                  onClick={() => message.response && setSelectedResponse(message.response)}
                >
                  <span className="message-avatar" aria-hidden="true">
                    {message.role === "user" ? "You" : <ShieldCheck size={16} />}
                  </span>
                  <span className="message-body">
                    <span className="message-role">{message.role}</span>
                    <p className="message-content">{message.content}</p>
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>

        <form className="composer" onSubmit={onSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="Ask GraphHarness…"
            rows={2}
          />
          <button
            className="send-button"
            type="submit"
            disabled={isSending || !input.trim()}
            aria-label={isSending ? "Running request" : "Send message"}
            title={isSending ? "Running" : "Send"}
          >
            {isSending ? (
              <Loader2 className="sending" size={18} aria-hidden="true" />
            ) : (
              <Send size={18} aria-hidden="true" />
            )}
          </button>
          <span className="composer-hint">
            Press <kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> for newline
          </span>
        </form>
      </main>

      <aside className="inspector">
        <RunSummary response={latestResponse} />
        <ToolTimeline response={latestResponse} />
        <TraceTable events={latestResponse?.trace_events ?? []} />
      </aside>

      {runsOpen ? (
        <RunsDrawer
          runs={runs}
          loading={runsLoading}
          error={runsError}
          available={runsAvailable}
          onClose={() => setRunsOpen(false)}
          onRefresh={() => void loadRuns()}
          onSelect={(runId) => void selectRun(runId)}
        />
      ) : null}
    </div>
  );
}

function RunsDrawer({
  runs,
  loading,
  error,
  available,
  onClose,
  onRefresh,
  onSelect,
}: {
  runs: RunRow[];
  loading: boolean;
  error: string | null;
  available: boolean;
  onClose: () => void;
  onRefresh: () => void;
  onSelect: (runId: string) => void;
}) {
  return (
    <div className="drawer-overlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="drawer" onClick={(event) => event.stopPropagation()}>
        <header className="drawer-header">
          <div>
            <h3>Run history</h3>
            <p>{available ? `${runs.length} most recent run${runs.length === 1 ? "" : "s"}` : "Run store disabled"}</p>
          </div>
          <div className="drawer-actions">
            <button className="icon-button" onClick={onRefresh} title="Refresh">
              <RefreshCw size={16} aria-hidden="true" className={loading ? "sending" : undefined} />
            </button>
            <button className="icon-button" onClick={onClose} title="Close">
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        </header>

        {!available ? (
          <div className="placeholder">
            Set <code>RUNS_ENABLED=true</code> in the backend env to capture run history.
          </div>
        ) : error ? (
          <div className="alert" role="alert">
            <AlertTriangle size={16} aria-hidden="true" />
            <span>{error}</span>
          </div>
        ) : loading && runs.length === 0 ? (
          <div className="placeholder">Loading…</div>
        ) : runs.length === 0 ? (
          <div className="placeholder">No runs recorded yet.</div>
        ) : (
          <ul className="runs-list">
            {runs.map((run) => (
              <li key={run.id}>
                <button className="run-item" onClick={() => onSelect(run.id)}>
                  <div className="run-item-row">
                    <span className={`run-status run-status-${run.status}`}>{run.status}</span>
                    <span className="run-meta">{formatRelativeTime(run.created_at)}</span>
                  </div>
                  <div className="run-item-message">{run.input_message || <em>(no input)</em>}</div>
                  <div className="run-item-row run-item-footer">
                    <span title="tool calls">
                      <Wrench size={12} aria-hidden="true" />
                      {run.tool_call_count}
                    </span>
                    <span title="turns">
                      <Activity size={12} aria-hidden="true" />
                      {run.turns}
                    </span>
                    <span title="duration">{run.duration_ms} ms</span>
                    {run.llm_model ? <span className="run-model">{run.llm_model}</span> : null}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diff = Date.now() - then;
  const seconds = Math.round(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function HealthBadge({ status }: { status: "checking" | "healthy" | "offline" }) {
  const icon =
    status === "healthy" ? (
      <CheckCircle2 size={16} aria-hidden="true" />
    ) : status === "offline" ? (
      <XCircle size={16} aria-hidden="true" />
    ) : (
      <Server size={16} aria-hidden="true" />
    );
  return (
    <span className={`health health-${status}`}>
      {icon}
      {status}
    </span>
  );
}

function RunSummary({ response }: { response: ChatResponse | null }) {
  return (
    <section className="inspector-section">
      <div className="section-heading">
        <Activity size={16} aria-hidden="true" />
        <span>Run</span>
      </div>
      {response ? (
        <div className="run-grid">
          <Metric label="status" value={response.status} tone={response.status} />
          <Metric label="stop" value={response.stop_reason} />
          <Metric label="turns" value={String(response.turns)} />
          <Metric label="tools" value={String(response.tool_calls.length)} />
          {response.warnings.map((warning) => (
            <div className="warning" key={warning}>
              <AlertTriangle size={15} aria-hidden="true" />
              {warning}
            </div>
          ))}
        </div>
      ) : (
        <div className="placeholder">No run selected</div>
      )}
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className={`metric metric-${tone ?? "neutral"}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ToolTimeline({ response }: { response: ChatResponse | null }) {
  return (
    <section className="inspector-section tool-section">
      <div className="section-heading">
        <Wrench size={16} aria-hidden="true" />
        <span>Tools</span>
      </div>
      {response?.tool_calls.length ? (
        <div className="tool-list">
          {response.tool_calls.map((tool) => (
            <details key={tool.id} className="tool-card">
              <summary>
                <span>{tool.name}</span>
                <small className={tool.result?.ok === false || tool.error ? "bad" : "good"}>
                  {tool.result?.ok === false || tool.error ? "error" : "ok"}
                </small>
              </summary>
              <pre>{JSON.stringify({ args: tool.args, result: tool.result, error: tool.error }, null, 2)}</pre>
            </details>
          ))}
        </div>
      ) : (
        <div className="placeholder">No tools</div>
      )}
    </section>
  );
}

function TraceTable({ events }: { events: AgentTraceEvent[] }) {
  return (
    <section className="inspector-section trace-section">
      <div className="section-heading">
        <Activity size={16} aria-hidden="true" />
        <span>Trace</span>
      </div>
      {events.length ? (
        <div className="trace-list">
          {events.map((event, index) => (
            <details key={`${event.event}-${index}`} className="trace-row">
              <summary>
                <span>{event.event}</span>
                <small>turn {event.turn}</small>
              </summary>
              <p>{event.message}</p>
              <pre>{JSON.stringify(event.metadata, null, 2)}</pre>
            </details>
          ))}
        </div>
      ) : (
        <div className="placeholder">No trace events</div>
      )}
    </section>
  );
}
