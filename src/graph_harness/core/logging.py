"""Request-id-aware logging configuration for cross-log correlation."""

import logging
import sys
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(value: str) -> None:
    """Bind the current request id for this execution context."""
    _request_id.set(value)


def get_request_id() -> str:
    """Return the request id bound to the current context, or a placeholder."""
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    """Inject the current request id onto every log record for correlation."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach the current request id to the record and keep it."""
        record.request_id = get_request_id()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Install a stdout handler that stamps every record with the request id."""
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s %(message)s")
    )
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
