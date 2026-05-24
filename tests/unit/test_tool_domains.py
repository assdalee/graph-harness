from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.tools.graph_tools import GraphToolFactory


def build_registry():
    return GraphToolFactory(MockGraphClient(), GraphOperationCatalog.default()).build_registry()


def test_registry_exposes_graph_capability_domains() -> None:
    registry = build_registry()

    domains = {domain.name: domain for domain in registry.list_domains()}

    assert {
        "identity_access",
        "security",
        "audit_activity",
        "devices",
        "catalog_operations",
    } <= set(domains)
    assert domains["identity_access"].display_name == "Identity and Access"
    assert "User.Read.All" in domains["identity_access"].required_permissions


def test_tools_are_classified_by_domain_and_safety() -> None:
    registry = build_registry()

    delete_grant = registry.get("delete_oauth_permission_grant")
    security_alerts = registry.get("list_security_alerts")
    sign_ins = registry.get("list_sign_in_logs")

    assert delete_grant is not None
    assert delete_grant.domain == "identity_access"
    assert delete_grant.safety == "destructive"
    assert delete_grant.requires_confirmation is True
    assert security_alerts is not None
    assert security_alerts.domain == "security"
    assert sign_ins is not None
    assert sign_ins.domain == "audit_activity"


def test_domain_tool_selection_picks_relevant_security_tools() -> None:
    registry = build_registry()

    selected = registry.select_tools_for_query("List high severity security alerts", max_tools=6)
    names = {tool.name for tool in selected}

    assert "list_security_alerts" in names
    assert {tool.domain for tool in selected} == {"security"}


def test_domain_tool_selection_keeps_identity_resolvers_for_group_workflow() -> None:
    registry = build_registry()

    selected = registry.select_tools_for_query("Add Sarah to the Finance group", max_tools=16)
    names = {tool.name for tool in selected}

    assert "resolve_user" in names
    assert "resolve_group" in names
    assert "add_group_member" in names


def test_domain_tool_selection_falls_back_to_full_registry_when_ambiguous() -> None:
    registry = build_registry()

    selected = registry.select_tools_for_query("Summarize whatever is useful", max_tools=6)

    assert len(selected) == len(registry.list())


def test_domain_tool_selection_anchors_recovery_on_failed_tool_name() -> None:
    registry = build_registry()

    selected = registry.select_tools_for_query(
        "Recovery policy instruction: Tool `list_users` failed with `rate_limited`.",
        max_tools=16,
    )
    names = {tool.name for tool in selected}

    assert "list_users" in names
    assert {tool.domain for tool in selected} == {"identity_access"}
