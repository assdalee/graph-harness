import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  KeyRound,
  RefreshCw,
  Search,
  Send,
  Server,
  ShieldCheck,
  Wrench,
  XCircle,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AgentTraceEvent,
  ChatMessage,
  ChatResponse,
  OperationSummary,
  getHealth,
  getOperations,
  sendChat,
} from "./api";

const EXAMPLES = [
  "List users",
  "Find Sarah Chen",
  "List high severity alerts",
  "Show OAuth grants",
];

export function App() {
  const [apiKey, setApiKey] = useState("");
  const [health, setHealth] = useState<"checking" | "healthy" | "offline">("checking");
  const [serviceName, setServiceName] = useState("GraphHarness");
  const [operations, setOperations] = useState<OperationSummary[]>([]);
  const [operationFilter, setOperationFilter] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState(EXAMPLES[0]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [selectedResponse, setSelectedResponse] = useState<ChatResponse | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
              <small>{operation.read_only ? "read" : "write"}</small>
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
          <button className="secondary-button" onClick={resetThread}>
            New thread
          </button>
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
              {EXAMPLES.map((example) => (
                <button key={example} onClick={() => setInput(example)}>
                  {example}
                </button>
              ))}
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, index) => (
                <button
                  key={`${message.role}-${index}`}
                  className={`message message-${message.role}`}
                  onClick={() => message.response && setSelectedResponse(message.response)}
                >
                  <span>{message.role}</span>
                  <p>{message.content}</p>
                </button>
              ))}
            </div>
          )}
        </section>

        <form className="composer" onSubmit={onSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask GraphHarness"
            rows={2}
          />
          <button
            className="send-button"
            type="submit"
            disabled={isSending || !input.trim()}
            aria-label={isSending ? "Running request" : "Send message"}
            title={isSending ? "Running" : "Send"}
          >
            {isSending ? <Clock size={18} aria-hidden="true" /> : <Send size={18} aria-hidden="true" />}
          </button>
        </form>
      </main>

      <aside className="inspector">
        <RunSummary response={latestResponse} />
        <ToolTimeline response={latestResponse} />
        <TraceTable events={latestResponse?.trace_events ?? []} />
      </aside>
    </div>
  );
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
