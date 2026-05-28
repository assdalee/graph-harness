"""Shared Pydantic response models reused across HTTP API endpoints."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error payload returned for failed API requests."""

    detail: str = Field(description="Human-readable error message")
    code: str | None = Field(default=None, description="Stable error code")


class HealthResponse(BaseModel):
    """Health-check payload reporting service liveness."""

    status: str = Field(examples=["ok"])
    service: str

