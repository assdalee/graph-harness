"""Application settings model and environment-variable parsing helpers."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    """Validated runtime configuration for the harness, sourced from env vars."""

    app_name: str = "GraphHarness"
    app_env: str = "local"
    api_key_name: str = "x-api-key"
    # Gates the HTTP API (the x-api-key header) — NOT an LLM provider credential.
    # Preferred env var: API_GATEWAY_KEY (legacy alias: LLM_API_KEY).
    llm_api_key: str | None = None
    max_request_bytes: int = 1_000_000

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = False

    llm_model: str = "openai/gpt-4o-mini"
    llm_backend: str = "litellm"
    llm_fake_scenarios_path: str | None = None
    # The upstream LLM provider API key passed to LiteLLM.
    # Preferred env var: LLM_PROVIDER_API_KEY (legacy alias: LLM_API_KEY_PROVIDER).
    llm_api_key_provider: str | None = None
    openrouter_api_key: str | None = None
    litellm_api_base: str | None = None
    litellm_temperature: float | None = None
    litellm_max_tokens: int = 2048
    litellm_timeout_seconds: float = 60
    # Override the model-profile tool-history quirk (None = auto-detect by family).
    llm_requires_tools_with_tool_history: bool | None = None

    graph_tenant_id: str = ""
    graph_backend: str = "live"
    graph_client_id: str = ""
    graph_client_secret: str = ""
    graph_scopes: list[str] = Field(
        default_factory=lambda: ["https://graph.microsoft.com/.default"]
    )
    graph_default_api_version: str = "v1.0"
    graph_timeout_seconds: float = 30

    agent_max_turns: int = 4
    agent_max_tool_calls: int = 8
    agent_llm_retries: int = 2
    agent_empty_response_retries: int = 1
    agent_repeated_tool_call_limit: int = 2
    agent_recovery_max_attempts: int = 1
    agent_enable_clarification_policy: bool = True
    agent_enable_context_compaction: bool = True
    agent_context_recent_messages: int = 8
    agent_context_max_tool_chars: int = 1800
    agent_log_trace_events: bool = True
    agent_parallel_reads: bool = True
    agent_require_mutation_confirmation: bool = True
    agent_enable_domain_tool_selection: bool = True
    agent_domain_tool_selection_max_tools: int = 16
    agent_max_wall_clock_seconds: float = 0.0

    runs_enabled: bool = False
    runs_backend: str = "sqlite"
    runs_db_path: str = "./data/runs.sqlite3"

    @field_validator("graph_scopes", "cors_allow_origins", mode="before")
    @classmethod
    def split_csv(cls, value: str | list[str]) -> list[str]:
        """Accept a comma-separated string or list for multi-value fields."""
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @field_validator("agent_max_turns")
    @classmethod
    def clamp_max_turns(cls, value: int) -> int:
        """Keep the agent turn budget within a safe range."""
        return max(1, min(value, 10))

    @field_validator("agent_max_tool_calls")
    @classmethod
    def clamp_max_tool_calls(cls, value: int) -> int:
        """Keep the per-run tool-call budget within a safe range."""
        return max(1, min(value, 20))

    @field_validator("agent_llm_retries")
    @classmethod
    def clamp_llm_retries(cls, value: int) -> int:
        """Keep the LLM retry count within a safe range."""
        return max(0, min(value, 5))

    @field_validator("agent_empty_response_retries")
    @classmethod
    def clamp_empty_response_retries(cls, value: int) -> int:
        """Keep the empty-response retry count within a safe range."""
        return max(0, min(value, 3))

    @field_validator("agent_repeated_tool_call_limit")
    @classmethod
    def clamp_repeated_tool_call_limit(cls, value: int) -> int:
        """Keep the repeated-tool-call limit within a safe range."""
        return max(1, min(value, 5))

    @field_validator("agent_recovery_max_attempts")
    @classmethod
    def clamp_recovery_max_attempts(cls, value: int) -> int:
        """Keep the recovery-attempt count within a safe range."""
        return max(0, min(value, 3))

    @field_validator("agent_context_recent_messages")
    @classmethod
    def clamp_context_recent_messages(cls, value: int) -> int:
        """Keep the recent-message retention window within a safe range."""
        return max(4, min(value, 30))

    @field_validator("agent_context_max_tool_chars")
    @classmethod
    def clamp_context_max_tool_chars(cls, value: int) -> int:
        """Keep the per-tool-output truncation length within a safe range."""
        return max(400, min(value, 12000))

    @field_validator("agent_domain_tool_selection_max_tools")
    @classmethod
    def clamp_domain_tool_selection_max_tools(cls, value: int) -> int:
        """Keep the domain tool-selection cap within a safe range."""
        return max(3, min(value, 50))

    @field_validator("agent_max_wall_clock_seconds")
    @classmethod
    def clamp_wall_clock(cls, value: float) -> float:
        """Clamp the run deadline (0 disables it, else cap at 10 minutes)."""
        # 0 disables the deadline; otherwise cap at 10 minutes.
        return max(0.0, min(value, 600.0))

    @field_validator("max_request_bytes")
    @classmethod
    def clamp_request_bytes(cls, value: int) -> int:
        """Keep the max request-body size within a safe range."""
        return max(1024, min(value, 50_000_000))

    @property
    def api_gateway_key(self) -> str | None:
        """Clear alias for the HTTP API gateway key (see ``llm_api_key``)."""
        return self.llm_api_key

    @property
    def llm_provider_api_key(self) -> str | None:
        """Clear alias for the upstream LLM provider key (see ``llm_api_key_provider``)."""
        return self.llm_api_key_provider

    @classmethod
    def from_env(cls) -> "Settings":
        """Build a Settings instance from environment variables (and .env)."""
        load_dotenv(override=False)
        return cls(
            app_name=_get_str("APP_NAME", cls.model_fields["app_name"].default),
            app_env=_get_str("APP_ENV", cls.model_fields["app_env"].default),
            api_key_name=_get_str("API_KEY_NAME", cls.model_fields["api_key_name"].default),
            llm_api_key=_get_optional_str("API_GATEWAY_KEY") or _get_optional_str("LLM_API_KEY"),
            max_request_bytes=_get_int("MAX_REQUEST_BYTES", 1_000_000),
            cors_allow_origins=_get_str("CORS_ALLOW_ORIGINS", "*"),
            cors_allow_credentials=_get_bool("CORS_ALLOW_CREDENTIALS", False),
            llm_model=_get_str("LLM_MODEL", cls.model_fields["llm_model"].default),
            llm_backend=_get_str("LLM_BACKEND", cls.model_fields["llm_backend"].default),
            llm_fake_scenarios_path=_get_optional_str("LLM_FAKE_SCENARIOS_PATH"),
            llm_api_key_provider=_get_optional_str("LLM_PROVIDER_API_KEY")
            or _get_optional_str("LLM_API_KEY_PROVIDER"),
            openrouter_api_key=_get_optional_str("OPENROUTER_API_KEY"),
            litellm_api_base=_get_optional_str("LITELLM_API_BASE"),
            litellm_temperature=_get_optional_float("LITELLM_TEMPERATURE"),
            litellm_max_tokens=_get_int("LITELLM_MAX_TOKENS", 2048),
            litellm_timeout_seconds=_get_float("LITELLM_TIMEOUT_SECONDS", 60),
            llm_requires_tools_with_tool_history=_get_optional_bool(
                "LLM_REQUIRES_TOOLS_WITH_TOOL_HISTORY"
            ),
            graph_tenant_id=_get_str("GRAPH_TENANT_ID", ""),
            graph_backend=_get_str("GRAPH_BACKEND", cls.model_fields["graph_backend"].default),
            graph_client_id=_get_str("GRAPH_CLIENT_ID", ""),
            graph_client_secret=_get_str("GRAPH_CLIENT_SECRET", ""),
            graph_scopes=_get_str("GRAPH_SCOPES", "https://graph.microsoft.com/.default"),
            graph_default_api_version=_get_str("GRAPH_DEFAULT_API_VERSION", "v1.0"),
            graph_timeout_seconds=_get_float("GRAPH_TIMEOUT_SECONDS", 30),
            agent_max_turns=_get_int("AGENT_MAX_TURNS", 4),
            agent_max_tool_calls=_get_int("AGENT_MAX_TOOL_CALLS", 8),
            agent_llm_retries=_get_int("AGENT_LLM_RETRIES", 2),
            agent_empty_response_retries=_get_int("AGENT_EMPTY_RESPONSE_RETRIES", 1),
            agent_repeated_tool_call_limit=_get_int("AGENT_REPEATED_TOOL_CALL_LIMIT", 2),
            agent_recovery_max_attempts=_get_int("AGENT_RECOVERY_MAX_ATTEMPTS", 1),
            agent_enable_clarification_policy=_get_bool("AGENT_ENABLE_CLARIFICATION_POLICY", True),
            agent_enable_context_compaction=_get_bool("AGENT_ENABLE_CONTEXT_COMPACTION", True),
            agent_context_recent_messages=_get_int("AGENT_CONTEXT_RECENT_MESSAGES", 8),
            agent_context_max_tool_chars=_get_int("AGENT_CONTEXT_MAX_TOOL_CHARS", 1800),
            agent_log_trace_events=_get_bool("AGENT_LOG_TRACE_EVENTS", True),
            agent_parallel_reads=_get_bool("AGENT_PARALLEL_READS", True),
            agent_require_mutation_confirmation=_get_bool(
                "AGENT_REQUIRE_MUTATION_CONFIRMATION",
                True,
            ),
            agent_enable_domain_tool_selection=_get_bool(
                "AGENT_ENABLE_DOMAIN_TOOL_SELECTION",
                True,
            ),
            agent_domain_tool_selection_max_tools=_get_int(
                "AGENT_DOMAIN_TOOL_SELECTION_MAX_TOOLS",
                16,
            ),
            agent_max_wall_clock_seconds=_get_float("AGENT_MAX_WALL_CLOCK_SECONDS", 0.0),
            runs_enabled=_get_bool("RUNS_ENABLED", False),
            runs_backend=_get_str("RUNS_BACKEND", "sqlite"),
            runs_db_path=_get_str("RUNS_DB_PATH", "./data/runs.sqlite3"),
        )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance."""
    return Settings.from_env()


def _get_str(name: str, default: str) -> str:
    """Read a string env var, falling back to the default."""
    value = os.getenv(name)
    return value if value is not None else default


def _get_optional_str(name: str) -> str | None:
    """Read an optional string env var, treating empty as unset."""
    value = os.getenv(name)
    return value or None


def _get_int(name: str, default: int) -> int:
    """Read an integer env var, falling back to the default on parse failure."""
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    """Read a float env var, falling back to the default on parse failure."""
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    """Read a boolean env var from common truthy spellings."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_optional_bool(name: str) -> bool | None:
    """Read an optional boolean env var, returning None when unset."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_optional_float(name: str) -> float | None:
    """Read an optional float env var, returning None when unset or invalid."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None
