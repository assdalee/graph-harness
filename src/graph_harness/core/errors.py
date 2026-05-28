"""Typed application errors that map to HTTP status codes and error codes."""


class AppError(Exception):
    """Base error carrying an HTTP status, machine code, and structured details."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        """Store the human message and optional structured details."""
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(AppError):
    """Raised when the caller is not authenticated."""

    status_code = 401
    code = "authentication_error"


class AuthorizationError(AppError):
    """Raised when the caller lacks permission for the requested action."""

    status_code = 403
    code = "authorization_error"


class ToolExecutionError(AppError):
    """Raised when a tool invocation fails due to bad input or execution."""

    status_code = 400
    code = "tool_execution_error"


class UpstreamServiceError(AppError):
    """Raised when an upstream dependency (Graph or LLM) fails."""

    status_code = 502
    code = "upstream_service_error"

