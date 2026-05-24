from graph_harness.api_models.operations import DomainSummary, OperationSummary, OperationsResponse
from graph_harness.tools.registry import ToolRegistry


class OperationsService:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def list_operations(self) -> OperationsResponse:
        operations = [
            OperationSummary(
                name=tool.name,
                description=tool.description,
                read_only=tool.read_only,
                requires_confirmation=tool.requires_confirmation,
                domain=tool.domain,
                safety=tool.safety,
                required_permissions=list(tool.required_permissions),
                tags=list(tool.tags),
                args_schema=tool.args_model.model_json_schema(),
            )
            for tool in self._registry.list()
        ]
        domains = [
            DomainSummary(
                name=domain.name,
                display_name=domain.display_name,
                description=domain.description,
                required_permissions=list(domain.required_permissions),
                tags=list(domain.tags),
                operation_count=len(self._registry.tools_for_domain(domain.name)),
            )
            for domain in self._registry.list_domains()
        ]
        return OperationsResponse(
            operation_count=len(operations),
            domain_count=len(domains),
            domains=domains,
            operations=operations,
        )
