"""Base abstractions for Microsoft Graph capability domains and their tool contracts."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from graph_harness.tools.base import ToolDefinition


@dataclass(frozen=True)
class DomainMetadata:
    """Identifying details and required permissions for a Graph domain."""

    name: str
    display_name: str
    description: str
    required_permissions: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


class GraphDomain(ABC):
    """Owns a Microsoft Graph capability family and its tool contracts."""

    metadata: DomainMetadata

    @property
    def name(self) -> str:
        """Return the domain's stable identifier from its metadata."""
        return self.metadata.name

    @abstractmethod
    def tools(self) -> list[ToolDefinition]:
        """Return the tool contracts this domain exposes to the agent."""
        raise NotImplementedError
