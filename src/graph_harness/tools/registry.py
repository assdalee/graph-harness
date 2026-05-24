from __future__ import annotations

import re

from graph_harness.graph.domains.base import DomainMetadata, GraphDomain
from graph_harness.tools.base import ToolDefinition


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._domains: dict[str, DomainMetadata] = {}

    def register_domain(self, domain: GraphDomain) -> None:
        if domain.name in self._domains:
            raise ValueError(f"Duplicate domain registered: {domain.name}")
        self._domains[domain.name] = domain.metadata
        for tool in domain.tools():
            self.register(tool)

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool registered: {tool.name}")
        if tool.domain not in self._domains:
            self._domains[tool.domain] = DomainMetadata(
                name=tool.domain,
                display_name=tool.domain.replace("_", " ").title(),
                description=f"{tool.domain} tools.",
            )
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list(self) -> list[ToolDefinition]:
        return sorted(self._tools.values(), key=lambda tool: tool.name)

    def openai_tools(self) -> list[dict]:
        return [tool.to_openai_tool() for tool in self.list()]

    def list_domains(self) -> list[DomainMetadata]:
        return sorted(self._domains.values(), key=lambda domain: domain.name)

    def tools_for_domain(self, domain: str) -> list[ToolDefinition]:
        return [tool for tool in self.list() if tool.domain == domain]

    def search_tools(self, query: str, *, max_tools: int | None = None) -> list[ToolDefinition]:
        tokens = _tokenize(query)
        if not tokens:
            return self.list()

        scored = [(self._score_tool(tool, tokens), tool) for tool in self.list()]
        matches = [(score, tool) for score, tool in scored if score > 0]
        if not matches:
            return self.list()

        matches.sort(key=lambda item: (-item[0], item[1].name))
        selected = [tool for _score, tool in matches]
        if max_tools is not None and len(selected) > max_tools:
            selected = selected[:max_tools]
        return selected

    def select_tools_for_query(self, query: str, *, max_tools: int) -> list[ToolDefinition]:
        """Select a compact, domain-aware tool set for one model turn.

        This keeps context smaller without making the model depend on a proprietary
        provider-side tool-search feature.
        """
        tokens = _tokenize(query)
        if not tokens:
            return self.list()

        domain_scores = [
            (
                self._score_domain(domain, tokens)
                + sum(
                    self._score_tool(tool, tokens) for tool in self.tools_for_domain(domain.name)
                ),
                domain,
            )
            for domain in self.list_domains()
        ]
        ranked_domains = [
            (score, domain)
            for score, domain in sorted(domain_scores, key=lambda item: (-item[0], item[1].name))
            if score > 0
        ]
        top_score = ranked_domains[0][0] if ranked_domains else 0
        selected_domains = [
            domain.name for score, domain in ranked_domains if score >= max(2, int(top_score * 0.6))
        ][:2]
        if not selected_domains:
            return self.list()

        domain_tools = [tool for tool in self.list() if tool.domain in selected_domains]
        if len(domain_tools) <= max_tools:
            return domain_tools

        ranked = self.search_tools(query, max_tools=max_tools)
        domain_ranked = [tool for tool in ranked if tool.domain in selected_domains]
        if len(domain_ranked) >= min(3, max_tools):
            return domain_ranked[:max_tools]
        return domain_tools[:max_tools]

    def _score_domain(self, domain: DomainMetadata, tokens: set[str]) -> int:
        haystack = " ".join(
            [
                domain.name,
                domain.display_name,
                domain.description,
                " ".join(domain.tags),
            ]
        ).lower()
        return sum(3 for token in tokens if token in haystack)

    def _score_tool(self, tool: ToolDefinition, tokens: set[str]) -> int:
        haystack = " ".join(
            [
                tool.name.replace("_", " "),
                tool.description,
                tool.domain.replace("_", " "),
                tool.safety,
                " ".join(tool.tags),
                " ".join(tool.required_permissions),
            ]
        ).lower()
        score = 0
        for token in tokens:
            if token in tool.name.lower().split("_"):
                score += 5
            elif token in haystack:
                score += 2
        return score


def _tokenize(text: str) -> set[str]:
    aliases = {
        "signin": "sign in",
        "signins": "sign in",
        "oauth": "oauth grant permission app consent",
        "mfa": "authentication",
        "entra": "identity directory user group",
    }
    normalized = text.lower()
    for source, target in aliases.items():
        normalized = normalized.replace(source, target)
    stopwords = {
        "and",
        "are",
        "can",
        "for",
        "from",
        "graph",
        "failed",
        "list",
        "microsoft",
        "not",
        "now",
        "only",
        "otherwise",
        "policy",
        "request",
        "retry",
        "the",
        "this",
        "tool",
        "using",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", normalized)
        if len(token) > 2 and token not in stopwords
    }
