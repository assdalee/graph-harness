"""Pydantic response models describing available operations and domains for the API."""

from typing import Any

from pydantic import BaseModel, Field


class OperationSummary(BaseModel):
    """Catalog entry for one operation, including its safety and permission metadata."""

    name: str
    description: str
    read_only: bool
    requires_confirmation: bool
    domain: str = "general"
    safety: str = "read_only"
    required_permissions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    args_schema: dict[str, Any] = Field(default_factory=dict)


class DomainSummary(BaseModel):
    """Catalog entry for one operation domain and its aggregate operation count."""

    name: str
    display_name: str
    description: str
    required_permissions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    operation_count: int


class OperationsResponse(BaseModel):
    """Response listing all exposed operations grouped by domain with counts."""

    operation_count: int
    domain_count: int = 0
    domains: list[DomainSummary] = Field(default_factory=list)
    operations: list[OperationSummary]
