from datetime import datetime, timezone
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from graph_harness.graph.domains.base import DomainMetadata, GraphDomain
from graph_harness.graph.client import GraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.tools.base import ConfirmableArgs, ToolDefinition
from graph_harness.tools.registry import ToolRegistry
from graph_harness.tools.results import ToolResult


class PaginationArgs(BaseModel):
    top: int | None = Field(default=25, ge=1, le=999)
    all_pages: bool = Field(
        default=False, description="Fetch additional pages when Graph returns @odata.nextLink."
    )
    max_pages: int = Field(default=1, ge=1, le=10)


class ResolveUserArgs(BaseModel):
    query: str = Field(description="User display name, mail, UPN, or object ID.")
    allow_ambiguous: bool = Field(default=False)


class ResolveGroupArgs(BaseModel):
    query: str = Field(description="Group display name, mail nickname, mail, or object ID.")
    allow_ambiguous: bool = Field(default=False)


class ListUsersArgs(PaginationArgs):
    select_fields: list[str] | None = Field(default=None)
    filter_expression: str | None = Field(default=None)


class GetUserArgs(BaseModel):
    user_id: str = Field(description="User object ID or userPrincipalName.")
    select_fields: list[str] | None = None


class SearchUserArgs(BaseModel):
    query: str = Field(description="Display name, mail, or userPrincipalName to search for.")
    top: int = Field(default=5, ge=1, le=25)


class UpdateUserArgs(ConfirmableArgs):
    user_id: str
    update_data: dict[str, Any]


class DeleteUserArgs(ConfirmableArgs):
    user_id: str


class RevokeUserSessionsArgs(ConfirmableArgs):
    user_id: str


class ListGroupsArgs(PaginationArgs):
    select_fields: list[str] | None = None
    filter_expression: str | None = None


class GetGroupArgs(BaseModel):
    group_id: str


class ListGroupMembersArgs(PaginationArgs):
    group_id: str
    select_fields: list[str] | None = None
    top: int | None = Field(default=50, ge=1, le=999)


class AddGroupMemberArgs(ConfirmableArgs):
    group_id: str
    member_id: str


class RemoveGroupMemberArgs(ConfirmableArgs):
    group_id: str
    member_id: str


class ListDevicesArgs(PaginationArgs):
    select_fields: list[str] | None = None
    filter_expression: str | None = None


class GetDeviceArgs(BaseModel):
    device_id: str = Field(description="Directory device object ID.")
    select_fields: list[str] | None = None


class LogQueryArgs(PaginationArgs):
    user_principal_name: str | None = None
    created_after: datetime | None = None
    status_error_code: int | None = None
    filter_expression: str | None = None


SecuritySeverity = Literal["unknown", "informational", "low", "medium", "high"]
SecurityStatus = Literal["unknown", "new", "inProgress", "resolved"]


class SecurityListArgs(PaginationArgs):
    severity: SecuritySeverity | None = None
    status: SecurityStatus | None = None
    created_after: datetime | None = None
    assigned_to: str | None = None
    filter_expression: str | None = None
    count: bool | None = None


AlertClassification = Literal[
    "unknown", "falsePositive", "truePositive", "informationalExpectedActivity"
]


class GetSecurityAlertArgs(BaseModel):
    alert_id: str = Field(description="Microsoft Graph security alert (alerts_v2) ID.")


class GetSecurityIncidentArgs(BaseModel):
    incident_id: str = Field(description="Microsoft Graph security incident ID.")


class UpdateSecurityAlertArgs(ConfirmableArgs):
    alert_id: str
    status: SecurityStatus | None = None
    assigned_to: str | None = None
    classification: AlertClassification | None = None
    determination: str | None = None


class ListServicePrincipalsArgs(PaginationArgs):
    app_id: str | None = None
    display_name: str | None = None
    select_fields: list[str] | None = None


class ListOAuthPermissionGrantsArgs(PaginationArgs):
    client_id: str | None = None
    consent_type: str | None = None


class DeleteOAuthPermissionGrantArgs(ConfirmableArgs):
    grant_id: str


class GenericGraphOperationArgs(ConfirmableArgs):
    operation_name: str
    path_params: dict[str, Any] = Field(default_factory=dict)
    body: dict[str, Any] | None = None
    query_params: dict[str, Any] | None = None
    api_version: str | None = None


class IdentityAccessDomain(GraphDomain):
    metadata = DomainMetadata(
        name="identity_access",
        display_name="Identity and Access",
        description=(
            "Users, groups, directory apps, service principals, OAuth grants, and "
            "identity mutations such as session revocation or group membership changes."
        ),
        required_permissions=(
            "User.Read.All",
            "Group.Read.All",
            "Directory.Read.All",
            "Application.Read.All",
            "DelegatedPermissionGrant.ReadWrite.All",
        ),
        tags=(
            "identity",
            "access",
            "entra",
            "azure ad",
            "users",
            "groups",
            "apps",
            "service principals",
            "oauth",
            "permissions",
            "resolve",
            "lookup",
            "name",
            "mail",
            "upn",
        ),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "resolve_user",
                "Resolve a user name, mail, UPN, or ID to exact Graph user identifiers.",
                ResolveUserArgs,
                self._handlers.resolve_user,
                domain=self.metadata.name,
                tags=("user", "identity", "lookup", "resolver"),
            ),
            _tool(
                "resolve_group",
                "Resolve a group name, mail nickname, mail, or ID to exact Graph group identifiers.",
                ResolveGroupArgs,
                self._handlers.resolve_group,
                domain=self.metadata.name,
                tags=("group", "identity", "lookup", "resolver"),
            ),
            _tool(
                "list_users",
                "List directory users.",
                ListUsersArgs,
                self._handlers.list_users,
                domain=self.metadata.name,
                tags=("users", "directory", "read"),
            ),
            _tool(
                "get_user",
                "Get a user by object ID or UPN.",
                GetUserArgs,
                self._handlers.get_user,
                domain=self.metadata.name,
                tags=("user", "directory", "read"),
            ),
            _tool(
                "search_user",
                "Search users by display name, mail, or UPN.",
                SearchUserArgs,
                self._handlers.search_user,
                domain=self.metadata.name,
                tags=("user", "search", "directory"),
            ),
            _tool(
                "update_user",
                "Update user properties.",
                UpdateUserArgs,
                self._handlers.update_user,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("user", "update", "mutation"),
            ),
            _tool(
                "delete_user",
                "Delete a user.",
                DeleteUserArgs,
                self._handlers.delete_user,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("user", "delete", "mutation"),
            ),
            _tool(
                "revoke_user_sessions",
                "Revoke all sign-in sessions for a user.",
                RevokeUserSessionsArgs,
                self._handlers.revoke_user_sessions,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("user", "sessions", "revoke", "mutation"),
            ),
            _tool(
                "list_groups",
                "List Microsoft 365 groups.",
                ListGroupsArgs,
                self._handlers.list_groups,
                domain=self.metadata.name,
                tags=("groups", "directory", "read"),
            ),
            _tool(
                "get_group",
                "Get a group by ID.",
                GetGroupArgs,
                self._handlers.get_group,
                domain=self.metadata.name,
                tags=("group", "directory", "read"),
            ),
            _tool(
                "list_group_members",
                "List members of a group.",
                ListGroupMembersArgs,
                self._handlers.list_group_members,
                domain=self.metadata.name,
                tags=("group", "members", "read"),
            ),
            _tool(
                "add_group_member",
                "Add a directory object to a group.",
                AddGroupMemberArgs,
                self._handlers.add_group_member,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("group", "member", "add", "mutation"),
            ),
            _tool(
                "remove_group_member",
                "Remove a directory object from a group.",
                RemoveGroupMemberArgs,
                self._handlers.remove_group_member,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("group", "member", "remove", "mutation"),
            ),
            _tool(
                "list_service_principals",
                "List Entra service principals.",
                ListServicePrincipalsArgs,
                self._handlers.list_service_principals,
                domain=self.metadata.name,
                tags=("apps", "service principals", "identity", "read"),
            ),
            _tool(
                "list_oauth_permission_grants",
                "List OAuth permission grants.",
                ListOAuthPermissionGrantsArgs,
                self._handlers.list_oauth_permission_grants,
                domain=self.metadata.name,
                tags=("oauth", "permission", "grant", "consent", "read"),
            ),
            _tool(
                "delete_oauth_permission_grant",
                "Delete an OAuth permission grant.",
                DeleteOAuthPermissionGrantArgs,
                self._handlers.delete_oauth_permission_grant,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("oauth", "permission", "grant", "delete", "mutation"),
            ),
        ]


class SecurityDomain(GraphDomain):
    metadata = DomainMetadata(
        name="security",
        display_name="Security",
        description="Microsoft Graph security alerts, incidents, and security investigation data.",
        required_permissions=(
            "SecurityAlert.Read.All",
            "SecurityAlert.ReadWrite.All",
            "SecurityIncident.Read.All",
        ),
        tags=("security", "defender", "alerts", "incidents", "risk"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_security_alerts",
                "List Microsoft Graph security alerts.",
                SecurityListArgs,
                self._handlers.list_security_alerts,
                domain=self.metadata.name,
                tags=("security", "alerts", "defender", "severity"),
            ),
            _tool(
                "get_security_alert",
                "Get a single Microsoft Graph security alert by ID.",
                GetSecurityAlertArgs,
                self._handlers.get_security_alert,
                domain=self.metadata.name,
                tags=("security", "alert", "defender", "investigation"),
            ),
            _tool(
                "update_security_alert",
                "Triage a security alert (status, assignee, classification, determination).",
                UpdateSecurityAlertArgs,
                self._handlers.update_security_alert,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("security", "alert", "triage", "mutation"),
            ),
            _tool(
                "list_security_incidents",
                "List Microsoft Graph security incidents.",
                SecurityListArgs,
                self._handlers.list_security_incidents,
                domain=self.metadata.name,
                tags=("security", "incidents", "defender", "investigation"),
            ),
            _tool(
                "get_security_incident",
                "Get a single Microsoft Graph security incident by ID.",
                GetSecurityIncidentArgs,
                self._handlers.get_security_incident,
                domain=self.metadata.name,
                tags=("security", "incident", "defender", "investigation"),
            ),
        ]


class AuditActivityDomain(GraphDomain):
    metadata = DomainMetadata(
        name="audit_activity",
        display_name="Audit and Activity",
        description="Sign-in logs, directory audit events, and tenant activity investigation.",
        required_permissions=("AuditLog.Read.All", "Directory.Read.All"),
        tags=("audit", "activity", "logs", "sign in", "signin", "directory audit"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_sign_in_logs",
                "List Entra sign-in logs.",
                LogQueryArgs,
                self._handlers.list_sign_in_logs,
                domain=self.metadata.name,
                tags=("audit", "sign in", "signin", "failed login", "activity"),
            ),
            _tool(
                "list_directory_audits",
                "List directory audit events.",
                LogQueryArgs,
                self._handlers.list_directory_audits,
                domain=self.metadata.name,
                tags=("audit", "directory", "activity", "changes"),
            ),
        ]


class DirectoryDeviceDomain(GraphDomain):
    metadata = DomainMetadata(
        name="devices",
        display_name="Directory Devices",
        description=(
            "Microsoft Entra directory device objects (registered and joined devices). "
            "This is directory inventory only; it does not include Intune managed-device "
            "or device-compliance data, which live under a separate Graph surface."
        ),
        required_permissions=("Device.Read.All", "Directory.Read.All"),
        tags=("devices", "endpoint", "entra", "directory", "registered", "joined"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_devices",
                "List Microsoft Entra directory devices.",
                ListDevicesArgs,
                self._handlers.list_devices,
                domain=self.metadata.name,
                tags=("devices", "endpoint", "directory", "read"),
            ),
            _tool(
                "get_device",
                "Get a Microsoft Entra directory device by object ID.",
                GetDeviceArgs,
                self._handlers.get_device,
                domain=self.metadata.name,
                tags=("device", "directory", "read"),
            ),
        ]


class CatalogOperationDomain(GraphDomain):
    metadata = DomainMetadata(
        name="catalog_operations",
        display_name="Catalog Operations",
        description="Advanced escape hatch for executing cataloged Microsoft Graph operations by name.",
        tags=("catalog", "advanced", "generic", "graph operation"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "graph_operation",
                "Execute a cataloged Microsoft Graph operation by name.",
                GenericGraphOperationArgs,
                self._handlers.graph_operation,
                read_only=False,
                domain=self.metadata.name,
                safety="catalog_controlled",
                tags=("catalog", "advanced", "generic"),
            ),
        ]


class GraphToolFactory:
    def __init__(self, client: GraphClient, catalog: GraphOperationCatalog) -> None:
        self._client = client
        self._catalog = catalog

    def build_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        for domain in [
            IdentityAccessDomain(self),
            SecurityDomain(self),
            AuditActivityDomain(self),
            DirectoryDeviceDomain(self),
            CatalogOperationDomain(self),
        ]:
            registry.register_domain(domain)
        return registry

    async def resolve_user(self, args: ResolveUserArgs) -> Any:
        if _looks_like_object_id(args.query) or "@" in args.query:
            payload = await self._client.request("GET", f"/users/{args.query}")
            if isinstance(payload, dict) and "error" not in payload:
                return payload

        escaped = _escape_odata_string(args.query)
        filter_expr = (
            f"displayName eq '{escaped}' or userPrincipalName eq '{escaped}' or mail eq '{escaped}'"
        )
        payload = await self._client.request(
            "GET",
            "/users",
            params={
                "$filter": filter_expr,
                "$top": 5,
                "$select": "id,displayName,userPrincipalName,mail",
            },
        )
        return _single_match_or_result(
            payload, allow_ambiguous=args.allow_ambiguous, entity_name="user"
        )

    async def resolve_group(self, args: ResolveGroupArgs) -> Any:
        if _looks_like_object_id(args.query):
            payload = await self._client.request("GET", f"/groups/{args.query}")
            if isinstance(payload, dict) and "error" not in payload:
                return payload

        escaped = _escape_odata_string(args.query)
        filter_expr = (
            f"displayName eq '{escaped}' or mailNickname eq '{escaped}' or mail eq '{escaped}'"
        )
        payload = await self._client.request(
            "GET",
            "/groups",
            params={
                "$filter": filter_expr,
                "$top": 5,
                "$select": "id,displayName,mail,mailNickname",
            },
        )
        return _single_match_or_result(
            payload, allow_ambiguous=args.allow_ambiguous, entity_name="group"
        )

    async def list_users(self, args: ListUsersArgs) -> Any:
        return await self._client.request_collection(
            "/users",
            params=_odata_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_user(self, args: GetUserArgs) -> Any:
        return await self._client.request(
            "GET", f"/users/{args.user_id}", params=_select_params(args.select_fields)
        )

    async def search_user(self, args: SearchUserArgs) -> Any:
        escaped = _escape_odata_string(args.query)
        filter_expression = (
            f"startswith(displayName,'{escaped}') "
            f"or startswith(userPrincipalName,'{escaped}') "
            f"or startswith(mail,'{escaped}')"
        )
        return await self._client.request(
            "GET",
            "/users",
            params={"$filter": filter_expression, "$top": args.top},
            advanced_query=True,
        )

    async def update_user(self, args: UpdateUserArgs) -> Any:
        return await self._client.request(
            "PATCH", f"/users/{args.user_id}", json_data=args.update_data
        )

    async def delete_user(self, args: DeleteUserArgs) -> Any:
        return await self._client.request("DELETE", f"/users/{args.user_id}")

    async def revoke_user_sessions(self, args: RevokeUserSessionsArgs) -> Any:
        return await self._client.request("POST", f"/users/{args.user_id}/revokeSignInSessions")

    async def list_groups(self, args: ListGroupsArgs) -> Any:
        return await self._client.request_collection(
            "/groups",
            params=_odata_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_group(self, args: GetGroupArgs) -> Any:
        return await self._client.request("GET", f"/groups/{args.group_id}")

    async def list_group_members(self, args: ListGroupMembersArgs) -> Any:
        params = _select_params(args.select_fields)
        if args.top:
            params["$top"] = args.top
        return await self._client.request_collection(
            f"/groups/{args.group_id}/members",
            params=params,
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def add_group_member(self, args: AddGroupMemberArgs) -> Any:
        body = {"@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{args.member_id}"}
        return await self._client.request(
            "POST", f"/groups/{args.group_id}/members/$ref", json_data=body
        )

    async def remove_group_member(self, args: RemoveGroupMemberArgs) -> Any:
        return await self._client.request(
            "DELETE", f"/groups/{args.group_id}/members/{args.member_id}/$ref"
        )

    async def list_devices(self, args: ListDevicesArgs) -> Any:
        return await self._client.request_collection(
            "/devices",
            params=_odata_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_device(self, args: GetDeviceArgs) -> Any:
        return await self._client.request(
            "GET", f"/devices/{args.device_id}", params=_select_params(args.select_fields)
        )

    async def list_sign_in_logs(self, args: LogQueryArgs) -> Any:
        return await self._client.request_collection(
            "/auditLogs/signIns",
            params=_log_query_params(args),
            api_version="beta",
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_directory_audits(self, args: LogQueryArgs) -> Any:
        return await self._client.request_collection(
            "/auditLogs/directoryAudits",
            params=_log_query_params(args),
            api_version="beta",
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_security_alerts(self, args: SecurityListArgs) -> Any:
        params = _security_query_params(args)
        if args.count is not None:
            params["$count"] = str(args.count).lower()
        return await self._client.request_collection(
            "/security/alerts_v2",
            params=params,
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_security_alert(self, args: GetSecurityAlertArgs) -> Any:
        return await self._client.request("GET", f"/security/alerts_v2/{args.alert_id}")

    async def update_security_alert(self, args: UpdateSecurityAlertArgs) -> Any:
        body: dict[str, Any] = {}
        if args.status is not None:
            body["status"] = args.status
        if args.assigned_to is not None:
            body["assignedTo"] = args.assigned_to
        if args.classification is not None:
            body["classification"] = args.classification
        if args.determination is not None:
            body["determination"] = args.determination
        if not body:
            return ToolResult.failure(
                "validation_error",
                "Provide at least one field to update (status, assigned_to, classification, "
                "or determination).",
            )
        return await self._client.request(
            "PATCH", f"/security/alerts_v2/{args.alert_id}", json_data=body
        )

    async def list_security_incidents(self, args: SecurityListArgs) -> Any:
        return await self._client.request_collection(
            "/security/incidents",
            params=_security_query_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_security_incident(self, args: GetSecurityIncidentArgs) -> Any:
        return await self._client.request("GET", f"/security/incidents/{args.incident_id}")

    async def list_service_principals(self, args: ListServicePrincipalsArgs) -> Any:
        filters: list[str] = []
        if args.app_id:
            filters.append(f"appId eq '{_escape_odata_string(args.app_id)}'")
        if args.display_name:
            filters.append(f"displayName eq '{_escape_odata_string(args.display_name)}'")
        params = _select_params(args.select_fields)
        if filters:
            params["$filter"] = " and ".join(filters)
        if args.top:
            params["$top"] = args.top
        return await self._client.request_collection(
            "/servicePrincipals",
            params=params,
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_oauth_permission_grants(self, args: ListOAuthPermissionGrantsArgs) -> Any:
        filters: list[str] = []
        if args.client_id:
            filters.append(f"clientId eq '{_escape_odata_string(args.client_id)}'")
        if args.consent_type:
            filters.append(f"consentType eq '{_escape_odata_string(args.consent_type)}'")
        params: dict[str, Any] = {}
        if filters:
            params["$filter"] = " and ".join(filters)
        if args.top:
            params["$top"] = args.top
        return await self._client.request_collection(
            "/oauth2PermissionGrants",
            params=params,
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def delete_oauth_permission_grant(self, args: DeleteOAuthPermissionGrantArgs) -> Any:
        return await self._client.request("DELETE", f"/oauth2PermissionGrants/{args.grant_id}")

    async def graph_operation(self, args: GenericGraphOperationArgs) -> Any:
        operation = self._catalog.get(args.operation_name)
        if operation is None:
            return ToolResult.failure(
                "validation_error",
                f"Unknown operation '{args.operation_name}'.",
                details={"operation_name": args.operation_name},
            )
        if not operation.read_only and not args.confirmed:
            return ToolResult.failure(
                "confirmation_required",
                (
                    f"Operation '{args.operation_name}' mutates Microsoft Graph data "
                    "and requires confirmed=true before execution."
                ),
                details={"operation_name": args.operation_name},
            )
        try:
            endpoint = operation.endpoint.format(**args.path_params)
        except KeyError as exc:
            return ToolResult.failure(
                "validation_error",
                f"Missing path parameter: {exc.args[0]}.",
                details={"missing_param": exc.args[0]},
            )
        return await self._client.request(
            operation.method,
            endpoint,
            json_data=args.body,
            params=args.query_params,
            api_version=args.api_version or operation.api_version,
        )


def _tool(
    name: str,
    description: str,
    args_model: type[BaseModel],
    handler: Any,
    *,
    read_only: bool = True,
    requires_confirmation: bool = False,
    domain: str,
    safety: str = "read_only",
    required_permissions: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=description,
        args_model=args_model,
        handler=handler,
        read_only=read_only,
        requires_confirmation=requires_confirmation,
        domain=domain,
        safety=safety,
        required_permissions=required_permissions,
        tags=tags,
    )


def _select_params(select_fields: list[str] | None) -> dict[str, Any]:
    return {"$select": ",".join(select_fields)} if select_fields else {}


def _odata_params(args: Any) -> dict[str, Any]:
    params = _select_params(getattr(args, "select_fields", None))
    if getattr(args, "filter_expression", None):
        params["$filter"] = args.filter_expression
    if getattr(args, "top", None):
        params["$top"] = args.top
    return params


def _filter_top_params(args: Any) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if getattr(args, "filter_expression", None):
        params["$filter"] = args.filter_expression
    if getattr(args, "top", None):
        params["$top"] = args.top
    return params


def _log_query_params(args: LogQueryArgs) -> dict[str, Any]:
    filters: list[str] = []
    if args.user_principal_name:
        filters.append(f"userPrincipalName eq '{_escape_odata_string(args.user_principal_name)}'")
    if args.created_after:
        filters.append(f"createdDateTime ge {_format_datetime(args.created_after)}")
    if args.status_error_code is not None:
        filters.append(f"status/errorCode eq {args.status_error_code}")
    if args.filter_expression:
        filters.append(f"({args.filter_expression})")
    params: dict[str, Any] = {}
    if filters:
        params["$filter"] = " and ".join(filters)
    if args.top:
        params["$top"] = args.top
    return params


def _security_query_params(args: SecurityListArgs) -> dict[str, Any]:
    filters: list[str] = []
    if args.severity:
        filters.append(f"severity eq '{args.severity}'")
    if args.status:
        filters.append(f"status eq '{args.status}'")
    if args.assigned_to:
        filters.append(f"assignedTo eq '{_escape_odata_string(args.assigned_to)}'")
    if args.created_after:
        filters.append(f"createdDateTime ge {_format_datetime(args.created_after)}")
    if args.filter_expression:
        filters.append(f"({args.filter_expression})")
    params: dict[str, Any] = {}
    if filters:
        params["$filter"] = " and ".join(filters)
    if args.top:
        params["$top"] = args.top
    return params


def _single_match_or_result(payload: Any, *, allow_ambiguous: bool, entity_name: str) -> Any:
    records = payload.get("value") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        return payload
    if len(records) == 1 or allow_ambiguous:
        return payload
    if len(records) == 0:
        return ToolResult.failure("not_found", f"No matching {entity_name} was found.")
    return ToolResult.failure(
        "ambiguous_identity",
        f"Multiple matching {entity_name}s were found. Use a unique ID, UPN, or set allow_ambiguous=true.",
        details={"matches": records},
    )


def _escape_odata_string(value: str) -> str:
    return value.replace("'", "''")


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


_OBJECT_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def _looks_like_object_id(value: str) -> bool:
    return bool(_OBJECT_ID_RE.match(value.strip()))
