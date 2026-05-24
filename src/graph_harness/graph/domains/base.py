from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from graph_harness.tools.base import ToolDefinition


@dataclass(frozen=True)
class DomainMetadata:
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
        return self.metadata.name

    @abstractmethod
    def tools(self) -> list[ToolDefinition]:
        raise NotImplementedError
