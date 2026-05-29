"""Microsoft Graph tool args models, domain definitions, and handler implementations."""

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
    """Shared paging controls mixed into list-style tool inputs."""

    top: int | None = Field(default=25, ge=1, le=999)
    all_pages: bool = Field(
        default=False, description="Fetch additional pages when Graph returns @odata.nextLink."
    )
    max_pages: int = Field(default=1, ge=1, le=10)


class ResolveUserArgs(BaseModel):
    """Input for resolving a free-form user reference to a Graph user."""

    query: str = Field(description="User display name, mail, UPN, or object ID.")
    allow_ambiguous: bool = Field(default=False)


class ResolveGroupArgs(BaseModel):
    """Input for resolving a free-form group reference to a Graph group."""

    query: str = Field(description="Group display name, mail nickname, mail, or object ID.")
    allow_ambiguous: bool = Field(default=False)


class ListUsersArgs(PaginationArgs):
    """Input for listing directory users with optional field selection and filter."""

    select_fields: list[str] | None = Field(default=None)
    filter_expression: str | None = Field(default=None)


class GetUserArgs(BaseModel):
    """Input for fetching a single user by ID or UPN."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    select_fields: list[str] | None = None


class SearchUserArgs(BaseModel):
    """Input for prefix-searching users by name, mail, or UPN."""

    query: str = Field(description="Display name, mail, or userPrincipalName to search for.")
    top: int = Field(default=5, ge=1, le=25)


class UpdateUserArgs(ConfirmableArgs):
    """Confirmable input for patching properties on a user."""

    user_id: str
    update_data: dict[str, Any]


class DeleteUserArgs(ConfirmableArgs):
    """Confirmable input for deleting a user."""

    user_id: str


class RevokeUserSessionsArgs(ConfirmableArgs):
    """Confirmable input for revoking all sign-in sessions for a user."""

    user_id: str


class ListGroupsArgs(PaginationArgs):
    """Input for listing groups with optional field selection and filter."""

    select_fields: list[str] | None = None
    filter_expression: str | None = None


class GetGroupArgs(BaseModel):
    """Input for fetching a single group by ID."""

    group_id: str


class ListGroupMembersArgs(PaginationArgs):
    """Input for listing the members of a group."""

    group_id: str
    select_fields: list[str] | None = None
    top: int | None = Field(default=50, ge=1, le=999)


class AddGroupMemberArgs(ConfirmableArgs):
    """Confirmable input for adding a directory object to a group."""

    group_id: str
    member_id: str


class RemoveGroupMemberArgs(ConfirmableArgs):
    """Confirmable input for removing a directory object from a group."""

    group_id: str
    member_id: str


class ListDevicesArgs(PaginationArgs):
    """Input for listing directory devices with optional field selection and filter."""

    select_fields: list[str] | None = None
    filter_expression: str | None = None


class GetDeviceArgs(BaseModel):
    """Input for fetching a single directory device by object ID."""

    device_id: str = Field(description="Directory device object ID.")
    select_fields: list[str] | None = None


class LogQueryArgs(PaginationArgs):
    """Input for querying sign-in or directory-audit logs."""

    user_principal_name: str | None = None
    created_after: datetime | None = None
    status_error_code: int | None = None
    filter_expression: str | None = None


SecuritySeverity = Literal["unknown", "informational", "low", "medium", "high"]
SecurityStatus = Literal["unknown", "new", "inProgress", "resolved"]


class SecurityListArgs(PaginationArgs):
    """Input for filtering security alert or incident collections."""

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
    """Input for fetching a single security alert by ID."""

    alert_id: str = Field(description="Microsoft Graph security alert (alerts_v2) ID.")


class GetSecurityIncidentArgs(BaseModel):
    """Input for fetching a single security incident by ID."""

    incident_id: str = Field(description="Microsoft Graph security incident ID.")


class UpdateSecurityAlertArgs(ConfirmableArgs):
    """Confirmable input for triaging a security alert."""

    alert_id: str
    status: SecurityStatus | None = None
    assigned_to: str | None = None
    classification: AlertClassification | None = None
    determination: str | None = None


class ListServicePrincipalsArgs(PaginationArgs):
    """Input for listing service principals, optionally filtered by app ID or name."""

    app_id: str | None = None
    display_name: str | None = None
    select_fields: list[str] | None = None


class ListOAuthPermissionGrantsArgs(PaginationArgs):
    """Input for listing OAuth permission grants, optionally filtered."""

    client_id: str | None = None
    consent_type: str | None = None


class DeleteOAuthPermissionGrantArgs(ConfirmableArgs):
    """Confirmable input for deleting an OAuth permission grant."""

    grant_id: str


class GenericGraphOperationArgs(ConfirmableArgs):
    """Confirmable input for invoking a cataloged Graph operation by name."""

    operation_name: str
    path_params: dict[str, Any] = Field(default_factory=dict)
    body: dict[str, Any] | None = None
    query_params: dict[str, Any] | None = None
    api_version: str | None = None


# --- Identity & access governance ------------------------------------------

ConditionalAccessState = Literal["enabled", "disabled", "enabledForReportingButNotEnforced"]


class ListRoleAssignmentsArgs(PaginationArgs):
    principal_id: str | None = Field(
        default=None, description="Filter by principal (user/group/SP) object ID."
    )
    role_definition_id: str | None = Field(
        default=None, description="Filter by role definition ID."
    )


class AssignDirectoryRoleArgs(ConfirmableArgs):
    principal_id: str = Field(description="Object ID of the user, group, or service principal.")
    role_definition_id: str = Field(
        description="Directory role definition (or template) ID to grant."
    )
    directory_scope_id: str = Field(
        default="/", description="Assignment scope; '/' is tenant-wide."
    )


class RemoveRoleAssignmentArgs(ConfirmableArgs):
    assignment_id: str = Field(description="unifiedRoleAssignment ID to delete.")


class GetConditionalAccessPolicyArgs(BaseModel):
    policy_id: str = Field(description="Conditional Access policy object ID.")


class SetConditionalAccessPolicyStateArgs(ConfirmableArgs):
    policy_id: str = Field(description="Conditional Access policy object ID.")
    state: ConditionalAccessState = Field(description="Target enforcement state.")


class GetUserLicenseDetailsArgs(BaseModel):
    user_id: str = Field(description="User object ID or userPrincipalName.")


class AssignUserLicenseArgs(ConfirmableArgs):
    user_id: str = Field(description="User object ID or userPrincipalName.")
    add_sku_ids: list[str] = Field(default_factory=list, description="SKU IDs to assign.")
    remove_sku_ids: list[str] = Field(default_factory=list, description="SKU IDs to remove.")
    disabled_plans: list[str] | None = Field(
        default=None, description="Service plan IDs to disable on the added SKUs."
    )


class ListApplicationsArgs(PaginationArgs):
    display_name: str | None = None
    app_id: str | None = None
    select_fields: list[str] | None = None


class GetApplicationArgs(BaseModel):
    application_id: str = Field(description="Application (app registration) object ID.")


class UpdateApplicationArgs(ConfirmableArgs):
    application_id: str
    update_data: dict[str, Any]


class DeleteApplicationArgs(ConfirmableArgs):
    application_id: str


# --- Privileged Identity Management (PIM) ----------------------------------


class CreateRoleEligibilityRequestArgs(ConfirmableArgs):
    principal_id: str = Field(description="Object ID of the user, group, or service principal.")
    role_definition_id: str = Field(description="Directory role definition ID to make eligible.")
    justification: str = Field(description="Business justification recorded with the request.")
    directory_scope_id: str = Field(
        default="/", description="Assignment scope; '/' is tenant-wide."
    )


class ActivateEligibleRoleArgs(ConfirmableArgs):
    principal_id: str = Field(description="Object ID of the principal activating the role.")
    role_definition_id: str = Field(description="Directory role definition ID to activate.")
    justification: str = Field(description="Business justification recorded with the activation.")
    directory_scope_id: str = Field(
        default="/", description="Activation scope; '/' is tenant-wide."
    )


# --- Access reviews & entitlement management --------------------------------


class StopAccessReviewInstanceArgs(ConfirmableArgs):
    definition_id: str = Field(description="Access review schedule definition ID.")
    instance_id: str = Field(description="Access review instance ID to stop.")


# --- Authentication methods -------------------------------------------------


class ListUserAuthenticationMethodsArgs(PaginationArgs):
    user_id: str = Field(description="User object ID or userPrincipalName.")


class DeleteUserAuthenticationMethodArgs(ConfirmableArgs):
    user_id: str = Field(description="User object ID or userPrincipalName.")
    method_id: str = Field(description="Microsoft Authenticator method ID to delete.")


class ResetPasswordArgs(ConfirmableArgs):
    user_id: str = Field(description="User object ID or userPrincipalName.")
    method_id: str = Field(description="Password authentication method ID.")
    new_password: str | None = Field(
        default=None, description="Optional new password; omit to auto-generate."
    )


# --- Identity protection ----------------------------------------------------


class DismissRiskyUsersArgs(ConfirmableArgs):
    user_ids: list[str] = Field(description="Object IDs of risky users to dismiss.")


class ConfirmCompromisedUsersArgs(ConfirmableArgs):
    user_ids: list[str] = Field(description="Object IDs of users to confirm as compromised.")


class IdentityAccessDomain(GraphDomain):
    """Graph domain exposing user, group, app, and OAuth identity tools."""

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
        """Store the handler facade that backs each tool's execution."""
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        """Return the identity and access tool definitions for this domain."""
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
    """Graph domain exposing security alert and incident tools."""

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
        """Store the handler facade that backs each tool's execution."""
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        """Return the security alert and incident tool definitions for this domain."""
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
    """Graph domain exposing sign-in log and directory audit tools."""

    metadata = DomainMetadata(
        name="audit_activity",
        display_name="Audit and Activity",
        description="Sign-in logs, directory audit events, and tenant activity investigation.",
        required_permissions=("AuditLog.Read.All", "Directory.Read.All"),
        tags=("audit", "activity", "logs", "sign in", "signin", "directory audit"),
    )

    def __init__(self, handlers: Any) -> None:
        """Store the handler facade that backs each tool's execution."""
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        """Return the audit log and sign-in activity tool definitions for this domain."""
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
    """Graph domain exposing directory device inventory tools."""

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
        """Store the handler facade that backs each tool's execution."""
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        """Return the directory device tool definitions for this domain."""
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
    """Graph domain exposing the generic cataloged-operation escape hatch."""

    metadata = DomainMetadata(
        name="catalog_operations",
        display_name="Catalog Operations",
        description="Advanced escape hatch for executing cataloged Microsoft Graph operations by name.",
        tags=("catalog", "advanced", "generic", "graph operation"),
    )

    def __init__(self, handlers: Any) -> None:
        """Store the handler facade that backs each tool's execution."""
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        """Return the generic cataloged-operation tool definition for this domain."""
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


class RoleManagementDomain(GraphDomain):
    metadata = DomainMetadata(
        name="role_management",
        display_name="Role Management (RBAC)",
        description=(
            "Microsoft Entra directory roles and RBAC: list roles and definitions, inspect "
            "role assignments, and grant or remove directory role assignments."
        ),
        required_permissions=(
            "RoleManagement.Read.Directory",
            "RoleManagement.ReadWrite.Directory",
        ),
        tags=("rbac", "roles", "directory roles", "entra", "privilege", "admin", "assignment"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_directory_roles",
                "List activated Entra directory roles.",
                PaginationArgs,
                self._handlers.list_directory_roles,
                domain=self.metadata.name,
                tags=("roles", "rbac", "read"),
            ),
            _tool(
                "list_role_definitions",
                "List Entra role definitions (built-in and custom).",
                PaginationArgs,
                self._handlers.list_role_definitions,
                domain=self.metadata.name,
                tags=("roles", "definitions", "rbac", "read"),
            ),
            _tool(
                "list_role_assignments",
                "List directory role assignments, optionally filtered by principal or role.",
                ListRoleAssignmentsArgs,
                self._handlers.list_role_assignments,
                domain=self.metadata.name,
                tags=("roles", "assignments", "rbac", "read"),
            ),
            _tool(
                "assign_directory_role",
                "Assign a directory role to a principal.",
                AssignDirectoryRoleArgs,
                self._handlers.assign_directory_role,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("roles", "assign", "rbac", "mutation"),
            ),
            _tool(
                "remove_role_assignment",
                "Remove a directory role assignment.",
                RemoveRoleAssignmentArgs,
                self._handlers.remove_role_assignment,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("roles", "remove", "rbac", "mutation"),
            ),
        ]


class ConditionalAccessDomain(GraphDomain):
    metadata = DomainMetadata(
        name="conditional_access",
        display_name="Conditional Access",
        description=(
            "Microsoft Entra Conditional Access policies: list and inspect policies and change "
            "a policy's enforcement state (enabled, disabled, report-only)."
        ),
        required_permissions=(
            "Policy.Read.All",
            "Policy.ReadWrite.ConditionalAccess",
        ),
        tags=("conditional access", "ca", "policy", "mfa", "entra", "zero trust", "access"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_conditional_access_policies",
                "List Conditional Access policies.",
                PaginationArgs,
                self._handlers.list_conditional_access_policies,
                domain=self.metadata.name,
                tags=("conditional access", "policy", "read"),
            ),
            _tool(
                "get_conditional_access_policy",
                "Get a Conditional Access policy by ID.",
                GetConditionalAccessPolicyArgs,
                self._handlers.get_conditional_access_policy,
                domain=self.metadata.name,
                tags=("conditional access", "policy", "read"),
            ),
            _tool(
                "set_conditional_access_policy_state",
                "Change a Conditional Access policy's enforcement state.",
                SetConditionalAccessPolicyStateArgs,
                self._handlers.set_conditional_access_policy_state,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("conditional access", "policy", "state", "mutation"),
            ),
        ]


class LicenseManagementDomain(GraphDomain):
    metadata = DomainMetadata(
        name="license_management",
        display_name="License Management",
        description=(
            "Microsoft 365 license inventory and assignment: list subscribed SKUs, read a "
            "user's license details, and assign or remove user licenses."
        ),
        required_permissions=(
            "Organization.Read.All",
            "Directory.Read.All",
            "User.ReadWrite.All",
        ),
        tags=("licenses", "skus", "subscriptions", "m365", "assignment", "entitlement"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_subscribed_skus",
                "List the tenant's subscribed Microsoft 365 SKUs.",
                PaginationArgs,
                self._handlers.list_subscribed_skus,
                domain=self.metadata.name,
                tags=("licenses", "skus", "read"),
            ),
            _tool(
                "get_user_license_details",
                "List the licenses assigned to a user.",
                GetUserLicenseDetailsArgs,
                self._handlers.get_user_license_details,
                domain=self.metadata.name,
                tags=("licenses", "user", "read"),
            ),
            _tool(
                "assign_user_license",
                "Add or remove licenses for a user.",
                AssignUserLicenseArgs,
                self._handlers.assign_user_license,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("licenses", "assign", "mutation"),
            ),
        ]


class ApplicationsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="applications",
        display_name="Applications",
        description=(
            "Microsoft Entra application registrations: list and inspect applications and "
            "update or delete an app registration."
        ),
        required_permissions=(
            "Application.Read.All",
            "Application.ReadWrite.All",
        ),
        tags=("applications", "app registrations", "entra", "apps", "client"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_applications",
                "List Entra application registrations.",
                ListApplicationsArgs,
                self._handlers.list_applications,
                domain=self.metadata.name,
                tags=("applications", "apps", "read"),
            ),
            _tool(
                "get_application",
                "Get an application registration by object ID.",
                GetApplicationArgs,
                self._handlers.get_application,
                domain=self.metadata.name,
                tags=("application", "app", "read"),
            ),
            _tool(
                "update_application",
                "Update properties on an application registration.",
                UpdateApplicationArgs,
                self._handlers.update_application,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("application", "update", "mutation"),
            ),
            _tool(
                "delete_application",
                "Delete an application registration.",
                DeleteApplicationArgs,
                self._handlers.delete_application,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("application", "delete", "mutation"),
            ),
        ]


class PrivilegedIdentityDomain(GraphDomain):
    metadata = DomainMetadata(
        name="privileged_identity",
        display_name="Privileged Identity Management",
        description=(
            "Microsoft Entra Privileged Identity Management (PIM): inspect eligible and active "
            "role assignment schedules and request eligibility or just-in-time activation of "
            "directory roles."
        ),
        required_permissions=(
            "RoleManagement.Read.Directory",
            "RoleManagement.ReadWrite.Directory",
        ),
        tags=("pim", "privileged", "roles", "eligibility", "activation", "jit", "entra"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_eligible_role_assignments",
                "List PIM eligible role assignment schedule instances.",
                PaginationArgs,
                self._handlers.list_eligible_role_assignments,
                domain=self.metadata.name,
                tags=("pim", "eligible", "roles", "read"),
            ),
            _tool(
                "list_active_role_assignment_schedules",
                "List PIM active role assignment schedule instances.",
                PaginationArgs,
                self._handlers.list_active_role_assignment_schedules,
                domain=self.metadata.name,
                tags=("pim", "active", "roles", "read"),
            ),
            _tool(
                "create_role_eligibility_request",
                "Request that a principal become eligible for a directory role via PIM.",
                CreateRoleEligibilityRequestArgs,
                self._handlers.create_role_eligibility_request,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("pim", "eligibility", "request", "mutation"),
            ),
            _tool(
                "activate_eligible_role",
                "Activate an eligible directory role for a principal via PIM.",
                ActivateEligibleRoleArgs,
                self._handlers.activate_eligible_role,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("pim", "activation", "request", "mutation"),
            ),
        ]


class AccessReviewsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="access_reviews",
        display_name="Access Reviews & Entitlement",
        description=(
            "Microsoft Entra identity governance: list access review definitions and "
            "entitlement-management access packages, and stop a running access review instance."
        ),
        required_permissions=(
            "AccessReview.Read.All",
            "AccessReview.ReadWrite.All",
            "EntitlementManagement.Read.All",
        ),
        tags=(
            "access reviews",
            "entitlement",
            "governance",
            "access packages",
            "certification",
            "entra",
        ),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_access_review_definitions",
                "List access review schedule definitions.",
                PaginationArgs,
                self._handlers.list_access_review_definitions,
                domain=self.metadata.name,
                tags=("access reviews", "definitions", "governance", "read"),
            ),
            _tool(
                "list_access_packages",
                "List entitlement-management access packages.",
                PaginationArgs,
                self._handlers.list_access_packages,
                domain=self.metadata.name,
                tags=("entitlement", "access packages", "governance", "read"),
            ),
            _tool(
                "stop_access_review_instance",
                "Stop a running access review instance.",
                StopAccessReviewInstanceArgs,
                self._handlers.stop_access_review_instance,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("access reviews", "stop", "governance", "mutation"),
            ),
        ]


class AuthenticationMethodsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="authentication_methods",
        display_name="Authentication Methods",
        description=(
            "Microsoft Entra authentication methods: inspect a user's registered methods and "
            "perform credential mutations such as removing an authenticator method or resetting "
            "a password."
        ),
        required_permissions=(
            "UserAuthenticationMethod.Read.All",
            "UserAuthenticationMethod.ReadWrite.All",
        ),
        tags=("authentication", "mfa", "credentials", "password", "sspr", "entra"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_user_authentication_methods",
                "List a user's registered authentication methods.",
                ListUserAuthenticationMethodsArgs,
                self._handlers.list_user_authentication_methods,
                domain=self.metadata.name,
                tags=("authentication", "methods", "mfa", "read"),
            ),
            _tool(
                "delete_user_authentication_method",
                "Delete a user's Microsoft Authenticator authentication method.",
                DeleteUserAuthenticationMethodArgs,
                self._handlers.delete_user_authentication_method,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("authentication", "method", "delete", "mutation"),
            ),
            _tool(
                "reset_password",
                "Reset a user's password authentication method (SSPR-style).",
                ResetPasswordArgs,
                self._handlers.reset_password,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("authentication", "password", "reset", "sspr", "mutation"),
            ),
        ]


class IdentityProtectionDomain(GraphDomain):
    metadata = DomainMetadata(
        name="identity_protection",
        display_name="Identity Protection",
        description=(
            "Microsoft Entra Identity Protection: inspect risky users and risk detections and "
            "remediate risk by dismissing or confirming users as compromised."
        ),
        required_permissions=(
            "IdentityRiskyUser.Read.All",
            "IdentityRiskEvent.Read.All",
            "IdentityRiskyUser.ReadWrite.All",
        ),
        tags=("identity protection", "risk", "risky users", "detections", "remediation", "entra"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_risky_users",
                "List Identity Protection risky users.",
                PaginationArgs,
                self._handlers.list_risky_users,
                domain=self.metadata.name,
                tags=("identity protection", "risky users", "risk", "read"),
            ),
            _tool(
                "list_risk_detections",
                "List Identity Protection risk detections.",
                PaginationArgs,
                self._handlers.list_risk_detections,
                domain=self.metadata.name,
                tags=("identity protection", "risk detections", "risk", "read"),
            ),
            _tool(
                "dismiss_risky_users",
                "Dismiss the risk state for one or more risky users.",
                DismissRiskyUsersArgs,
                self._handlers.dismiss_risky_users,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("identity protection", "risky users", "dismiss", "mutation"),
            ),
            _tool(
                "confirm_compromised_users",
                "Confirm one or more users as compromised.",
                ConfirmCompromisedUsersArgs,
                self._handlers.confirm_compromised_users,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("identity protection", "risky users", "compromised", "mutation"),
            ),
        ]


class GraphToolFactory:
    """Builds the tool registry and implements every Graph tool handler."""

    def __init__(self, client: GraphClient, catalog: GraphOperationCatalog) -> None:
        """Store the Graph client and operation catalog used by all handlers."""
        self._client = client
        self._catalog = catalog

    def build_registry(self) -> ToolRegistry:
        """Construct and register every Graph domain into a fresh tool registry."""
        registry = ToolRegistry()
        for domain in [
            IdentityAccessDomain(self),
            SecurityDomain(self),
            AuditActivityDomain(self),
            DirectoryDeviceDomain(self),
            RoleManagementDomain(self),
            ConditionalAccessDomain(self),
            LicenseManagementDomain(self),
            ApplicationsDomain(self),
            PrivilegedIdentityDomain(self),
            AccessReviewsDomain(self),
            AuthenticationMethodsDomain(self),
            IdentityProtectionDomain(self),
            CatalogOperationDomain(self),
        ]:
            registry.register_domain(domain)
        return registry

    async def resolve_user(self, args: ResolveUserArgs) -> Any:
        """Resolve a user by ID/UPN fast-path or a filtered lookup, returning one match."""
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
        """Resolve a group by ID fast-path or a filtered lookup, returning one match."""
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
        """List directory users, applying OData select/filter/top and paging."""
        return await self._client.request_collection(
            "/users",
            params=_odata_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_user(self, args: GetUserArgs) -> Any:
        """Fetch a single user by object ID or UPN with optional field selection."""
        return await self._client.request(
            "GET", f"/users/{args.user_id}", params=_select_params(args.select_fields)
        )

    async def search_user(self, args: SearchUserArgs) -> Any:
        """Prefix-search users across display name, UPN, and mail via advanced query."""
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
        """Patch the supplied properties onto a user."""
        return await self._client.request(
            "PATCH", f"/users/{args.user_id}", json_data=args.update_data
        )

    async def delete_user(self, args: DeleteUserArgs) -> Any:
        """Delete a user by object ID or UPN."""
        return await self._client.request("DELETE", f"/users/{args.user_id}")

    async def revoke_user_sessions(self, args: RevokeUserSessionsArgs) -> Any:
        """Revoke all active sign-in sessions for a user to force reauthentication."""
        return await self._client.request("POST", f"/users/{args.user_id}/revokeSignInSessions")

    async def list_groups(self, args: ListGroupsArgs) -> Any:
        """List groups, applying OData select/filter/top and paging."""
        return await self._client.request_collection(
            "/groups",
            params=_odata_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_group(self, args: GetGroupArgs) -> Any:
        """Fetch a single group by object ID."""
        return await self._client.request("GET", f"/groups/{args.group_id}")

    async def list_group_members(self, args: ListGroupMembersArgs) -> Any:
        """List the members of a group with optional field selection and paging."""
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
        """Add a directory object to a group via its members $ref collection."""
        body = {"@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{args.member_id}"}
        return await self._client.request(
            "POST", f"/groups/{args.group_id}/members/$ref", json_data=body
        )

    async def remove_group_member(self, args: RemoveGroupMemberArgs) -> Any:
        """Remove a directory object from a group's membership."""
        return await self._client.request(
            "DELETE", f"/groups/{args.group_id}/members/{args.member_id}/$ref"
        )

    async def list_devices(self, args: ListDevicesArgs) -> Any:
        """List directory devices, applying OData select/filter/top and paging."""
        return await self._client.request_collection(
            "/devices",
            params=_odata_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_device(self, args: GetDeviceArgs) -> Any:
        """Fetch a single directory device by object ID with optional field selection."""
        return await self._client.request(
            "GET", f"/devices/{args.device_id}", params=_select_params(args.select_fields)
        )

    async def list_sign_in_logs(self, args: LogQueryArgs) -> Any:
        """List Entra sign-in logs from the beta endpoint, applying log filters and paging."""
        return await self._client.request_collection(
            "/auditLogs/signIns",
            params=_log_query_params(args),
            api_version="beta",
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_directory_audits(self, args: LogQueryArgs) -> Any:
        """List directory audit events from the beta endpoint, applying log filters and paging."""
        return await self._client.request_collection(
            "/auditLogs/directoryAudits",
            params=_log_query_params(args),
            api_version="beta",
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_security_alerts(self, args: SecurityListArgs) -> Any:
        """List alerts_v2 security alerts, applying security filters, optional $count, and paging."""
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
        """Fetch a single alerts_v2 security alert by ID."""
        return await self._client.request("GET", f"/security/alerts_v2/{args.alert_id}")

    async def update_security_alert(self, args: UpdateSecurityAlertArgs) -> Any:
        """Triage an alert, patching only supplied fields and rejecting empty updates."""
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
        """List security incidents, applying security filters and paging."""
        return await self._client.request_collection(
            "/security/incidents",
            params=_security_query_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_security_incident(self, args: GetSecurityIncidentArgs) -> Any:
        """Fetch a single security incident by ID."""
        return await self._client.request("GET", f"/security/incidents/{args.incident_id}")

    async def list_service_principals(self, args: ListServicePrincipalsArgs) -> Any:
        """List service principals, optionally filtered by app ID and/or display name."""
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
        """List OAuth permission grants, optionally filtered by client ID and/or consent type."""
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
        """Delete an OAuth permission grant by ID to revoke consented permissions."""
        return await self._client.request("DELETE", f"/oauth2PermissionGrants/{args.grant_id}")

    async def list_directory_roles(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/directoryRoles",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_role_definitions(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/roleManagement/directory/roleDefinitions",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_role_assignments(self, args: ListRoleAssignmentsArgs) -> Any:
        filters: list[str] = []
        if args.principal_id:
            filters.append(f"principalId eq '{_escape_odata_string(args.principal_id)}'")
        if args.role_definition_id:
            filters.append(f"roleDefinitionId eq '{_escape_odata_string(args.role_definition_id)}'")
        params = _pagination_params(args)
        if filters:
            params["$filter"] = " and ".join(filters)
        return await self._client.request_collection(
            "/roleManagement/directory/roleAssignments",
            params=params,
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def assign_directory_role(self, args: AssignDirectoryRoleArgs) -> Any:
        body = {
            "principalId": args.principal_id,
            "roleDefinitionId": args.role_definition_id,
            "directoryScopeId": args.directory_scope_id,
        }
        return await self._client.request(
            "POST", "/roleManagement/directory/roleAssignments", json_data=body
        )

    async def remove_role_assignment(self, args: RemoveRoleAssignmentArgs) -> Any:
        return await self._client.request(
            "DELETE", f"/roleManagement/directory/roleAssignments/{args.assignment_id}"
        )

    async def list_conditional_access_policies(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/identity/conditionalAccess/policies",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_conditional_access_policy(self, args: GetConditionalAccessPolicyArgs) -> Any:
        return await self._client.request(
            "GET", f"/identity/conditionalAccess/policies/{args.policy_id}"
        )

    async def set_conditional_access_policy_state(
        self, args: SetConditionalAccessPolicyStateArgs
    ) -> Any:
        return await self._client.request(
            "PATCH",
            f"/identity/conditionalAccess/policies/{args.policy_id}",
            json_data={"state": args.state},
        )

    async def list_subscribed_skus(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/subscribedSkus",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_user_license_details(self, args: GetUserLicenseDetailsArgs) -> Any:
        return await self._client.request("GET", f"/users/{args.user_id}/licenseDetails")

    async def assign_user_license(self, args: AssignUserLicenseArgs) -> Any:
        if not args.add_sku_ids and not args.remove_sku_ids:
            return ToolResult.failure(
                "validation_error",
                "Provide at least one SKU in add_sku_ids or remove_sku_ids.",
            )
        add_licenses = [
            {"skuId": sku, "disabledPlans": args.disabled_plans or []} for sku in args.add_sku_ids
        ]
        body = {"addLicenses": add_licenses, "removeLicenses": args.remove_sku_ids}
        return await self._client.request(
            "POST", f"/users/{args.user_id}/assignLicense", json_data=body
        )

    async def list_applications(self, args: ListApplicationsArgs) -> Any:
        filters: list[str] = []
        if args.display_name:
            filters.append(f"displayName eq '{_escape_odata_string(args.display_name)}'")
        if args.app_id:
            filters.append(f"appId eq '{_escape_odata_string(args.app_id)}'")
        params = _pagination_params(args)
        params.update(_select_params(args.select_fields))
        if filters:
            params["$filter"] = " and ".join(filters)
        return await self._client.request_collection(
            "/applications",
            params=params,
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_application(self, args: GetApplicationArgs) -> Any:
        return await self._client.request("GET", f"/applications/{args.application_id}")

    async def update_application(self, args: UpdateApplicationArgs) -> Any:
        if not args.update_data:
            return ToolResult.failure(
                "validation_error", "Provide update_data with at least one property to change."
            )
        return await self._client.request(
            "PATCH", f"/applications/{args.application_id}", json_data=args.update_data
        )

    async def delete_application(self, args: DeleteApplicationArgs) -> Any:
        return await self._client.request("DELETE", f"/applications/{args.application_id}")

    async def list_eligible_role_assignments(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/roleManagement/directory/roleEligibilityScheduleInstances",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_active_role_assignment_schedules(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/roleManagement/directory/roleAssignmentScheduleInstances",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def create_role_eligibility_request(self, args: CreateRoleEligibilityRequestArgs) -> Any:
        body = {
            "principalId": args.principal_id,
            "roleDefinitionId": args.role_definition_id,
            "justification": args.justification,
            "action": "adminAssign",
            "directoryScopeId": args.directory_scope_id,
        }
        return await self._client.request(
            "POST", "/roleManagement/directory/roleEligibilityScheduleRequests", json_data=body
        )

    async def activate_eligible_role(self, args: ActivateEligibleRoleArgs) -> Any:
        body = {
            "principalId": args.principal_id,
            "roleDefinitionId": args.role_definition_id,
            "justification": args.justification,
            "action": "selfActivate",
            "directoryScopeId": args.directory_scope_id,
        }
        return await self._client.request(
            "POST", "/roleManagement/directory/roleAssignmentScheduleRequests", json_data=body
        )

    async def list_access_review_definitions(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/identityGovernance/accessReviews/definitions",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_access_packages(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/identityGovernance/entitlementManagement/accessPackages",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def stop_access_review_instance(self, args: StopAccessReviewInstanceArgs) -> Any:
        endpoint = (
            f"/identityGovernance/accessReviews/definitions/{args.definition_id}"
            f"/instances/{args.instance_id}/stop"
        )
        return await self._client.request("POST", endpoint)

    async def list_user_authentication_methods(
        self, args: ListUserAuthenticationMethodsArgs
    ) -> Any:
        return await self._client.request_collection(
            f"/users/{args.user_id}/authentication/methods",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def delete_user_authentication_method(
        self, args: DeleteUserAuthenticationMethodArgs
    ) -> Any:
        return await self._client.request(
            "DELETE",
            f"/users/{args.user_id}/authentication/microsoftAuthenticatorMethods/{args.method_id}",
        )

    async def reset_password(self, args: ResetPasswordArgs) -> Any:
        body: dict[str, Any] = {}
        if args.new_password is not None:
            body["newPassword"] = args.new_password
        return await self._client.request(
            "POST",
            f"/users/{args.user_id}/authentication/methods/{args.method_id}/resetPassword",
            json_data=body or None,
        )

    async def list_risky_users(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/identityProtection/riskyUsers",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_risk_detections(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/identityProtection/riskDetections",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def dismiss_risky_users(self, args: DismissRiskyUsersArgs) -> Any:
        return await self._client.request(
            "POST",
            "/identityProtection/riskyUsers/dismiss",
            json_data={"userIds": args.user_ids},
        )

    async def confirm_compromised_users(self, args: ConfirmCompromisedUsersArgs) -> Any:
        return await self._client.request(
            "POST",
            "/identityProtection/riskyUsers/confirmCompromised",
            json_data={"userIds": args.user_ids},
        )

    async def graph_operation(self, args: GenericGraphOperationArgs) -> Any:
        """Execute a cataloged Graph operation, enforcing confirmation and path-param validation."""
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
    """Build a ToolDefinition from common metadata, defaulting to a safe read-only tool."""
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
    """Build an OData $select param dict, or empty when no fields are requested."""
    return {"$select": ",".join(select_fields)} if select_fields else {}


def _pagination_params(args: Any) -> dict[str, Any]:
    return {"$top": args.top} if getattr(args, "top", None) else {}


def _odata_params(args: Any) -> dict[str, Any]:
    """Assemble OData $select, $filter, and $top params from an args model's attributes."""
    params = _select_params(getattr(args, "select_fields", None))
    if getattr(args, "filter_expression", None):
        params["$filter"] = args.filter_expression
    if getattr(args, "top", None):
        params["$top"] = args.top
    return params


def _log_query_params(args: LogQueryArgs) -> dict[str, Any]:
    """Build a combined OData $filter (UPN, date, error code, free-form) plus $top for log queries."""
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
    """Build a combined OData $filter (severity, status, assignee, date, free-form) plus $top for security queries."""
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
    """Return the payload for a unique match, else a not_found or ambiguous_identity failure."""
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
    """Escape single quotes for safe interpolation into an OData string literal."""
    return value.replace("'", "''")


def _format_datetime(value: datetime) -> str:
    """Normalize a datetime to UTC and render it as a Graph-compatible Z-suffixed ISO string."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


_OBJECT_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def _looks_like_object_id(value: str) -> bool:
    """Return whether the value matches the GUID shape used by Graph object IDs."""
    return bool(_OBJECT_ID_RE.match(value.strip()))
