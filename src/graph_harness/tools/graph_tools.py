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


# --- Lifecycle workflows ----------------------------------------------------


class ListWorkflowRunsArgs(PaginationArgs):
    workflow_id: str = Field(description="Lifecycle workflow ID.")


class ActivateWorkflowArgs(ConfirmableArgs):
    workflow_id: str = Field(description="Lifecycle workflow ID to run on demand.")
    subject_ids: list[str] = Field(description="Object IDs of users to run the workflow against.")


# --- Administrative units ---------------------------------------------------


class ListAdministrativeUnitMembersArgs(PaginationArgs):
    au_id: str = Field(description="Administrative unit object ID.")


class AddAdministrativeUnitMemberArgs(ConfirmableArgs):
    au_id: str = Field(description="Administrative unit object ID.")
    member_id: str = Field(description="Directory object ID of the member to add.")


# --- Cross-tenant / B2B collaboration ---------------------------------------


class InviteGuestUserArgs(ConfirmableArgs):
    email: str = Field(description="Email address of the external user to invite.")
    redirect_url: str = Field(
        default="https://myapps.microsoft.com",
        description="URL the invited user is redirected to after accepting.",
    )
    send_message: bool = Field(
        default=True, description="Whether Graph sends the invitation email."
    )


# --- Microsoft 365 productivity --------------------------------------------


class ListMessagesArgs(PaginationArgs):
    """Input for listing a user's mail messages."""

    user_id: str = Field(description="User object ID or userPrincipalName.")


class GetMessageArgs(BaseModel):
    """Input for fetching a single mail message."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    message_id: str = Field(description="Mail message ID.")


class ListMailFoldersArgs(BaseModel):
    """Input for listing a user's mail folders."""

    user_id: str = Field(description="User object ID or userPrincipalName.")


class SendMailArgs(ConfirmableArgs):
    """Confirmable input for sending mail as a user."""

    user_id: str = Field(description="User object ID or userPrincipalName of the sender.")
    subject: str = Field(description="Message subject line.")
    body: str = Field(description="Plain-text message body.")
    to_recipients: list[str] = Field(description="Recipient email addresses.")


class ListEventsArgs(PaginationArgs):
    """Input for listing a user's calendar events."""

    user_id: str = Field(description="User object ID or userPrincipalName.")


class GetEventArgs(BaseModel):
    """Input for fetching a single calendar event."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    event_id: str = Field(description="Calendar event ID.")


class CreateEventArgs(ConfirmableArgs):
    """Confirmable input for creating a calendar event."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    subject: str = Field(description="Event subject line.")
    start_datetime: str = Field(description="Event start in ISO 8601 (e.g. 2026-06-01T09:00:00).")
    end_datetime: str = Field(description="Event end in ISO 8601 (e.g. 2026-06-01T10:00:00).")
    time_zone: str = Field(default="UTC", description="IANA/Windows time zone name.")
    attendees: list[str] = Field(default_factory=list, description="Attendee email addresses.")


class CancelEventArgs(ConfirmableArgs):
    """Confirmable input for cancelling a calendar event."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    event_id: str = Field(description="Calendar event ID to cancel.")
    comment: str = Field(default="", description="Optional cancellation comment for attendees.")


class ListJoinedTeamsArgs(BaseModel):
    """Input for listing the teams a user has joined."""

    user_id: str = Field(description="User object ID or userPrincipalName.")


class ListChannelsArgs(BaseModel):
    """Input for listing the channels of a team."""

    team_id: str = Field(description="Team (group) ID.")


class ListChannelMessagesArgs(BaseModel):
    """Input for listing the messages in a team channel."""

    team_id: str = Field(description="Team (group) ID.")
    channel_id: str = Field(description="Channel ID.")


class SendChannelMessageArgs(ConfirmableArgs):
    """Confirmable input for posting a message to a team channel."""

    team_id: str = Field(description="Team (group) ID.")
    channel_id: str = Field(description="Channel ID.")
    content: str = Field(description="Message body content.")


class ListDriveItemsArgs(PaginationArgs):
    """Input for listing items in the root of a user's drive."""

    user_id: str = Field(description="User object ID or userPrincipalName.")


class GetDriveItemArgs(BaseModel):
    """Input for fetching a single drive item by ID."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    item_id: str = Field(description="Drive item ID.")


class SearchDriveArgs(BaseModel):
    """Input for searching a user's drive."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    query: str = Field(description="Search query string.")


class CreateSharingLinkArgs(ConfirmableArgs):
    """Confirmable input for creating a sharing link on a drive item."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    item_id: str = Field(description="Drive item ID to share.")
    link_type: Literal["view", "edit"] = Field(default="view", description="Sharing link type.")
    scope: str = Field(default="organization", description="Sharing link scope.")


# --- Device management (Intune) --------------------------------------------


class GetManagedDeviceArgs(BaseModel):
    """Input for fetching a single Intune managed device by ID."""

    device_id: str = Field(description="Intune managed device ID.")


class WipeManagedDeviceArgs(ConfirmableArgs):
    """Confirmable input for wiping an Intune managed device."""

    device_id: str = Field(description="Intune managed device ID.")
    body: dict[str, Any] = Field(default_factory=dict, description="Optional wipe options.")


class RetireManagedDeviceArgs(ConfirmableArgs):
    """Confirmable input for retiring an Intune managed device."""

    device_id: str = Field(description="Intune managed device ID.")


class SyncManagedDeviceArgs(ConfirmableArgs):
    """Confirmable input for triggering a sync on an Intune managed device."""

    device_id: str = Field(description="Intune managed device ID.")


# --- Tier-1 collaboration, productivity, and reporting ---------------------


class ListUserChatsArgs(PaginationArgs):
    """Input for listing a user's Teams chats."""

    user_id: str = Field(description="User object ID or userPrincipalName.")


class ListChatMessagesArgs(PaginationArgs):
    """Input for listing the messages in a Teams chat."""

    chat_id: str = Field(description="Teams chat ID.")


class SendChatMessageArgs(ConfirmableArgs):
    """Confirmable input for sending a message to a Teams chat."""

    chat_id: str = Field(description="Teams chat ID.")
    content: str = Field(description="Message body content.")


class ListSitesArgs(PaginationArgs):
    """Input for listing SharePoint sites."""


class GetSiteArgs(BaseModel):
    """Input for fetching a single SharePoint site by ID."""

    site_id: str = Field(description="SharePoint site ID.")


class ListSiteListsArgs(BaseModel):
    """Input for listing the lists in a SharePoint site."""

    site_id: str = Field(description="SharePoint site ID.")


class ListListItemsArgs(BaseModel):
    """Input for listing the items in a SharePoint list."""

    site_id: str = Field(description="SharePoint site ID.")
    list_id: str = Field(description="SharePoint list ID.")


class CreateListItemArgs(ConfirmableArgs):
    """Confirmable input for creating an item in a SharePoint list."""

    site_id: str = Field(description="SharePoint site ID.")
    list_id: str = Field(description="SharePoint list ID.")
    fields: dict[str, Any] = Field(description="Field name/value pairs for the new list item.")


class ListNotebooksArgs(BaseModel):
    """Input for listing a user's OneNote notebooks."""

    user_id: str = Field(description="User object ID or userPrincipalName.")


class ListNotebookSectionsArgs(BaseModel):
    """Input for listing the sections in a OneNote notebook."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    notebook_id: str = Field(description="OneNote notebook ID.")


class ListSectionPagesArgs(BaseModel):
    """Input for listing the pages in a OneNote section."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    section_id: str = Field(description="OneNote section ID.")


class ListContactsArgs(PaginationArgs):
    """Input for listing a user's contacts."""

    user_id: str = Field(description="User object ID or userPrincipalName.")


class GetContactArgs(BaseModel):
    """Input for fetching a single contact."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    contact_id: str = Field(description="Contact ID.")


class CreateContactArgs(ConfirmableArgs):
    """Confirmable input for creating a contact for a user."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    given_name: str = Field(description="Contact given (first) name.")
    surname: str = Field(description="Contact surname (last name).")
    email: str = Field(description="Contact email address.")


class ListGroupPlansArgs(BaseModel):
    """Input for listing the Planner plans owned by a group."""

    group_id: str = Field(description="Group (team) ID that owns the plans.")


class GetPlanArgs(BaseModel):
    """Input for fetching a single Planner plan by ID."""

    plan_id: str = Field(description="Planner plan ID.")


class ListPlanTasksArgs(BaseModel):
    """Input for listing the tasks in a Planner plan."""

    plan_id: str = Field(description="Planner plan ID.")


class CreatePlannerTaskArgs(ConfirmableArgs):
    """Confirmable input for creating a Planner task."""

    plan_id: str = Field(description="Planner plan ID to add the task to.")
    title: str = Field(description="Task title.")
    bucket_id: str | None = Field(default=None, description="Optional Planner bucket ID.")


class ListTodoListsArgs(BaseModel):
    """Input for listing a user's To Do lists."""

    user_id: str = Field(description="User object ID or userPrincipalName.")


class ListTodoTasksArgs(BaseModel):
    """Input for listing the tasks in a To Do list."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    list_id: str = Field(description="To Do list ID.")


class CreateTodoTaskArgs(ConfirmableArgs):
    """Confirmable input for creating a To Do task."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    list_id: str = Field(description="To Do list ID.")
    title: str = Field(description="Task title.")


ReportPeriod = Literal["D7", "D30", "D90", "D180"]


class ReportPeriodArgs(BaseModel):
    """Input selecting the aggregation period for a usage report."""

    period: ReportPeriod = "D7"


# --- Tier-2 security, compliance, and engagement ---------------------------


class EmptyArgs(BaseModel):
    """Input for a tool that takes no parameters."""


SecureScoreControlState = Literal["Default", "Ignored", "ThirdParty", "Reviewed"]


class UpdateSecureScoreControlStateArgs(ConfirmableArgs):
    """Confirmable input for updating the review state of a Secure Score control."""

    control_id: str = Field(description="Secure Score control profile ID.")
    state: SecureScoreControlState = Field(description="New control state to record.")
    comment: str | None = Field(default=None, description="Optional reviewer comment.")


class CreateEdiscoveryCaseArgs(ConfirmableArgs):
    """Confirmable input for creating an eDiscovery case."""

    display_name: str = Field(description="Display name for the new eDiscovery case.")
    description: str | None = Field(default=None, description="Optional case description.")


class AddEdiscoveryCustodianArgs(ConfirmableArgs):
    """Confirmable input for adding a custodian to an eDiscovery case."""

    case_id: str = Field(description="eDiscovery case ID.")
    email: str = Field(description="Custodian email address (userPrincipalName).")


class ExtractSensitivityLabelsArgs(BaseModel):
    """Input for extracting the sensitivity labels applied to a drive item."""

    drive_id: str = Field(description="Drive ID containing the item.")
    item_id: str = Field(description="Drive item ID to inspect.")


class GetEdiscoveryCaseArgs(BaseModel):
    """Input for fetching a single eDiscovery case."""

    case_id: str = Field(description="eDiscovery case ID.")


class ListEdiscoveryCustodiansArgs(BaseModel):
    """Input for listing the custodians on an eDiscovery case."""

    case_id: str = Field(description="eDiscovery case ID.")


class CloseEdiscoveryCaseArgs(ConfirmableArgs):
    """Confirmable input for closing an eDiscovery case."""

    case_id: str = Field(description="eDiscovery case ID to close.")


class GetSensitivityLabelArgs(BaseModel):
    """Input for fetching a single sensitivity label."""

    label_id: str = Field(description="Sensitivity label ID.")


class GetThreatIntelHostArgs(BaseModel):
    """Input for fetching a threat intelligence host."""

    host_id: str = Field(description="Host identifier (hostname or IP).")


class GetVulnerabilityArgs(BaseModel):
    """Input for fetching a threat intelligence vulnerability."""

    vulnerability_id: str = Field(description="Vulnerability ID (e.g. a CVE identifier).")


class GetOnlineMeetingArgs(BaseModel):
    """Input for fetching a user's online meeting."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    meeting_id: str = Field(description="Online meeting ID.")


class ListAttendanceReportsArgs(BaseModel):
    """Input for listing an online meeting's attendance reports."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    meeting_id: str = Field(description="Online meeting ID.")


class CreateOnlineMeetingArgs(ConfirmableArgs):
    """Confirmable input for creating an online meeting for a user."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    subject: str = Field(description="Meeting subject.")
    start_date_time: str = Field(description="Meeting start time (ISO 8601).")
    end_date_time: str = Field(description="Meeting end time (ISO 8601).")


class GetBookingBusinessArgs(BaseModel):
    """Input for fetching a single Bookings business."""

    business_id: str = Field(description="Bookings business ID.")


class ListBookingServicesArgs(BaseModel):
    """Input for listing the services offered by a Bookings business."""

    business_id: str = Field(description="Bookings business ID.")


class ListBookingAppointmentsArgs(BaseModel):
    """Input for listing the appointments of a Bookings business."""

    business_id: str = Field(description="Bookings business ID.")


class CreateBookingAppointmentArgs(ConfirmableArgs):
    """Confirmable input for creating a Bookings appointment."""

    business_id: str = Field(description="Bookings business ID.")
    service_id: str = Field(description="Bookings service ID being booked.")
    customer_name: str = Field(description="Customer display name.")
    start_date_time: str = Field(description="Appointment start time (ISO 8601).")
    end_date_time: str = Field(description="Appointment end time (ISO 8601).")


class SearchQueryArgs(BaseModel):
    """Input for a Microsoft Search query across one or more entity types."""

    query: str = Field(description="Search query string (KQL or free text).")
    entity_types: list[str] = Field(
        default_factory=lambda: ["message"],
        description="Entity types to search (e.g. message, event, driveItem, site, chatMessage).",
    )
    size: int = Field(default=25, ge=1, le=500, description="Maximum hits to return.")


# --- Tier-3 long-tail / specialized ----------------------------------------


class GetPrinterArgs(BaseModel):
    """Input for fetching a Universal Print printer."""

    printer_id: str = Field(description="Universal Print printer ID.")


class ListPrintJobsArgs(BaseModel):
    """Input for listing the jobs queued on a Universal Print printer."""

    printer_id: str = Field(description="Universal Print printer ID.")


class CancelPrintJobArgs(ConfirmableArgs):
    """Confirmable input for cancelling a print job."""

    printer_id: str = Field(description="Universal Print printer ID.")
    job_id: str = Field(description="Print job ID to cancel.")


class ListClassMembersArgs(BaseModel):
    """Input for listing the members of an EDU class."""

    class_id: str = Field(description="Education class ID.")


class ListClassAssignmentsArgs(BaseModel):
    """Input for listing the assignments of an EDU class."""

    class_id: str = Field(description="Education class ID.")


class GetEducationUserArgs(BaseModel):
    """Input for fetching an EDU user."""

    user_id: str = Field(description="Education user ID or userPrincipalName.")


class GetCloudPcArgs(BaseModel):
    """Input for fetching a Windows 365 Cloud PC."""

    cloud_pc_id: str = Field(description="Cloud PC ID.")


class RebootCloudPcArgs(ConfirmableArgs):
    """Confirmable input for rebooting a Cloud PC."""

    cloud_pc_id: str = Field(description="Cloud PC ID to reboot.")


class ReprovisionCloudPcArgs(ConfirmableArgs):
    """Confirmable input for reprovisioning a Cloud PC (destructive)."""

    cloud_pc_id: str = Field(description="Cloud PC ID to reprovision.")


class GetEngageCommunityArgs(BaseModel):
    """Input for fetching a Viva Engage community."""

    community_id: str = Field(description="Viva Engage community ID.")


class GetSubscriptionArgs(BaseModel):
    """Input for fetching a change-notification subscription."""

    subscription_id: str = Field(description="Subscription ID.")


class CreateSubscriptionArgs(ConfirmableArgs):
    """Confirmable input for creating a change-notification subscription (webhook)."""

    change_type: str = Field(
        description="Comma-separated change types (e.g. 'created,updated,deleted')."
    )
    notification_url: str = Field(description="HTTPS notification endpoint that Graph will call.")
    resource: str = Field(
        description="Resource path to watch (e.g. 'me/mailFolders/Inbox/messages')."
    )
    expiration_date_time: str = Field(
        description="Subscription expiration time (ISO 8601, within Graph's per-resource cap)."
    )
    client_state: str | None = Field(
        default=None,
        description="Opaque value echoed in every notification for the receiver to validate.",
    )


class RenewSubscriptionArgs(ConfirmableArgs):
    """Confirmable input for extending a subscription's expiration."""

    subscription_id: str = Field(description="Subscription ID to renew.")
    expiration_date_time: str = Field(description="New expiration time (ISO 8601).")


class DeleteSubscriptionArgs(ConfirmableArgs):
    """Confirmable input for deleting a change-notification subscription."""

    subscription_id: str = Field(description="Subscription ID to delete.")


# --- Tier-4 write completeness ---------------------------------------------


class CreateUserArgs(ConfirmableArgs):
    """Confirmable input for creating a new user."""

    user_principal_name: str = Field(description="The new user's userPrincipalName.")
    display_name: str = Field(description="Display name.")
    mail_nickname: str = Field(description="Mail nickname (mailbox prefix).")
    password: str = Field(description="Initial password for the new user.")
    account_enabled: bool = Field(default=True, description="Whether the account is enabled.")


class CreateGroupArgs(ConfirmableArgs):
    """Confirmable input for creating a new group."""

    display_name: str = Field(description="Group display name.")
    mail_nickname: str = Field(description="Group mail nickname.")
    mail_enabled: bool = Field(default=False, description="Whether the group is mail-enabled.")
    security_enabled: bool = Field(
        default=True, description="Whether the group is a security group."
    )
    description: str | None = Field(default=None, description="Optional group description.")


class UpdateGroupArgs(ConfirmableArgs):
    """Confirmable input for updating a group's mutable properties."""

    group_id: str = Field(description="Group ID to update.")
    display_name: str | None = Field(default=None, description="New display name.")
    description: str | None = Field(default=None, description="New description.")


class DeleteGroupArgs(ConfirmableArgs):
    """Confirmable input for deleting a group (destructive)."""

    group_id: str = Field(description="Group ID to delete.")


class GroupOwnerArgs(ConfirmableArgs):
    """Confirmable input for adding or removing a group owner."""

    group_id: str = Field(description="Group ID.")
    owner_id: str = Field(description="Directory object ID of the owner.")


class SetServicePrincipalEnabledArgs(ConfirmableArgs):
    """Confirmable input for enabling or disabling a service principal."""

    service_principal_id: str = Field(description="Service principal object ID.")
    account_enabled: bool = Field(description="New accountEnabled value.")


class AddApplicationPasswordArgs(ConfirmableArgs):
    """Confirmable input for adding a client secret (password) to an application."""

    application_id: str = Field(description="Application object ID.")
    display_name: str = Field(description="Friendly name for the new secret.")


class RemoveApplicationPasswordArgs(ConfirmableArgs):
    """Confirmable input for removing a client secret from an application."""

    application_id: str = Field(description="Application object ID.")
    key_id: str = Field(description="Key identifier of the password credential to remove.")


class UploadFileArgs(ConfirmableArgs):
    """Confirmable input for uploading a small file to a drive."""

    drive_id: str = Field(description="Drive ID to upload into.")
    parent_path: str = Field(
        default="root",
        description="Parent folder path or 'root'. Relative paths are joined under root.",
    )
    file_name: str = Field(description="File name to create or overwrite.")
    content: str = Field(description="UTF-8 text content for the upload (small-file path).")


class CreateFolderArgs(ConfirmableArgs):
    """Confirmable input for creating a folder in a drive."""

    drive_id: str = Field(description="Drive ID.")
    parent_id: str = Field(default="root", description="Parent folder ID, or 'root'.")
    folder_name: str = Field(description="New folder name.")


class DeleteDriveItemArgs(ConfirmableArgs):
    """Confirmable input for deleting a drive item (destructive)."""

    drive_id: str = Field(description="Drive ID.")
    item_id: str = Field(description="Drive item ID to delete.")


class CopyDriveItemArgs(ConfirmableArgs):
    """Confirmable input for copying a drive item."""

    drive_id: str = Field(description="Source drive ID.")
    item_id: str = Field(description="Source drive item ID.")
    new_name: str | None = Field(default=None, description="Optional new name for the copy.")
    target_parent_id: str | None = Field(
        default=None, description="Optional target parent folder ID."
    )


class MessageActionArgs(ConfirmableArgs):
    """Confirmable input for an action targeting a specific mail message."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    message_id: str = Field(description="Mail message ID.")


class ReplyMessageArgs(MessageActionArgs):
    """Confirmable input for replying to a mail message."""

    comment: str = Field(description="Reply comment to prepend to the original message.")
    reply_all: bool = Field(default=False, description="Whether to reply to all recipients.")


class ForwardMessageArgs(MessageActionArgs):
    """Confirmable input for forwarding a mail message."""

    to_recipients: list[str] = Field(description="Forward target email addresses.")
    comment: str | None = Field(default=None, description="Optional comment to include.")


class MoveMessageArgs(MessageActionArgs):
    """Confirmable input for moving a mail message to another folder."""

    destination_id: str = Field(description="Destination mail folder ID.")


class UpdateMessageArgs(MessageActionArgs):
    """Confirmable input for updating a mail message (e.g. mark read, set flag)."""

    is_read: bool | None = Field(default=None, description="Set the message read state.")
    flag_status: str | None = Field(
        default=None,
        description="Flag status (e.g. 'flagged', 'complete', 'notFlagged').",
    )


class CreateMailFolderArgs(ConfirmableArgs):
    """Confirmable input for creating a mail folder."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    display_name: str = Field(description="Folder display name.")


class UpdateEventArgs(ConfirmableArgs):
    """Confirmable input for updating a calendar event."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    event_id: str = Field(description="Calendar event ID.")
    subject: str | None = Field(default=None, description="New subject.")
    body_content: str | None = Field(default=None, description="New body content.")


EventResponse = Literal["accept", "tentativelyAccept", "decline"]


class RespondToEventArgs(ConfirmableArgs):
    """Confirmable input for responding to a calendar event invite."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    event_id: str = Field(description="Calendar event ID.")
    response: EventResponse = Field(description="Response to send.")
    comment: str | None = Field(default=None, description="Optional response comment.")
    send_response: bool = Field(default=True, description="Whether to notify the organizer.")


class CreateTeamArgs(ConfirmableArgs):
    """Confirmable input for creating a Microsoft Team."""

    display_name: str = Field(description="Team display name.")
    description: str | None = Field(default=None, description="Optional team description.")
    template: str = Field(
        default="https://graph.microsoft.com/v1.0/teamsTemplates('standard')",
        description="Team template binding URL.",
    )


class AddTeamMemberArgs(ConfirmableArgs):
    """Confirmable input for adding a member to a team."""

    team_id: str = Field(description="Team ID.")
    user_id: str = Field(description="User object ID to add.")
    roles: list[str] = Field(
        default_factory=list, description="Optional roles (e.g. ['owner'])."
    )


class CreateChannelArgs(ConfirmableArgs):
    """Confirmable input for creating a channel in a team."""

    team_id: str = Field(description="Team ID.")
    display_name: str = Field(description="Channel display name.")
    membership_type: str = Field(
        default="standard",
        description="Channel membership type (standard, private, shared).",
    )


class ArchiveTeamArgs(ConfirmableArgs):
    """Confirmable input for archiving a team."""

    team_id: str = Field(description="Team ID to archive.")


class CreateChatArgs(ConfirmableArgs):
    """Confirmable input for creating a Teams chat."""

    chat_type: str = Field(
        default="oneOnOne", description="Chat type (oneOnOne or group)."
    )
    member_ids: list[str] = Field(description="User IDs to include as members.")
    topic: str | None = Field(default=None, description="Optional chat topic (group chats).")


class UpdatePlannerTaskArgs(ConfirmableArgs):
    """Confirmable input for updating a Planner task (e.g. mark complete)."""

    task_id: str = Field(description="Planner task ID.")
    etag: str = Field(description="ETag from the task GET (used as If-Match).")
    title: str | None = Field(default=None, description="New title.")
    percent_complete: int | None = Field(
        default=None, ge=0, le=100, description="Completion percent (100 = done)."
    )


class DeletePlannerTaskArgs(ConfirmableArgs):
    """Confirmable input for deleting a Planner task (destructive)."""

    task_id: str = Field(description="Planner task ID.")
    etag: str = Field(description="ETag from the task GET (used as If-Match).")


class UpdateTodoTaskArgs(ConfirmableArgs):
    """Confirmable input for updating a To Do task."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    list_id: str = Field(description="To Do list ID.")
    task_id: str = Field(description="To Do task ID.")
    title: str | None = Field(default=None, description="New title.")
    status: str | None = Field(
        default=None,
        description="New status (e.g. 'completed', 'inProgress').",
    )


class DeleteTodoTaskArgs(ConfirmableArgs):
    """Confirmable input for deleting a To Do task (destructive)."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    list_id: str = Field(description="To Do list ID.")
    task_id: str = Field(description="To Do task ID.")


class UpdateContactArgs(ConfirmableArgs):
    """Confirmable input for updating a contact."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    contact_id: str = Field(description="Contact ID.")
    given_name: str | None = Field(default=None, description="New given name.")
    surname: str | None = Field(default=None, description="New surname.")
    email: str | None = Field(default=None, description="New email address.")


class DeleteContactArgs(ConfirmableArgs):
    """Confirmable input for deleting a contact (destructive)."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    contact_id: str = Field(description="Contact ID.")


class UpdateListItemArgs(ConfirmableArgs):
    """Confirmable input for updating a SharePoint list item."""

    site_id: str = Field(description="SharePoint site ID.")
    list_id: str = Field(description="SharePoint list ID.")
    item_id: str = Field(description="List item ID.")
    fields: dict[str, Any] = Field(description="Field name/value pairs to update.")


class DeleteListItemArgs(ConfirmableArgs):
    """Confirmable input for deleting a SharePoint list item (destructive)."""

    site_id: str = Field(description="SharePoint site ID.")
    list_id: str = Field(description="SharePoint list ID.")
    item_id: str = Field(description="List item ID to delete.")


class CreateConditionalAccessPolicyArgs(ConfirmableArgs):
    """Confirmable input for creating a Conditional Access policy.

    Accepts a Graph-shaped policy body so callers can express the full schema
    without us having to recreate every nested option as flat fields.
    """

    display_name: str = Field(description="Policy display name.")
    state: str = Field(
        default="enabledForReportingButNotEnforced",
        description="Policy state (enabled, disabled, enabledForReportingButNotEnforced).",
    )
    conditions: dict[str, Any] = Field(description="Graph conditions block.")
    grant_controls: dict[str, Any] | None = Field(
        default=None, description="Graph grantControls block."
    )


class DeleteConditionalAccessPolicyArgs(ConfirmableArgs):
    """Confirmable input for deleting a Conditional Access policy (destructive)."""

    policy_id: str = Field(description="Conditional Access policy ID to delete.")


class RemoteLockArgs(ConfirmableArgs):
    """Confirmable input for triggering a remote lock on a managed device."""

    device_id: str = Field(description="Intune managed device ID.")


class ResetPasscodeArgs(ConfirmableArgs):
    """Confirmable input for resetting the passcode on a managed device."""

    device_id: str = Field(description="Intune managed device ID.")


class RestartManagedDeviceArgs(ConfirmableArgs):
    """Confirmable input for triggering a reboot on a managed device."""

    device_id: str = Field(description="Intune managed device ID.")


class CancelBookingAppointmentArgs(ConfirmableArgs):
    """Confirmable input for cancelling a Bookings appointment."""

    business_id: str = Field(description="Bookings business ID.")
    appointment_id: str = Field(description="Appointment ID to cancel.")
    cancellation_message: str | None = Field(
        default=None, description="Optional cancellation message to customer."
    )


class RemoveUserLicenseArgs(ConfirmableArgs):
    """Confirmable input for removing licenses from a user."""

    user_id: str = Field(description="User object ID or userPrincipalName.")
    remove_skus: list[str] = Field(description="License SKU IDs to remove.")


class RunHuntingQueryArgs(BaseModel):
    """Input for running an advanced hunting (KQL) query.

    Hunting queries are read-only by intent (they do not change tenant state),
    so this is a read tool — but it's exposed via POST per Graph's contract.
    """

    query: str = Field(description="Advanced hunting (KQL) query string.")
    timespan: str | None = Field(
        default=None,
        description="Optional ISO 8601 timespan (e.g. 'PT24H') to bound the query window.",
    )


class UpdateSecurityIncidentArgs(ConfirmableArgs):
    """Confirmable input for updating a security incident (assign / classify / resolve)."""

    incident_id: str = Field(description="Security incident ID.")
    status: str | None = Field(
        default=None, description="New status (e.g. 'active', 'resolved', 'redirected')."
    )
    classification: str | None = Field(
        default=None,
        description="Classification (e.g. 'truePositive', 'falsePositive', 'informationalExpectedActivity').",
    )
    assigned_to: str | None = Field(default=None, description="UPN or display name of assignee.")
    determination: str | None = Field(default=None, description="Determination label, if any.")


class CreateThreatAssessmentRequestArgs(ConfirmableArgs):
    """Confirmable input for submitting a Defender threat assessment request.

    Accepts a free-form Graph body so callers can submit email/URL/file/EmailFile
    requests without us flattening the polymorphic schema.
    """

    request_type: str = Field(
        description="Graph @odata.type discriminator (e.g. 'mailAssessmentRequest', 'urlAssessmentRequest', 'fileAssessmentRequest', 'emailFileAssessmentRequest')."
    )
    body: dict[str, Any] = Field(
        description="Type-specific request payload (URL string, file hash, message ID, etc.)."
    )


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
            _tool(
                "create_user",
                "Create a new user in the directory.",
                CreateUserArgs,
                self._handlers.create_user,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("user", "create", "provisioning", "mutation"),
            ),
            _tool(
                "create_group",
                "Create a new group.",
                CreateGroupArgs,
                self._handlers.create_group,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("group", "create", "mutation"),
            ),
            _tool(
                "update_group",
                "Update a group's display name or description.",
                UpdateGroupArgs,
                self._handlers.update_group,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("group", "update", "mutation"),
            ),
            _tool(
                "delete_group",
                "Delete a group.",
                DeleteGroupArgs,
                self._handlers.delete_group,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("group", "delete", "destructive"),
            ),
            _tool(
                "add_group_owner",
                "Add an owner to a group.",
                GroupOwnerArgs,
                self._handlers.add_group_owner,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("group", "owner", "add", "mutation"),
            ),
            _tool(
                "remove_group_owner",
                "Remove an owner from a group.",
                GroupOwnerArgs,
                self._handlers.remove_group_owner,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("group", "owner", "remove", "mutation"),
            ),
            _tool(
                "set_service_principal_enabled",
                "Enable or disable a service principal (accountEnabled).",
                SetServicePrincipalEnabledArgs,
                self._handlers.set_service_principal_enabled,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("service principal", "disable", "enable", "mutation"),
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
            _tool(
                "update_security_incident",
                "Update a security incident (assign, classify, resolve).",
                UpdateSecurityIncidentArgs,
                self._handlers.update_security_incident,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("security", "incidents", "update", "mutation"),
            ),
            _tool(
                "run_hunting_query",
                "Run an advanced hunting (KQL) query against the security data lake.",
                RunHuntingQueryArgs,
                self._handlers.run_hunting_query,
                domain=self.metadata.name,
                tags=("security", "hunting", "kql", "read"),
            ),
            _tool(
                "create_threat_assessment_request",
                "Submit a Defender threat assessment request (mail/url/file/emailFile).",
                CreateThreatAssessmentRequestArgs,
                self._handlers.create_threat_assessment_request,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("security", "threat assessment", "submit", "mutation"),
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
            _tool(
                "create_conditional_access_policy",
                "Create a new Conditional Access policy.",
                CreateConditionalAccessPolicyArgs,
                self._handlers.create_conditional_access_policy,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("conditional access", "policy", "create", "mutation"),
            ),
            _tool(
                "delete_conditional_access_policy",
                "Delete a Conditional Access policy (destructive).",
                DeleteConditionalAccessPolicyArgs,
                self._handlers.delete_conditional_access_policy,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("conditional access", "policy", "delete", "destructive"),
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
            _tool(
                "remove_user_license",
                "Remove licenses from a user.",
                RemoveUserLicenseArgs,
                self._handlers.remove_user_license,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("licenses", "remove", "mutation"),
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
            _tool(
                "add_application_password",
                "Add a client secret (password) to an application.",
                AddApplicationPasswordArgs,
                self._handlers.add_application_password,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("application", "secret", "password", "mutation"),
            ),
            _tool(
                "remove_application_password",
                "Remove a client secret from an application.",
                RemoveApplicationPasswordArgs,
                self._handlers.remove_application_password,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("application", "secret", "password", "remove", "mutation"),
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


class LifecycleWorkflowsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="lifecycle_workflows",
        display_name="Lifecycle Workflows",
        description=(
            "Microsoft Entra identity governance lifecycle workflows: list joiner/mover/leaver "
            "workflows and their runs, and activate a workflow on demand for chosen subjects."
        ),
        required_permissions=(
            "LifecycleWorkflows.Read.All",
            "LifecycleWorkflows.ReadWrite.All",
        ),
        tags=(
            "lifecycle",
            "joiner",
            "mover",
            "leaver",
            "offboarding",
            "onboarding",
            "automation",
        ),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_lifecycle_workflows",
                "List identity-governance lifecycle workflows.",
                PaginationArgs,
                self._handlers.list_lifecycle_workflows,
                domain=self.metadata.name,
                tags=("lifecycle", "workflows", "read"),
            ),
            _tool(
                "list_workflow_runs",
                "List runs for a lifecycle workflow.",
                ListWorkflowRunsArgs,
                self._handlers.list_workflow_runs,
                domain=self.metadata.name,
                tags=("lifecycle", "runs", "read"),
            ),
            _tool(
                "activate_workflow",
                "Activate a lifecycle workflow on demand for the given subjects.",
                ActivateWorkflowArgs,
                self._handlers.activate_workflow,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("lifecycle", "activate", "mutation"),
            ),
        ]


class AdministrativeUnitsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="administrative_units",
        display_name="Administrative Units",
        description=(
            "Microsoft Entra administrative units: list administrative units and their members, "
            "and add a directory object as a member of an administrative unit."
        ),
        required_permissions=(
            "AdministrativeUnit.Read.All",
            "AdministrativeUnit.ReadWrite.All",
        ),
        tags=("administrative units", "scoping", "delegation", "directory", "entra"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_administrative_units",
                "List directory administrative units.",
                PaginationArgs,
                self._handlers.list_administrative_units,
                domain=self.metadata.name,
                tags=("administrative units", "directory", "read"),
            ),
            _tool(
                "list_administrative_unit_members",
                "List members of an administrative unit.",
                ListAdministrativeUnitMembersArgs,
                self._handlers.list_administrative_unit_members,
                domain=self.metadata.name,
                tags=("administrative units", "members", "read"),
            ),
            _tool(
                "add_administrative_unit_member",
                "Add a directory object as a member of an administrative unit.",
                AddAdministrativeUnitMemberArgs,
                self._handlers.add_administrative_unit_member,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("administrative units", "members", "add", "mutation"),
            ),
        ]


class B2BCollaborationDomain(GraphDomain):
    metadata = DomainMetadata(
        name="b2b_collaboration",
        display_name="Cross-tenant / B2B",
        description=(
            "Microsoft Entra cross-tenant and B2B collaboration: list guest users and invite an "
            "external user into the tenant as a guest."
        ),
        required_permissions=(
            "User.Invite.All",
            "User.ReadWrite.All",
        ),
        tags=("b2b", "guest", "cross-tenant", "collaboration", "invitation", "external", "entra"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_guest_users",
                "List guest (external) users in the directory.",
                PaginationArgs,
                self._handlers.list_guest_users,
                domain=self.metadata.name,
                tags=("b2b", "guest", "users", "read"),
            ),
            _tool(
                "invite_guest_user",
                "Invite an external user into the tenant as a guest.",
                InviteGuestUserArgs,
                self._handlers.invite_guest_user,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("b2b", "guest", "invite", "mutation"),
            ),
        ]


class MailDomain(GraphDomain):
    metadata = DomainMetadata(
        name="mail",
        display_name="Mail (Outlook)",
        description=(
            "Microsoft 365 Outlook mail: list and read a user's messages and mail folders, "
            "and send mail on a user's behalf."
        ),
        required_permissions=(
            "Mail.Read",
            "Mail.Send",
        ),
        tags=("mail", "outlook", "email", "messages", "inbox", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_messages",
                "List a user's mail messages.",
                ListMessagesArgs,
                self._handlers.list_messages,
                domain=self.metadata.name,
                tags=("mail", "messages", "read"),
            ),
            _tool(
                "get_message",
                "Get a single mail message by ID.",
                GetMessageArgs,
                self._handlers.get_message,
                domain=self.metadata.name,
                tags=("mail", "message", "read"),
            ),
            _tool(
                "list_mail_folders",
                "List a user's mail folders.",
                ListMailFoldersArgs,
                self._handlers.list_mail_folders,
                domain=self.metadata.name,
                tags=("mail", "folders", "read"),
            ),
            _tool(
                "send_mail",
                "Send mail on a user's behalf.",
                SendMailArgs,
                self._handlers.send_mail,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("mail", "send", "mutation"),
            ),
            _tool(
                "reply_message",
                "Reply to a mail message (optionally reply-all).",
                ReplyMessageArgs,
                self._handlers.reply_message,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("mail", "reply", "mutation"),
            ),
            _tool(
                "forward_message",
                "Forward a mail message to one or more recipients.",
                ForwardMessageArgs,
                self._handlers.forward_message,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("mail", "forward", "mutation"),
            ),
            _tool(
                "move_message",
                "Move a mail message to a different folder.",
                MoveMessageArgs,
                self._handlers.move_message,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("mail", "move", "mutation"),
            ),
            _tool(
                "update_message",
                "Update a mail message (e.g. mark read/unread, set flag).",
                UpdateMessageArgs,
                self._handlers.update_message,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("mail", "update", "mutation"),
            ),
            _tool(
                "delete_message",
                "Delete a mail message (destructive).",
                MessageActionArgs,
                self._handlers.delete_message,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("mail", "delete", "destructive"),
            ),
            _tool(
                "create_mail_folder",
                "Create a new mail folder for a user.",
                CreateMailFolderArgs,
                self._handlers.create_mail_folder,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("mail", "folder", "create", "mutation"),
            ),
        ]


class CalendarDomain(GraphDomain):
    metadata = DomainMetadata(
        name="calendar",
        display_name="Calendar & Events",
        description=(
            "Microsoft 365 calendar: list and read a user's events, create new events, "
            "and cancel existing events."
        ),
        required_permissions=(
            "Calendars.Read",
            "Calendars.ReadWrite",
        ),
        tags=("calendar", "events", "meetings", "outlook", "schedule", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_events",
                "List a user's calendar events.",
                ListEventsArgs,
                self._handlers.list_events,
                domain=self.metadata.name,
                tags=("calendar", "events", "read"),
            ),
            _tool(
                "get_event",
                "Get a single calendar event by ID.",
                GetEventArgs,
                self._handlers.get_event,
                domain=self.metadata.name,
                tags=("calendar", "event", "read"),
            ),
            _tool(
                "create_event",
                "Create a calendar event for a user.",
                CreateEventArgs,
                self._handlers.create_event,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("calendar", "event", "create", "mutation"),
            ),
            _tool(
                "cancel_event",
                "Cancel a calendar event.",
                CancelEventArgs,
                self._handlers.cancel_event,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("calendar", "event", "cancel", "mutation"),
            ),
            _tool(
                "update_event",
                "Update a calendar event's subject or body.",
                UpdateEventArgs,
                self._handlers.update_event,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("calendar", "event", "update", "mutation"),
            ),
            _tool(
                "respond_to_event",
                "Respond to a calendar event invite (accept / tentativelyAccept / decline).",
                RespondToEventArgs,
                self._handlers.respond_to_event,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("calendar", "event", "respond", "mutation"),
            ),
        ]


class TeamsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="teams",
        display_name="Teams",
        description=(
            "Microsoft Teams: list the teams a user has joined, list a team's channels and "
            "channel messages, and post a message to a channel."
        ),
        required_permissions=(
            "Team.ReadBasic.All",
            "Channel.ReadBasic.All",
            "ChannelMessage.Send",
        ),
        tags=("teams", "channels", "messages", "collaboration", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_joined_teams",
                "List the teams a user has joined.",
                ListJoinedTeamsArgs,
                self._handlers.list_joined_teams,
                domain=self.metadata.name,
                tags=("teams", "read"),
            ),
            _tool(
                "list_channels",
                "List the channels of a team.",
                ListChannelsArgs,
                self._handlers.list_channels,
                domain=self.metadata.name,
                tags=("teams", "channels", "read"),
            ),
            _tool(
                "list_channel_messages",
                "List the messages in a team channel.",
                ListChannelMessagesArgs,
                self._handlers.list_channel_messages,
                domain=self.metadata.name,
                tags=("teams", "channels", "messages", "read"),
            ),
            _tool(
                "send_channel_message",
                "Post a message to a team channel.",
                SendChannelMessageArgs,
                self._handlers.send_channel_message,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("teams", "channels", "message", "send", "mutation"),
            ),
            _tool(
                "create_team",
                "Create a new team from a Teams template.",
                CreateTeamArgs,
                self._handlers.create_team,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("teams", "team", "create", "mutation"),
            ),
            _tool(
                "add_team_member",
                "Add a member to a team.",
                AddTeamMemberArgs,
                self._handlers.add_team_member,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("teams", "members", "add", "mutation"),
            ),
            _tool(
                "create_channel",
                "Create a channel in a team.",
                CreateChannelArgs,
                self._handlers.create_channel,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("teams", "channels", "create", "mutation"),
            ),
            _tool(
                "archive_team",
                "Archive a team (read-only / no further activity).",
                ArchiveTeamArgs,
                self._handlers.archive_team,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("teams", "team", "archive", "mutation"),
            ),
        ]


class FilesDomain(GraphDomain):
    metadata = DomainMetadata(
        name="files",
        display_name="Files (OneDrive/SharePoint)",
        description=(
            "Microsoft 365 files: list and read items in a user's OneDrive, search the drive, "
            "and create a sharing link for an item."
        ),
        required_permissions=(
            "Files.Read.All",
            "Files.ReadWrite.All",
        ),
        tags=("files", "onedrive", "sharepoint", "documents", "drive", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_drive_items",
                "List items in the root of a user's drive.",
                ListDriveItemsArgs,
                self._handlers.list_drive_items,
                domain=self.metadata.name,
                tags=("files", "drive", "read"),
            ),
            _tool(
                "get_drive_item",
                "Get a single drive item by ID.",
                GetDriveItemArgs,
                self._handlers.get_drive_item,
                domain=self.metadata.name,
                tags=("files", "drive", "item", "read"),
            ),
            _tool(
                "search_drive",
                "Search a user's drive for items.",
                SearchDriveArgs,
                self._handlers.search_drive,
                domain=self.metadata.name,
                tags=("files", "drive", "search", "read"),
            ),
            _tool(
                "create_sharing_link",
                "Create a sharing link for a drive item.",
                CreateSharingLinkArgs,
                self._handlers.create_sharing_link,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("files", "drive", "share", "link", "mutation"),
            ),
            _tool(
                "upload_file",
                "Upload a small text file to a drive (PUT content).",
                UploadFileArgs,
                self._handlers.upload_file,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("files", "drive", "upload", "mutation"),
            ),
            _tool(
                "create_folder",
                "Create a folder in a drive.",
                CreateFolderArgs,
                self._handlers.create_folder,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("files", "drive", "folder", "create", "mutation"),
            ),
            _tool(
                "delete_drive_item",
                "Delete a drive item (destructive).",
                DeleteDriveItemArgs,
                self._handlers.delete_drive_item,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("files", "drive", "delete", "destructive"),
            ),
            _tool(
                "copy_drive_item",
                "Copy a drive item to a new name or parent.",
                CopyDriveItemArgs,
                self._handlers.copy_drive_item,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("files", "drive", "copy", "mutation"),
            ),
        ]


class DeviceManagementDomain(GraphDomain):
    metadata = DomainMetadata(
        name="device_management",
        display_name="Device Management (Intune)",
        description=(
            "Microsoft Intune device management: inventory managed devices, read device "
            "compliance and configuration policies, and perform device actions such as "
            "wipe, retire, and sync."
        ),
        required_permissions=(
            "DeviceManagementManagedDevices.Read.All",
            "DeviceManagementManagedDevices.ReadWrite.All",
            "DeviceManagementConfiguration.Read.All",
        ),
        tags=(
            "intune",
            "mdm",
            "endpoint",
            "managed devices",
            "compliance",
            "configuration",
            "wipe",
            "retire",
            "sync",
        ),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_managed_devices",
                "List Intune managed devices.",
                PaginationArgs,
                self._handlers.list_managed_devices,
                domain=self.metadata.name,
                tags=("intune", "managed devices", "read"),
            ),
            _tool(
                "get_managed_device",
                "Get an Intune managed device by ID.",
                GetManagedDeviceArgs,
                self._handlers.get_managed_device,
                domain=self.metadata.name,
                tags=("intune", "managed device", "read"),
            ),
            _tool(
                "list_device_compliance_policies",
                "List Intune device compliance policies.",
                PaginationArgs,
                self._handlers.list_device_compliance_policies,
                domain=self.metadata.name,
                tags=("intune", "compliance", "policy", "read"),
            ),
            _tool(
                "list_device_configurations",
                "List Intune device configuration profiles.",
                PaginationArgs,
                self._handlers.list_device_configurations,
                domain=self.metadata.name,
                tags=("intune", "configuration", "profile", "read"),
            ),
            _tool(
                "wipe_managed_device",
                "Wipe an Intune managed device.",
                WipeManagedDeviceArgs,
                self._handlers.wipe_managed_device,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("intune", "managed device", "wipe", "mutation"),
            ),
            _tool(
                "retire_managed_device",
                "Retire an Intune managed device.",
                RetireManagedDeviceArgs,
                self._handlers.retire_managed_device,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("intune", "managed device", "retire", "mutation"),
            ),
            _tool(
                "sync_managed_device",
                "Trigger a sync on an Intune managed device.",
                SyncManagedDeviceArgs,
                self._handlers.sync_managed_device,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("intune", "managed device", "sync", "mutation"),
            ),
            _tool(
                "remote_lock_device",
                "Trigger a remote lock on a managed device.",
                RemoteLockArgs,
                self._handlers.remote_lock_device,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("intune", "managed device", "lock", "mutation"),
            ),
            _tool(
                "reset_device_passcode",
                "Reset the passcode on a managed device.",
                ResetPasscodeArgs,
                self._handlers.reset_device_passcode,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="security_mutation",
                tags=("intune", "managed device", "passcode", "mutation"),
            ),
            _tool(
                "restart_managed_device",
                "Restart a managed device.",
                RestartManagedDeviceArgs,
                self._handlers.restart_managed_device,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("intune", "managed device", "restart", "mutation"),
            ),
        ]


class ChatsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="chats",
        display_name="Chats",
        description=(
            "Microsoft Teams chats: list a user's chats, read chat messages, and send a "
            "message to a chat."
        ),
        required_permissions=(
            "Chat.Read.All",
            "Chat.ReadWrite.All",
            "ChatMessage.Send",
        ),
        tags=("chats", "teams", "messages", "collaboration", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_user_chats",
                "List a user's Teams chats.",
                ListUserChatsArgs,
                self._handlers.list_user_chats,
                domain=self.metadata.name,
                tags=("chats", "teams", "read"),
            ),
            _tool(
                "list_chat_messages",
                "List the messages in a Teams chat.",
                ListChatMessagesArgs,
                self._handlers.list_chat_messages,
                domain=self.metadata.name,
                tags=("chats", "teams", "messages", "read"),
            ),
            _tool(
                "send_chat_message",
                "Send a message to a Teams chat.",
                SendChatMessageArgs,
                self._handlers.send_chat_message,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("chats", "teams", "message", "send", "mutation"),
            ),
            _tool(
                "create_chat",
                "Create a Teams chat (oneOnOne or group).",
                CreateChatArgs,
                self._handlers.create_chat,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("chats", "teams", "create", "mutation"),
            ),
        ]


class SharePointSitesDomain(GraphDomain):
    metadata = DomainMetadata(
        name="sharepoint_sites",
        display_name="SharePoint Sites",
        description=(
            "SharePoint sites: list and inspect sites, list a site's lists and list items, "
            "and create a new list item."
        ),
        required_permissions=(
            "Sites.Read.All",
            "Sites.ReadWrite.All",
        ),
        tags=("sharepoint", "sites", "lists", "documents", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_sites",
                "List SharePoint sites.",
                ListSitesArgs,
                self._handlers.list_sites,
                domain=self.metadata.name,
                tags=("sharepoint", "sites", "read"),
            ),
            _tool(
                "get_site",
                "Get a SharePoint site by ID.",
                GetSiteArgs,
                self._handlers.get_site,
                domain=self.metadata.name,
                tags=("sharepoint", "site", "read"),
            ),
            _tool(
                "list_site_lists",
                "List the lists in a SharePoint site.",
                ListSiteListsArgs,
                self._handlers.list_site_lists,
                domain=self.metadata.name,
                tags=("sharepoint", "lists", "read"),
            ),
            _tool(
                "list_list_items",
                "List the items in a SharePoint list.",
                ListListItemsArgs,
                self._handlers.list_list_items,
                domain=self.metadata.name,
                tags=("sharepoint", "list", "items", "read"),
            ),
            _tool(
                "create_list_item",
                "Create an item in a SharePoint list.",
                CreateListItemArgs,
                self._handlers.create_list_item,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("sharepoint", "list", "item", "create", "mutation"),
            ),
            _tool(
                "update_list_item",
                "Update fields on a SharePoint list item.",
                UpdateListItemArgs,
                self._handlers.update_list_item,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("sharepoint", "list", "item", "update", "mutation"),
            ),
            _tool(
                "delete_list_item",
                "Delete a SharePoint list item (destructive).",
                DeleteListItemArgs,
                self._handlers.delete_list_item,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("sharepoint", "list", "item", "delete", "destructive"),
            ),
        ]


class OneNoteDomain(GraphDomain):
    metadata = DomainMetadata(
        name="onenote",
        display_name="OneNote",
        description=(
            "Microsoft OneNote: list a user's notebooks, the sections in a notebook, and the "
            "pages in a section. Read-only."
        ),
        required_permissions=("Notes.Read.All",),
        tags=("onenote", "notebooks", "notes", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_notebooks",
                "List a user's OneNote notebooks.",
                ListNotebooksArgs,
                self._handlers.list_notebooks,
                domain=self.metadata.name,
                tags=("onenote", "notebooks", "read"),
            ),
            _tool(
                "list_notebook_sections",
                "List the sections in a OneNote notebook.",
                ListNotebookSectionsArgs,
                self._handlers.list_notebook_sections,
                domain=self.metadata.name,
                tags=("onenote", "sections", "read"),
            ),
            _tool(
                "list_section_pages",
                "List the pages in a OneNote section.",
                ListSectionPagesArgs,
                self._handlers.list_section_pages,
                domain=self.metadata.name,
                tags=("onenote", "pages", "read"),
            ),
        ]


class ContactsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="contacts",
        display_name="Contacts",
        description=(
            "Microsoft 365 personal contacts: list and read a user's contacts and create a "
            "new contact."
        ),
        required_permissions=(
            "Contacts.Read",
            "Contacts.ReadWrite",
        ),
        tags=("contacts", "outlook", "people", "address book", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_contacts",
                "List a user's contacts.",
                ListContactsArgs,
                self._handlers.list_contacts,
                domain=self.metadata.name,
                tags=("contacts", "people", "read"),
            ),
            _tool(
                "get_contact",
                "Get a single contact by ID.",
                GetContactArgs,
                self._handlers.get_contact,
                domain=self.metadata.name,
                tags=("contacts", "contact", "read"),
            ),
            _tool(
                "create_contact",
                "Create a contact for a user.",
                CreateContactArgs,
                self._handlers.create_contact,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("contacts", "contact", "create", "mutation"),
            ),
            _tool(
                "update_contact",
                "Update a contact's name or email.",
                UpdateContactArgs,
                self._handlers.update_contact,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("contacts", "contact", "update", "mutation"),
            ),
            _tool(
                "delete_contact",
                "Delete a contact (destructive).",
                DeleteContactArgs,
                self._handlers.delete_contact,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("contacts", "contact", "delete", "destructive"),
            ),
        ]


class PlannerDomain(GraphDomain):
    metadata = DomainMetadata(
        name="planner",
        display_name="Planner",
        description=(
            "Microsoft Planner: list a group's plans, inspect a plan and its tasks, and create "
            "a new Planner task."
        ),
        required_permissions=(
            "Tasks.Read.All",
            "Tasks.ReadWrite.All",
            "Group.Read.All",
        ),
        tags=("planner", "plans", "tasks", "buckets", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_group_plans",
                "List the Planner plans owned by a group.",
                ListGroupPlansArgs,
                self._handlers.list_group_plans,
                domain=self.metadata.name,
                tags=("planner", "plans", "read"),
            ),
            _tool(
                "get_plan",
                "Get a Planner plan by ID.",
                GetPlanArgs,
                self._handlers.get_plan,
                domain=self.metadata.name,
                tags=("planner", "plan", "read"),
            ),
            _tool(
                "list_plan_tasks",
                "List the tasks in a Planner plan.",
                ListPlanTasksArgs,
                self._handlers.list_plan_tasks,
                domain=self.metadata.name,
                tags=("planner", "tasks", "read"),
            ),
            _tool(
                "create_planner_task",
                "Create a Planner task.",
                CreatePlannerTaskArgs,
                self._handlers.create_planner_task,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("planner", "task", "create", "mutation"),
            ),
            _tool(
                "update_planner_task",
                "Update a Planner task (e.g. mark complete via percentComplete=100).",
                UpdatePlannerTaskArgs,
                self._handlers.update_planner_task,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("planner", "task", "update", "mutation"),
            ),
            _tool(
                "delete_planner_task",
                "Delete a Planner task (destructive).",
                DeletePlannerTaskArgs,
                self._handlers.delete_planner_task,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("planner", "task", "delete", "destructive"),
            ),
        ]


class TodoDomain(GraphDomain):
    metadata = DomainMetadata(
        name="todo",
        display_name="To Do",
        description=(
            "Microsoft To Do: list a user's task lists and the tasks in a list, and create a "
            "new task."
        ),
        required_permissions=(
            "Tasks.Read",
            "Tasks.ReadWrite",
        ),
        tags=("todo", "to do", "tasks", "lists", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_todo_lists",
                "List a user's To Do lists.",
                ListTodoListsArgs,
                self._handlers.list_todo_lists,
                domain=self.metadata.name,
                tags=("todo", "lists", "read"),
            ),
            _tool(
                "list_todo_tasks",
                "List the tasks in a To Do list.",
                ListTodoTasksArgs,
                self._handlers.list_todo_tasks,
                domain=self.metadata.name,
                tags=("todo", "tasks", "read"),
            ),
            _tool(
                "create_todo_task",
                "Create a To Do task.",
                CreateTodoTaskArgs,
                self._handlers.create_todo_task,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("todo", "task", "create", "mutation"),
            ),
            _tool(
                "update_todo_task",
                "Update a To Do task (e.g. mark completed).",
                UpdateTodoTaskArgs,
                self._handlers.update_todo_task,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("todo", "task", "update", "mutation"),
            ),
            _tool(
                "delete_todo_task",
                "Delete a To Do task (destructive).",
                DeleteTodoTaskArgs,
                self._handlers.delete_todo_task,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("todo", "task", "delete", "destructive"),
            ),
        ]


class UsageReportsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="usage_reports",
        display_name="Usage Reports",
        description=(
            "Microsoft 365 usage reports: Teams user activity, email activity, and Office 365 "
            "active users over a selectable reporting period. Read-only."
        ),
        required_permissions=("Reports.Read.All",),
        tags=("reports", "usage", "activity", "analytics", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "get_teams_user_activity_counts",
                "Get Microsoft Teams user activity counts for a reporting period.",
                ReportPeriodArgs,
                self._handlers.get_teams_user_activity_counts,
                domain=self.metadata.name,
                tags=("reports", "teams", "activity", "read"),
            ),
            _tool(
                "get_email_activity_counts",
                "Get email activity counts for a reporting period.",
                ReportPeriodArgs,
                self._handlers.get_email_activity_counts,
                domain=self.metadata.name,
                tags=("reports", "email", "activity", "read"),
            ),
            _tool(
                "get_office365_active_users",
                "Get Office 365 active user detail for a reporting period.",
                ReportPeriodArgs,
                self._handlers.get_office365_active_users,
                domain=self.metadata.name,
                tags=("reports", "office365", "active users", "read"),
            ),
        ]


class ServiceHealthDomain(GraphDomain):
    metadata = DomainMetadata(
        name="service_health",
        display_name="Service Health",
        description=(
            "Microsoft 365 service health: service health overviews, service issues, and "
            "service announcement messages. Read-only."
        ),
        required_permissions=(
            "ServiceHealth.Read.All",
            "ServiceMessage.Read.All",
        ),
        tags=("service health", "health", "issues", "announcements", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_service_health_overviews",
                "List Microsoft 365 service health overviews.",
                PaginationArgs,
                self._handlers.list_service_health_overviews,
                domain=self.metadata.name,
                tags=("service health", "health", "overview", "read"),
            ),
            _tool(
                "list_service_health_issues",
                "List Microsoft 365 service health issues.",
                PaginationArgs,
                self._handlers.list_service_health_issues,
                domain=self.metadata.name,
                tags=("service health", "issues", "incidents", "read"),
            ),
            _tool(
                "list_service_messages",
                "List Microsoft 365 service announcement messages.",
                PaginationArgs,
                self._handlers.list_service_messages,
                domain=self.metadata.name,
                tags=("service health", "messages", "announcements", "read"),
            ),
        ]


class SecureScoreDomain(GraphDomain):
    metadata = DomainMetadata(
        name="secure_score",
        display_name="Secure Score",
        description=(
            "Microsoft Secure Score: list secure score snapshots and the control profiles that "
            "describe each improvement action, and update a control's review state."
        ),
        required_permissions=(
            "SecurityEvents.Read.All",
            "SecurityEvents.ReadWrite.All",
        ),
        tags=("secure score", "security", "posture", "controls", "compliance"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_secure_scores",
                "List Microsoft Secure Score snapshots.",
                PaginationArgs,
                self._handlers.list_secure_scores,
                domain=self.metadata.name,
                tags=("secure score", "posture", "read"),
            ),
            _tool(
                "list_secure_score_control_profiles",
                "List Secure Score control profiles (improvement actions).",
                PaginationArgs,
                self._handlers.list_secure_score_control_profiles,
                domain=self.metadata.name,
                tags=("secure score", "controls", "read"),
            ),
            _tool(
                "update_secure_score_control_state",
                "Update the review state of a Secure Score control profile.",
                UpdateSecureScoreControlStateArgs,
                self._handlers.update_secure_score_control_state,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("secure score", "control", "update", "mutation"),
            ),
        ]


class EdiscoveryDomain(GraphDomain):
    metadata = DomainMetadata(
        name="ediscovery",
        display_name="eDiscovery",
        description=(
            "Microsoft Purview eDiscovery: list and inspect eDiscovery cases, list a case's "
            "custodians, and close a case."
        ),
        required_permissions=(
            "eDiscovery.Read.All",
            "eDiscovery.ReadWrite.All",
        ),
        tags=("ediscovery", "purview", "compliance", "legal", "cases"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_ediscovery_cases",
                "List Microsoft Purview eDiscovery cases.",
                PaginationArgs,
                self._handlers.list_ediscovery_cases,
                domain=self.metadata.name,
                tags=("ediscovery", "cases", "read"),
            ),
            _tool(
                "get_ediscovery_case",
                "Get an eDiscovery case by ID.",
                GetEdiscoveryCaseArgs,
                self._handlers.get_ediscovery_case,
                domain=self.metadata.name,
                tags=("ediscovery", "case", "read"),
            ),
            _tool(
                "list_ediscovery_custodians",
                "List the custodians on an eDiscovery case.",
                ListEdiscoveryCustodiansArgs,
                self._handlers.list_ediscovery_custodians,
                domain=self.metadata.name,
                tags=("ediscovery", "custodians", "read"),
            ),
            _tool(
                "create_ediscovery_case",
                "Create a new eDiscovery case.",
                CreateEdiscoveryCaseArgs,
                self._handlers.create_ediscovery_case,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("ediscovery", "case", "create", "mutation"),
            ),
            _tool(
                "add_ediscovery_custodian",
                "Add a custodian to an eDiscovery case.",
                AddEdiscoveryCustodianArgs,
                self._handlers.add_ediscovery_custodian,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("ediscovery", "custodian", "add", "mutation"),
            ),
            _tool(
                "close_ediscovery_case",
                "Close an eDiscovery case.",
                CloseEdiscoveryCaseArgs,
                self._handlers.close_ediscovery_case,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("ediscovery", "case", "close", "mutation"),
            ),
        ]


class InformationProtectionDomain(GraphDomain):
    metadata = DomainMetadata(
        name="information_protection",
        display_name="Information Protection",
        description=(
            "Microsoft Purview Information Protection: list and inspect sensitivity labels and "
            "read label policy settings. Read-only."
        ),
        required_permissions=("InformationProtectionPolicy.Read.All",),
        tags=("information protection", "sensitivity labels", "dlp", "purview", "compliance"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_sensitivity_labels",
                "List Microsoft Purview sensitivity labels.",
                PaginationArgs,
                self._handlers.list_sensitivity_labels,
                domain=self.metadata.name,
                tags=("information protection", "labels", "read"),
            ),
            _tool(
                "get_sensitivity_label",
                "Get a sensitivity label by ID.",
                GetSensitivityLabelArgs,
                self._handlers.get_sensitivity_label,
                domain=self.metadata.name,
                tags=("information protection", "label", "read"),
            ),
            _tool(
                "list_label_policy_settings",
                "Read sensitivity label policy settings.",
                EmptyArgs,
                self._handlers.list_label_policy_settings,
                domain=self.metadata.name,
                tags=("information protection", "policy", "read"),
            ),
            _tool(
                "extract_sensitivity_labels",
                "Extract the sensitivity labels applied to a drive item.",
                ExtractSensitivityLabelsArgs,
                self._handlers.extract_sensitivity_labels,
                domain=self.metadata.name,
                tags=("information protection", "labels", "driveitem", "read"),
            ),
        ]


class ThreatIntelligenceDomain(GraphDomain):
    metadata = DomainMetadata(
        name="threat_intelligence",
        display_name="Threat Intelligence",
        description=(
            "Microsoft Defender Threat Intelligence: list intel articles and profiles and look up "
            "hosts and vulnerabilities. Read-only."
        ),
        required_permissions=("ThreatIntelligence.Read.All",),
        tags=("threat intelligence", "defender", "tip", "security", "iocs"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_threat_intelligence_articles",
                "List Microsoft Defender Threat Intelligence articles.",
                PaginationArgs,
                self._handlers.list_threat_intelligence_articles,
                domain=self.metadata.name,
                tags=("threat intelligence", "articles", "read"),
            ),
            _tool(
                "list_intel_profiles",
                "List threat intelligence (threat actor) profiles.",
                PaginationArgs,
                self._handlers.list_intel_profiles,
                domain=self.metadata.name,
                tags=("threat intelligence", "profiles", "read"),
            ),
            _tool(
                "get_threat_intelligence_host",
                "Look up a host (hostname or IP) in threat intelligence.",
                GetThreatIntelHostArgs,
                self._handlers.get_threat_intelligence_host,
                domain=self.metadata.name,
                tags=("threat intelligence", "host", "read"),
            ),
            _tool(
                "get_vulnerability",
                "Look up a vulnerability (e.g. a CVE) in threat intelligence.",
                GetVulnerabilityArgs,
                self._handlers.get_vulnerability,
                domain=self.metadata.name,
                tags=("threat intelligence", "vulnerability", "cve", "read"),
            ),
        ]


class OnlineMeetingsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="online_meetings",
        display_name="Online Meetings",
        description=(
            "Microsoft Teams online meetings: get a meeting, list its attendance reports, and "
            "create a new online meeting."
        ),
        required_permissions=(
            "OnlineMeetings.Read",
            "OnlineMeetings.ReadWrite",
            "OnlineMeetingArtifact.Read.All",
        ),
        tags=("online meetings", "teams", "meetings", "attendance", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "get_online_meeting",
                "Get a user's online meeting by ID.",
                GetOnlineMeetingArgs,
                self._handlers.get_online_meeting,
                domain=self.metadata.name,
                tags=("online meetings", "meeting", "read"),
            ),
            _tool(
                "list_meeting_attendance_reports",
                "List an online meeting's attendance reports.",
                ListAttendanceReportsArgs,
                self._handlers.list_meeting_attendance_reports,
                domain=self.metadata.name,
                tags=("online meetings", "attendance", "read"),
            ),
            _tool(
                "create_online_meeting",
                "Create an online meeting for a user.",
                CreateOnlineMeetingArgs,
                self._handlers.create_online_meeting,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("online meetings", "meeting", "create", "mutation"),
            ),
        ]


class BookingsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="bookings",
        display_name="Bookings",
        description=(
            "Microsoft Bookings: list booking businesses, inspect a business and its services, "
            "list appointments, and create a new appointment."
        ),
        required_permissions=(
            "Bookings.Read.All",
            "BookingsAppointment.ReadWrite.All",
        ),
        tags=("bookings", "appointments", "scheduling", "services", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_booking_businesses",
                "List Microsoft Bookings businesses.",
                PaginationArgs,
                self._handlers.list_booking_businesses,
                domain=self.metadata.name,
                tags=("bookings", "businesses", "read"),
            ),
            _tool(
                "get_booking_business",
                "Get a Bookings business by ID.",
                GetBookingBusinessArgs,
                self._handlers.get_booking_business,
                domain=self.metadata.name,
                tags=("bookings", "business", "read"),
            ),
            _tool(
                "list_booking_services",
                "List the services offered by a Bookings business.",
                ListBookingServicesArgs,
                self._handlers.list_booking_services,
                domain=self.metadata.name,
                tags=("bookings", "services", "read"),
            ),
            _tool(
                "list_booking_appointments",
                "List the appointments of a Bookings business.",
                ListBookingAppointmentsArgs,
                self._handlers.list_booking_appointments,
                domain=self.metadata.name,
                tags=("bookings", "appointments", "read"),
            ),
            _tool(
                "create_booking_appointment",
                "Create an appointment for a Bookings business.",
                CreateBookingAppointmentArgs,
                self._handlers.create_booking_appointment,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("bookings", "appointment", "create", "mutation"),
            ),
            _tool(
                "cancel_booking_appointment",
                "Cancel a Bookings appointment.",
                CancelBookingAppointmentArgs,
                self._handlers.cancel_booking_appointment,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("bookings", "appointment", "cancel", "mutation"),
            ),
        ]


class SearchDomain(GraphDomain):
    metadata = DomainMetadata(
        name="search",
        display_name="Search",
        description=(
            "Microsoft Search API: run a query across entity types such as messages, events, "
            "drive items, sites, and chat messages. Read-only."
        ),
        required_permissions=(
            "Mail.Read",
            "Files.Read.All",
            "Sites.Read.All",
        ),
        tags=("search", "query", "kql", "discovery", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "search_query",
                "Run a Microsoft Search query across one or more entity types.",
                SearchQueryArgs,
                self._handlers.search_query,
                domain=self.metadata.name,
                tags=("search", "query", "read"),
            ),
        ]


class UniversalPrintDomain(GraphDomain):
    metadata = DomainMetadata(
        name="universal_print",
        display_name="Universal Print",
        description=(
            "Microsoft Universal Print: list printers and printer shares, inspect a printer's "
            "queued jobs, and cancel a print job."
        ),
        required_permissions=(
            "Printer.Read.All",
            "PrintJob.ReadWriteBasic.All",
        ),
        tags=("universal print", "printers", "print jobs", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_printers",
                "List Universal Print printers.",
                PaginationArgs,
                self._handlers.list_printers,
                domain=self.metadata.name,
                tags=("universal print", "printers", "read"),
            ),
            _tool(
                "get_printer",
                "Get a Universal Print printer by ID.",
                GetPrinterArgs,
                self._handlers.get_printer,
                domain=self.metadata.name,
                tags=("universal print", "printer", "read"),
            ),
            _tool(
                "list_printer_shares",
                "List Universal Print printer shares.",
                PaginationArgs,
                self._handlers.list_printer_shares,
                domain=self.metadata.name,
                tags=("universal print", "shares", "read"),
            ),
            _tool(
                "list_print_jobs",
                "List the jobs queued on a Universal Print printer.",
                ListPrintJobsArgs,
                self._handlers.list_print_jobs,
                domain=self.metadata.name,
                tags=("universal print", "jobs", "read"),
            ),
            _tool(
                "cancel_print_job",
                "Cancel a queued print job.",
                CancelPrintJobArgs,
                self._handlers.cancel_print_job,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("universal print", "job", "cancel", "mutation"),
            ),
        ]


class EducationDomain(GraphDomain):
    metadata = DomainMetadata(
        name="education",
        display_name="Education",
        description=(
            "Microsoft Education (EDU tenants): list schools and classes, inspect a class's "
            "members and assignments, and read EDU users. Read-only."
        ),
        required_permissions=(
            "EduRoster.Read.All",
            "EduAssignments.Read.All",
        ),
        tags=("education", "edu", "schools", "classes", "assignments"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_education_schools",
                "List Education schools in the tenant.",
                PaginationArgs,
                self._handlers.list_education_schools,
                domain=self.metadata.name,
                tags=("education", "schools", "read"),
            ),
            _tool(
                "list_education_classes",
                "List Education classes in the tenant.",
                PaginationArgs,
                self._handlers.list_education_classes,
                domain=self.metadata.name,
                tags=("education", "classes", "read"),
            ),
            _tool(
                "list_class_members",
                "List the members of an Education class.",
                ListClassMembersArgs,
                self._handlers.list_class_members,
                domain=self.metadata.name,
                tags=("education", "class", "members", "read"),
            ),
            _tool(
                "list_education_assignments",
                "List the assignments of an Education class.",
                ListClassAssignmentsArgs,
                self._handlers.list_education_assignments,
                domain=self.metadata.name,
                tags=("education", "class", "assignments", "read"),
            ),
            _tool(
                "get_education_user",
                "Get an Education user by ID or userPrincipalName.",
                GetEducationUserArgs,
                self._handlers.get_education_user,
                domain=self.metadata.name,
                tags=("education", "user", "read"),
            ),
        ]


class CloudPcDomain(GraphDomain):
    metadata = DomainMetadata(
        name="cloud_pc",
        display_name="Cloud PC (Windows 365)",
        description=(
            "Windows 365 Cloud PCs: list and get Cloud PCs, list provisioning policies, and "
            "trigger reboot or reprovision actions on a Cloud PC."
        ),
        required_permissions=(
            "CloudPC.Read.All",
            "CloudPC.ReadWrite.All",
        ),
        tags=("cloud pc", "windows 365", "endpoint", "virtual desktop"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_cloud_pcs",
                "List Windows 365 Cloud PCs.",
                PaginationArgs,
                self._handlers.list_cloud_pcs,
                domain=self.metadata.name,
                tags=("cloud pc", "list", "read"),
            ),
            _tool(
                "get_cloud_pc",
                "Get a Windows 365 Cloud PC by ID.",
                GetCloudPcArgs,
                self._handlers.get_cloud_pc,
                domain=self.metadata.name,
                tags=("cloud pc", "get", "read"),
            ),
            _tool(
                "list_cloud_pc_provisioning_policies",
                "List Cloud PC provisioning policies.",
                PaginationArgs,
                self._handlers.list_cloud_pc_provisioning_policies,
                domain=self.metadata.name,
                tags=("cloud pc", "provisioning", "policies", "read"),
            ),
            _tool(
                "reboot_cloud_pc",
                "Reboot a Cloud PC.",
                RebootCloudPcArgs,
                self._handlers.reboot_cloud_pc,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("cloud pc", "reboot", "mutation"),
            ),
            _tool(
                "reprovision_cloud_pc",
                "Reprovision a Cloud PC (destructive — resets the device).",
                ReprovisionCloudPcArgs,
                self._handlers.reprovision_cloud_pc,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("cloud pc", "reprovision", "destructive"),
            ),
        ]


class VivaDomain(GraphDomain):
    metadata = DomainMetadata(
        name="viva",
        display_name="Viva",
        description=(
            "Microsoft Viva employee experience: list Viva Engage communities, list learning "
            "course activities, and list learning providers. Read-only."
        ),
        required_permissions=(
            "Community.Read.All",
            "LearningContent.Read.All",
            "LearningAssignedCourse.Read",
        ),
        tags=("viva", "engage", "learning", "employee experience", "m365"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_engage_communities",
                "List Viva Engage communities.",
                PaginationArgs,
                self._handlers.list_engage_communities,
                domain=self.metadata.name,
                tags=("viva", "engage", "communities", "read"),
            ),
            _tool(
                "get_engage_community",
                "Get a Viva Engage community by ID.",
                GetEngageCommunityArgs,
                self._handlers.get_engage_community,
                domain=self.metadata.name,
                tags=("viva", "engage", "community", "read"),
            ),
            _tool(
                "list_learning_course_activities",
                "List Viva Learning course activities for the tenant.",
                PaginationArgs,
                self._handlers.list_learning_course_activities,
                domain=self.metadata.name,
                tags=("viva", "learning", "courses", "read"),
            ),
            _tool(
                "list_learning_providers",
                "List Viva Learning content providers.",
                PaginationArgs,
                self._handlers.list_learning_providers,
                domain=self.metadata.name,
                tags=("viva", "learning", "providers", "read"),
            ),
        ]


class PlacesDomain(GraphDomain):
    metadata = DomainMetadata(
        name="places",
        display_name="Places",
        description=(
            "Microsoft Places: list places, rooms, room lists, and workspaces (desks). "
            "Read-only."
        ),
        required_permissions=("Place.Read.All",),
        tags=("places", "rooms", "desks", "workspaces", "facilities"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_places",
                "List Microsoft Places (rooms, workspaces, and room lists).",
                PaginationArgs,
                self._handlers.list_places,
                domain=self.metadata.name,
                tags=("places", "list", "read"),
            ),
            _tool(
                "list_rooms",
                "List Microsoft Places rooms.",
                PaginationArgs,
                self._handlers.list_rooms,
                domain=self.metadata.name,
                tags=("places", "rooms", "read"),
            ),
            _tool(
                "list_room_lists",
                "List Microsoft Places room lists.",
                PaginationArgs,
                self._handlers.list_room_lists,
                domain=self.metadata.name,
                tags=("places", "room lists", "read"),
            ),
            _tool(
                "list_workspaces",
                "List Microsoft Places workspaces (desks and shared spaces).",
                PaginationArgs,
                self._handlers.list_workspaces,
                domain=self.metadata.name,
                tags=("places", "workspaces", "desks", "read"),
            ),
        ]


class ChangeNotificationsDomain(GraphDomain):
    metadata = DomainMetadata(
        name="change_notifications",
        display_name="Change Notifications",
        description=(
            "Microsoft Graph change notifications (webhooks): list and inspect subscriptions, "
            "create new subscriptions, renew them, and delete them."
        ),
        required_permissions=(),
        tags=("change notifications", "webhooks", "subscriptions", "infrastructure"),
    )

    def __init__(self, handlers: Any) -> None:
        self._handlers = handlers

    def tools(self) -> list[ToolDefinition]:
        return [
            _tool(
                "list_subscriptions",
                "List Microsoft Graph change-notification subscriptions.",
                PaginationArgs,
                self._handlers.list_subscriptions,
                domain=self.metadata.name,
                tags=("change notifications", "subscriptions", "read"),
            ),
            _tool(
                "get_subscription",
                "Get a change-notification subscription by ID.",
                GetSubscriptionArgs,
                self._handlers.get_subscription,
                domain=self.metadata.name,
                tags=("change notifications", "subscription", "read"),
            ),
            _tool(
                "create_subscription",
                "Create a change-notification subscription (webhook).",
                CreateSubscriptionArgs,
                self._handlers.create_subscription,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("change notifications", "subscription", "create", "mutation"),
            ),
            _tool(
                "renew_subscription",
                "Extend the expiration of a change-notification subscription.",
                RenewSubscriptionArgs,
                self._handlers.renew_subscription,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="mutation",
                tags=("change notifications", "subscription", "renew", "mutation"),
            ),
            _tool(
                "delete_subscription",
                "Delete a change-notification subscription.",
                DeleteSubscriptionArgs,
                self._handlers.delete_subscription,
                read_only=False,
                requires_confirmation=True,
                domain=self.metadata.name,
                safety="destructive",
                tags=("change notifications", "subscription", "delete", "destructive"),
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
            LifecycleWorkflowsDomain(self),
            AdministrativeUnitsDomain(self),
            B2BCollaborationDomain(self),
            MailDomain(self),
            CalendarDomain(self),
            TeamsDomain(self),
            FilesDomain(self),
            DeviceManagementDomain(self),
            ChatsDomain(self),
            SharePointSitesDomain(self),
            OneNoteDomain(self),
            ContactsDomain(self),
            PlannerDomain(self),
            TodoDomain(self),
            UsageReportsDomain(self),
            ServiceHealthDomain(self),
            SecureScoreDomain(self),
            EdiscoveryDomain(self),
            InformationProtectionDomain(self),
            ThreatIntelligenceDomain(self),
            OnlineMeetingsDomain(self),
            BookingsDomain(self),
            SearchDomain(self),
            UniversalPrintDomain(self),
            EducationDomain(self),
            CloudPcDomain(self),
            VivaDomain(self),
            PlacesDomain(self),
            ChangeNotificationsDomain(self),
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

    async def list_messages(self, args: ListMessagesArgs) -> Any:
        return await self._client.request_collection(
            f"/users/{args.user_id}/messages",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_message(self, args: GetMessageArgs) -> Any:
        return await self._client.request(
            "GET", f"/users/{args.user_id}/messages/{args.message_id}"
        )

    async def list_mail_folders(self, args: ListMailFoldersArgs) -> Any:
        return await self._client.request_collection(f"/users/{args.user_id}/mailFolders")

    async def send_mail(self, args: SendMailArgs) -> Any:
        message = {
            "subject": args.subject,
            "body": {"contentType": "Text", "content": args.body},
            "toRecipients": [
                {"emailAddress": {"address": address}} for address in args.to_recipients
            ],
        }
        return await self._client.request(
            "POST", f"/users/{args.user_id}/sendMail", json_data={"message": message}
        )

    async def list_events(self, args: ListEventsArgs) -> Any:
        return await self._client.request_collection(
            f"/users/{args.user_id}/events",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_event(self, args: GetEventArgs) -> Any:
        return await self._client.request("GET", f"/users/{args.user_id}/events/{args.event_id}")

    async def create_event(self, args: CreateEventArgs) -> Any:
        body: dict[str, Any] = {
            "subject": args.subject,
            "start": {"dateTime": args.start_datetime, "timeZone": args.time_zone},
            "end": {"dateTime": args.end_datetime, "timeZone": args.time_zone},
        }
        if args.attendees:
            body["attendees"] = [
                {"emailAddress": {"address": address}, "type": "required"}
                for address in args.attendees
            ]
        return await self._client.request("POST", f"/users/{args.user_id}/events", json_data=body)

    async def cancel_event(self, args: CancelEventArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/users/{args.user_id}/events/{args.event_id}/cancel",
            json_data={"comment": args.comment},
        )

    async def list_joined_teams(self, args: ListJoinedTeamsArgs) -> Any:
        return await self._client.request_collection(f"/users/{args.user_id}/joinedTeams")

    async def list_channels(self, args: ListChannelsArgs) -> Any:
        return await self._client.request_collection(f"/teams/{args.team_id}/channels")

    async def list_channel_messages(self, args: ListChannelMessagesArgs) -> Any:
        return await self._client.request_collection(
            f"/teams/{args.team_id}/channels/{args.channel_id}/messages"
        )

    async def send_channel_message(self, args: SendChannelMessageArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/teams/{args.team_id}/channels/{args.channel_id}/messages",
            json_data={"body": {"content": args.content}},
        )

    async def list_drive_items(self, args: ListDriveItemsArgs) -> Any:
        return await self._client.request_collection(
            f"/users/{args.user_id}/drive/root/children",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_drive_item(self, args: GetDriveItemArgs) -> Any:
        return await self._client.request(
            "GET", f"/users/{args.user_id}/drive/items/{args.item_id}"
        )

    async def search_drive(self, args: SearchDriveArgs) -> Any:
        escaped = _escape_odata_string(args.query)
        return await self._client.request_collection(
            f"/users/{args.user_id}/drive/root/search(q='{escaped}')"
        )

    async def create_sharing_link(self, args: CreateSharingLinkArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/users/{args.user_id}/drive/items/{args.item_id}/createLink",
            json_data={"type": args.link_type, "scope": args.scope},
        )

    async def list_managed_devices(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/deviceManagement/managedDevices",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_managed_device(self, args: GetManagedDeviceArgs) -> Any:
        return await self._client.request(
            "GET", f"/deviceManagement/managedDevices/{args.device_id}"
        )

    async def list_device_compliance_policies(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/deviceManagement/deviceCompliancePolicies",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_device_configurations(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/deviceManagement/deviceConfigurations",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def wipe_managed_device(self, args: WipeManagedDeviceArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/deviceManagement/managedDevices/{args.device_id}/wipe",
            json_data=args.body or {},
        )

    async def retire_managed_device(self, args: RetireManagedDeviceArgs) -> Any:
        return await self._client.request(
            "POST", f"/deviceManagement/managedDevices/{args.device_id}/retire"
        )

    async def sync_managed_device(self, args: SyncManagedDeviceArgs) -> Any:
        return await self._client.request(
            "POST", f"/deviceManagement/managedDevices/{args.device_id}/syncDevice"
        )

    async def list_user_chats(self, args: ListUserChatsArgs) -> Any:
        return await self._client.request_collection(
            f"/users/{args.user_id}/chats",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_chat_messages(self, args: ListChatMessagesArgs) -> Any:
        return await self._client.request_collection(
            f"/chats/{args.chat_id}/messages",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def send_chat_message(self, args: SendChatMessageArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/chats/{args.chat_id}/messages",
            json_data={"body": {"content": args.content}},
        )

    async def list_sites(self, args: ListSitesArgs) -> Any:
        return await self._client.request_collection(
            "/sites",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_site(self, args: GetSiteArgs) -> Any:
        return await self._client.request("GET", f"/sites/{args.site_id}")

    async def list_site_lists(self, args: ListSiteListsArgs) -> Any:
        return await self._client.request_collection(f"/sites/{args.site_id}/lists")

    async def list_list_items(self, args: ListListItemsArgs) -> Any:
        return await self._client.request_collection(
            f"/sites/{args.site_id}/lists/{args.list_id}/items"
        )

    async def create_list_item(self, args: CreateListItemArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/sites/{args.site_id}/lists/{args.list_id}/items",
            json_data={"fields": args.fields},
        )

    async def list_notebooks(self, args: ListNotebooksArgs) -> Any:
        return await self._client.request_collection(f"/users/{args.user_id}/onenote/notebooks")

    async def list_notebook_sections(self, args: ListNotebookSectionsArgs) -> Any:
        return await self._client.request_collection(
            f"/users/{args.user_id}/onenote/notebooks/{args.notebook_id}/sections"
        )

    async def list_section_pages(self, args: ListSectionPagesArgs) -> Any:
        return await self._client.request_collection(
            f"/users/{args.user_id}/onenote/sections/{args.section_id}/pages"
        )

    async def list_contacts(self, args: ListContactsArgs) -> Any:
        return await self._client.request_collection(
            f"/users/{args.user_id}/contacts",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_contact(self, args: GetContactArgs) -> Any:
        return await self._client.request(
            "GET", f"/users/{args.user_id}/contacts/{args.contact_id}"
        )

    async def create_contact(self, args: CreateContactArgs) -> Any:
        body = {
            "givenName": args.given_name,
            "surname": args.surname,
            "emailAddresses": [
                {"address": args.email, "name": f"{args.given_name} {args.surname}"}
            ],
        }
        return await self._client.request(
            "POST", f"/users/{args.user_id}/contacts", json_data=body
        )

    async def list_group_plans(self, args: ListGroupPlansArgs) -> Any:
        return await self._client.request_collection(f"/groups/{args.group_id}/planner/plans")

    async def get_plan(self, args: GetPlanArgs) -> Any:
        return await self._client.request("GET", f"/planner/plans/{args.plan_id}")

    async def list_plan_tasks(self, args: ListPlanTasksArgs) -> Any:
        return await self._client.request_collection(f"/planner/plans/{args.plan_id}/tasks")

    async def create_planner_task(self, args: CreatePlannerTaskArgs) -> Any:
        body: dict[str, Any] = {"planId": args.plan_id, "title": args.title}
        if args.bucket_id:
            body["bucketId"] = args.bucket_id
        return await self._client.request("POST", "/planner/tasks", json_data=body)

    async def list_todo_lists(self, args: ListTodoListsArgs) -> Any:
        return await self._client.request_collection(f"/users/{args.user_id}/todo/lists")

    async def list_todo_tasks(self, args: ListTodoTasksArgs) -> Any:
        return await self._client.request_collection(
            f"/users/{args.user_id}/todo/lists/{args.list_id}/tasks"
        )

    async def create_todo_task(self, args: CreateTodoTaskArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/users/{args.user_id}/todo/lists/{args.list_id}/tasks",
            json_data={"title": args.title},
        )

    async def get_teams_user_activity_counts(self, args: ReportPeriodArgs) -> Any:
        # Real Graph returns CSV for report functions; the mock returns a JSON
        # placeholder, an accepted fidelity tradeoff for this JSON-only client.
        return await self._client.request(
            "GET", f"/reports/getTeamsUserActivityCounts(period='{args.period}')"
        )

    async def get_email_activity_counts(self, args: ReportPeriodArgs) -> Any:
        return await self._client.request(
            "GET", f"/reports/getEmailActivityCounts(period='{args.period}')"
        )

    async def get_office365_active_users(self, args: ReportPeriodArgs) -> Any:
        return await self._client.request(
            "GET", f"/reports/getOffice365ActiveUserDetail(period='{args.period}')"
        )

    async def list_service_health_overviews(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/admin/serviceAnnouncement/healthOverviews",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_service_health_issues(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/admin/serviceAnnouncement/issues",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_service_messages(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/admin/serviceAnnouncement/messages",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_secure_scores(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/security/secureScores",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_secure_score_control_profiles(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/security/secureScoreControlProfiles",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def update_secure_score_control_state(
        self, args: UpdateSecureScoreControlStateArgs
    ) -> Any:
        update: dict[str, Any] = {"state": args.state}
        if args.comment:
            update["comment"] = args.comment
        return await self._client.request(
            "PATCH",
            f"/security/secureScoreControlProfiles/{args.control_id}",
            json_data={"controlStateUpdates": [update]},
        )

    async def list_ediscovery_cases(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/security/cases/ediscoveryCases",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_ediscovery_case(self, args: GetEdiscoveryCaseArgs) -> Any:
        return await self._client.request(
            "GET", f"/security/cases/ediscoveryCases/{args.case_id}"
        )

    async def list_ediscovery_custodians(self, args: ListEdiscoveryCustodiansArgs) -> Any:
        return await self._client.request_collection(
            f"/security/cases/ediscoveryCases/{args.case_id}/custodians"
        )

    async def create_ediscovery_case(self, args: CreateEdiscoveryCaseArgs) -> Any:
        body: dict[str, Any] = {"displayName": args.display_name}
        if args.description:
            body["description"] = args.description
        return await self._client.request(
            "POST", "/security/cases/ediscoveryCases", json_data=body
        )

    async def add_ediscovery_custodian(self, args: AddEdiscoveryCustodianArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/security/cases/ediscoveryCases/{args.case_id}/custodians",
            json_data={"email": args.email},
        )

    async def close_ediscovery_case(self, args: CloseEdiscoveryCaseArgs) -> Any:
        return await self._client.request(
            "POST", f"/security/cases/ediscoveryCases/{args.case_id}/close"
        )

    async def list_sensitivity_labels(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/security/informationProtection/sensitivityLabels",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_sensitivity_label(self, args: GetSensitivityLabelArgs) -> Any:
        return await self._client.request(
            "GET", f"/security/informationProtection/sensitivityLabels/{args.label_id}"
        )

    async def list_label_policy_settings(self, args: EmptyArgs) -> Any:
        return await self._client.request_collection(
            "/security/informationProtection/labelPolicySettings"
        )

    async def extract_sensitivity_labels(self, args: ExtractSensitivityLabelsArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/drives/{args.drive_id}/items/{args.item_id}/extractSensitivityLabels",
        )

    async def list_threat_intelligence_articles(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/security/threatIntelligence/articles",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_intel_profiles(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/security/threatIntelligence/intelProfiles",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_threat_intelligence_host(self, args: GetThreatIntelHostArgs) -> Any:
        return await self._client.request(
            "GET", f"/security/threatIntelligence/hosts/{args.host_id}"
        )

    async def get_vulnerability(self, args: GetVulnerabilityArgs) -> Any:
        return await self._client.request(
            "GET", f"/security/threatIntelligence/vulnerabilities/{args.vulnerability_id}"
        )

    async def get_online_meeting(self, args: GetOnlineMeetingArgs) -> Any:
        return await self._client.request(
            "GET", f"/users/{args.user_id}/onlineMeetings/{args.meeting_id}"
        )

    async def list_meeting_attendance_reports(self, args: ListAttendanceReportsArgs) -> Any:
        return await self._client.request_collection(
            f"/users/{args.user_id}/onlineMeetings/{args.meeting_id}/attendanceReports"
        )

    async def create_online_meeting(self, args: CreateOnlineMeetingArgs) -> Any:
        body = {
            "subject": args.subject,
            "startDateTime": args.start_date_time,
            "endDateTime": args.end_date_time,
        }
        return await self._client.request(
            "POST", f"/users/{args.user_id}/onlineMeetings", json_data=body
        )

    async def list_booking_businesses(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/solutions/bookingBusinesses",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_booking_business(self, args: GetBookingBusinessArgs) -> Any:
        return await self._client.request(
            "GET", f"/solutions/bookingBusinesses/{args.business_id}"
        )

    async def list_booking_services(self, args: ListBookingServicesArgs) -> Any:
        return await self._client.request_collection(
            f"/solutions/bookingBusinesses/{args.business_id}/services"
        )

    async def list_booking_appointments(self, args: ListBookingAppointmentsArgs) -> Any:
        return await self._client.request_collection(
            f"/solutions/bookingBusinesses/{args.business_id}/appointments"
        )

    async def create_booking_appointment(self, args: CreateBookingAppointmentArgs) -> Any:
        body = {
            "serviceId": args.service_id,
            "customerName": args.customer_name,
            "startDateTime": {"dateTime": args.start_date_time, "timeZone": "UTC"},
            "endDateTime": {"dateTime": args.end_date_time, "timeZone": "UTC"},
        }
        return await self._client.request(
            "POST",
            f"/solutions/bookingBusinesses/{args.business_id}/appointments",
            json_data=body,
        )

    async def search_query(self, args: SearchQueryArgs) -> Any:
        body = {
            "requests": [
                {
                    "entityTypes": args.entity_types,
                    "query": {"queryString": args.query},
                    "size": args.size,
                }
            ]
        }
        return await self._client.request("POST", "/search/query", json_data=body)

    async def list_printers(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/print/printers",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_printer(self, args: GetPrinterArgs) -> Any:
        return await self._client.request("GET", f"/print/printers/{args.printer_id}")

    async def list_printer_shares(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/print/printerShares",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_print_jobs(self, args: ListPrintJobsArgs) -> Any:
        return await self._client.request_collection(
            f"/print/printers/{args.printer_id}/jobs"
        )

    async def cancel_print_job(self, args: CancelPrintJobArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/print/printers/{args.printer_id}/jobs/{args.job_id}/cancelPrintJob",
        )

    async def list_education_schools(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/education/schools",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_education_classes(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/education/classes",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_class_members(self, args: ListClassMembersArgs) -> Any:
        return await self._client.request_collection(
            f"/education/classes/{args.class_id}/members"
        )

    async def list_education_assignments(self, args: ListClassAssignmentsArgs) -> Any:
        return await self._client.request_collection(
            f"/education/classes/{args.class_id}/assignments"
        )

    async def get_education_user(self, args: GetEducationUserArgs) -> Any:
        return await self._client.request("GET", f"/education/users/{args.user_id}")

    async def list_cloud_pcs(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/deviceManagement/virtualEndpoint/cloudPCs",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_cloud_pc(self, args: GetCloudPcArgs) -> Any:
        return await self._client.request(
            "GET", f"/deviceManagement/virtualEndpoint/cloudPCs/{args.cloud_pc_id}"
        )

    async def list_cloud_pc_provisioning_policies(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/deviceManagement/virtualEndpoint/provisioningPolicies",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def reboot_cloud_pc(self, args: RebootCloudPcArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/deviceManagement/virtualEndpoint/cloudPCs/{args.cloud_pc_id}/reboot",
        )

    async def reprovision_cloud_pc(self, args: ReprovisionCloudPcArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/deviceManagement/virtualEndpoint/cloudPCs/{args.cloud_pc_id}/reprovision",
        )

    async def list_engage_communities(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/employeeExperience/communities",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_engage_community(self, args: GetEngageCommunityArgs) -> Any:
        return await self._client.request(
            "GET", f"/employeeExperience/communities/{args.community_id}"
        )

    async def list_learning_course_activities(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/employeeExperience/learningCourseActivities",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_learning_providers(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/employeeExperience/learningProviders",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_places(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/places",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_rooms(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/places/microsoft.graph.room",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_room_lists(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/places/microsoft.graph.roomList",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_workspaces(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/places/microsoft.graph.workspace",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_subscriptions(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/subscriptions",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def get_subscription(self, args: GetSubscriptionArgs) -> Any:
        return await self._client.request("GET", f"/subscriptions/{args.subscription_id}")

    async def create_subscription(self, args: CreateSubscriptionArgs) -> Any:
        body: dict[str, Any] = {
            "changeType": args.change_type,
            "notificationUrl": args.notification_url,
            "resource": args.resource,
            "expirationDateTime": args.expiration_date_time,
        }
        if args.client_state:
            body["clientState"] = args.client_state
        return await self._client.request("POST", "/subscriptions", json_data=body)

    async def renew_subscription(self, args: RenewSubscriptionArgs) -> Any:
        return await self._client.request(
            "PATCH",
            f"/subscriptions/{args.subscription_id}",
            json_data={"expirationDateTime": args.expiration_date_time},
        )

    async def delete_subscription(self, args: DeleteSubscriptionArgs) -> Any:
        return await self._client.request(
            "DELETE", f"/subscriptions/{args.subscription_id}"
        )

    # --- Tier-4 write-completeness handlers --------------------------------

    async def create_user(self, args: CreateUserArgs) -> Any:
        body = {
            "userPrincipalName": args.user_principal_name,
            "displayName": args.display_name,
            "mailNickname": args.mail_nickname,
            "accountEnabled": args.account_enabled,
            "passwordProfile": {
                "password": args.password,
                "forceChangePasswordNextSignIn": True,
            },
        }
        return await self._client.request("POST", "/users", json_data=body)

    async def create_group(self, args: CreateGroupArgs) -> Any:
        body: dict[str, Any] = {
            "displayName": args.display_name,
            "mailNickname": args.mail_nickname,
            "mailEnabled": args.mail_enabled,
            "securityEnabled": args.security_enabled,
        }
        if args.description:
            body["description"] = args.description
        return await self._client.request("POST", "/groups", json_data=body)

    async def update_group(self, args: UpdateGroupArgs) -> Any:
        body: dict[str, Any] = {}
        if args.display_name is not None:
            body["displayName"] = args.display_name
        if args.description is not None:
            body["description"] = args.description
        return await self._client.request(
            "PATCH", f"/groups/{args.group_id}", json_data=body
        )

    async def delete_group(self, args: DeleteGroupArgs) -> Any:
        return await self._client.request("DELETE", f"/groups/{args.group_id}")

    async def add_group_owner(self, args: GroupOwnerArgs) -> Any:
        body = {
            "@odata.id": (
                f"https://graph.microsoft.com/v1.0/directoryObjects/{args.owner_id}"
            )
        }
        return await self._client.request(
            "POST", f"/groups/{args.group_id}/owners/$ref", json_data=body
        )

    async def remove_group_owner(self, args: GroupOwnerArgs) -> Any:
        return await self._client.request(
            "DELETE", f"/groups/{args.group_id}/owners/{args.owner_id}/$ref"
        )

    async def set_service_principal_enabled(
        self, args: SetServicePrincipalEnabledArgs
    ) -> Any:
        return await self._client.request(
            "PATCH",
            f"/servicePrincipals/{args.service_principal_id}",
            json_data={"accountEnabled": args.account_enabled},
        )

    async def update_security_incident(self, args: UpdateSecurityIncidentArgs) -> Any:
        body: dict[str, Any] = {}
        if args.status is not None:
            body["status"] = args.status
        if args.classification is not None:
            body["classification"] = args.classification
        if args.assigned_to is not None:
            body["assignedTo"] = args.assigned_to
        if args.determination is not None:
            body["determination"] = args.determination
        return await self._client.request(
            "PATCH", f"/security/incidents/{args.incident_id}", json_data=body
        )

    async def run_hunting_query(self, args: RunHuntingQueryArgs) -> Any:
        body: dict[str, Any] = {"Query": args.query}
        if args.timespan:
            body["Timespan"] = args.timespan
        return await self._client.request("POST", "/security/runHuntingQuery", json_data=body)

    async def create_threat_assessment_request(
        self, args: CreateThreatAssessmentRequestArgs
    ) -> Any:
        body = dict(args.body)
        body.setdefault("@odata.type", f"#microsoft.graph.{args.request_type}")
        return await self._client.request(
            "POST", "/informationProtection/threatAssessmentRequests", json_data=body
        )

    async def create_conditional_access_policy(
        self, args: CreateConditionalAccessPolicyArgs
    ) -> Any:
        body: dict[str, Any] = {
            "displayName": args.display_name,
            "state": args.state,
            "conditions": args.conditions,
        }
        if args.grant_controls is not None:
            body["grantControls"] = args.grant_controls
        return await self._client.request(
            "POST", "/identity/conditionalAccess/policies", json_data=body
        )

    async def delete_conditional_access_policy(
        self, args: DeleteConditionalAccessPolicyArgs
    ) -> Any:
        return await self._client.request(
            "DELETE", f"/identity/conditionalAccess/policies/{args.policy_id}"
        )

    async def remove_user_license(self, args: RemoveUserLicenseArgs) -> Any:
        body = {"addLicenses": [], "removeLicenses": args.remove_skus}
        return await self._client.request(
            "POST", f"/users/{args.user_id}/assignLicense", json_data=body
        )

    async def add_application_password(self, args: AddApplicationPasswordArgs) -> Any:
        body = {"passwordCredential": {"displayName": args.display_name}}
        return await self._client.request(
            "POST", f"/applications/{args.application_id}/addPassword", json_data=body
        )

    async def remove_application_password(
        self, args: RemoveApplicationPasswordArgs
    ) -> Any:
        return await self._client.request(
            "POST",
            f"/applications/{args.application_id}/removePassword",
            json_data={"keyId": args.key_id},
        )

    async def reply_message(self, args: ReplyMessageArgs) -> Any:
        action = "replyAll" if args.reply_all else "reply"
        return await self._client.request(
            "POST",
            f"/users/{args.user_id}/messages/{args.message_id}/{action}",
            json_data={"comment": args.comment},
        )

    async def forward_message(self, args: ForwardMessageArgs) -> Any:
        body: dict[str, Any] = {
            "toRecipients": [
                {"emailAddress": {"address": addr}} for addr in args.to_recipients
            ]
        }
        if args.comment:
            body["comment"] = args.comment
        return await self._client.request(
            "POST",
            f"/users/{args.user_id}/messages/{args.message_id}/forward",
            json_data=body,
        )

    async def move_message(self, args: MoveMessageArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/users/{args.user_id}/messages/{args.message_id}/move",
            json_data={"destinationId": args.destination_id},
        )

    async def update_message(self, args: UpdateMessageArgs) -> Any:
        body: dict[str, Any] = {}
        if args.is_read is not None:
            body["isRead"] = args.is_read
        if args.flag_status is not None:
            body["flag"] = {"flagStatus": args.flag_status}
        return await self._client.request(
            "PATCH",
            f"/users/{args.user_id}/messages/{args.message_id}",
            json_data=body,
        )

    async def delete_message(self, args: MessageActionArgs) -> Any:
        return await self._client.request(
            "DELETE", f"/users/{args.user_id}/messages/{args.message_id}"
        )

    async def create_mail_folder(self, args: CreateMailFolderArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/users/{args.user_id}/mailFolders",
            json_data={"displayName": args.display_name},
        )

    async def update_event(self, args: UpdateEventArgs) -> Any:
        body: dict[str, Any] = {}
        if args.subject is not None:
            body["subject"] = args.subject
        if args.body_content is not None:
            body["body"] = {"contentType": "text", "content": args.body_content}
        return await self._client.request(
            "PATCH",
            f"/users/{args.user_id}/events/{args.event_id}",
            json_data=body,
        )

    async def respond_to_event(self, args: RespondToEventArgs) -> Any:
        body: dict[str, Any] = {"sendResponse": args.send_response}
        if args.comment:
            body["comment"] = args.comment
        return await self._client.request(
            "POST",
            f"/users/{args.user_id}/events/{args.event_id}/{args.response}",
            json_data=body,
        )

    async def create_team(self, args: CreateTeamArgs) -> Any:
        body: dict[str, Any] = {
            "template@odata.bind": args.template,
            "displayName": args.display_name,
        }
        if args.description:
            body["description"] = args.description
        return await self._client.request("POST", "/teams", json_data=body)

    async def add_team_member(self, args: AddTeamMemberArgs) -> Any:
        body = {
            "@odata.type": "#microsoft.graph.aadUserConversationMember",
            "user@odata.bind": (
                f"https://graph.microsoft.com/v1.0/users('{args.user_id}')"
            ),
            "roles": args.roles,
        }
        return await self._client.request(
            "POST", f"/teams/{args.team_id}/members", json_data=body
        )

    async def create_channel(self, args: CreateChannelArgs) -> Any:
        body = {
            "displayName": args.display_name,
            "membershipType": args.membership_type,
        }
        return await self._client.request(
            "POST", f"/teams/{args.team_id}/channels", json_data=body
        )

    async def archive_team(self, args: ArchiveTeamArgs) -> Any:
        return await self._client.request("POST", f"/teams/{args.team_id}/archive")

    async def create_chat(self, args: CreateChatArgs) -> Any:
        members = [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": (
                    f"https://graph.microsoft.com/v1.0/users('{mid}')"
                ),
            }
            for mid in args.member_ids
        ]
        body: dict[str, Any] = {"chatType": args.chat_type, "members": members}
        if args.topic:
            body["topic"] = args.topic
        return await self._client.request("POST", "/chats", json_data=body)

    async def upload_file(self, args: UploadFileArgs) -> Any:
        path = (
            f"/drives/{args.drive_id}/root:/{args.file_name}:/content"
            if args.parent_path == "root"
            else f"/drives/{args.drive_id}/root:/{args.parent_path}/{args.file_name}:/content"
        )
        return await self._client.request(
            "PUT", path, json_data={"_content": args.content}
        )

    async def create_folder(self, args: CreateFolderArgs) -> Any:
        body = {
            "name": args.folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail",
        }
        return await self._client.request(
            "POST",
            f"/drives/{args.drive_id}/items/{args.parent_id}/children",
            json_data=body,
        )

    async def delete_drive_item(self, args: DeleteDriveItemArgs) -> Any:
        return await self._client.request(
            "DELETE", f"/drives/{args.drive_id}/items/{args.item_id}"
        )

    async def copy_drive_item(self, args: CopyDriveItemArgs) -> Any:
        body: dict[str, Any] = {}
        if args.new_name:
            body["name"] = args.new_name
        if args.target_parent_id:
            body["parentReference"] = {"id": args.target_parent_id}
        return await self._client.request(
            "POST",
            f"/drives/{args.drive_id}/items/{args.item_id}/copy",
            json_data=body,
        )

    async def remote_lock_device(self, args: RemoteLockArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/deviceManagement/managedDevices/{args.device_id}/remoteLock",
        )

    async def reset_device_passcode(self, args: ResetPasscodeArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/deviceManagement/managedDevices/{args.device_id}/resetPasscode",
        )

    async def restart_managed_device(self, args: RestartManagedDeviceArgs) -> Any:
        return await self._client.request(
            "POST",
            f"/deviceManagement/managedDevices/{args.device_id}/rebootNow",
        )

    async def update_list_item(self, args: UpdateListItemArgs) -> Any:
        return await self._client.request(
            "PATCH",
            f"/sites/{args.site_id}/lists/{args.list_id}/items/{args.item_id}/fields",
            json_data=args.fields,
        )

    async def delete_list_item(self, args: DeleteListItemArgs) -> Any:
        return await self._client.request(
            "DELETE",
            f"/sites/{args.site_id}/lists/{args.list_id}/items/{args.item_id}",
        )

    async def update_contact(self, args: UpdateContactArgs) -> Any:
        body: dict[str, Any] = {}
        if args.given_name is not None:
            body["givenName"] = args.given_name
        if args.surname is not None:
            body["surname"] = args.surname
        if args.email is not None:
            body["emailAddresses"] = [{"address": args.email}]
        return await self._client.request(
            "PATCH",
            f"/users/{args.user_id}/contacts/{args.contact_id}",
            json_data=body,
        )

    async def delete_contact(self, args: DeleteContactArgs) -> Any:
        return await self._client.request(
            "DELETE", f"/users/{args.user_id}/contacts/{args.contact_id}"
        )

    async def update_planner_task(self, args: UpdatePlannerTaskArgs) -> Any:
        body: dict[str, Any] = {}
        if args.title is not None:
            body["title"] = args.title
        if args.percent_complete is not None:
            body["percentComplete"] = args.percent_complete
        return await self._client.request(
            "PATCH", f"/planner/tasks/{args.task_id}", json_data=body
        )

    async def delete_planner_task(self, args: DeletePlannerTaskArgs) -> Any:
        return await self._client.request("DELETE", f"/planner/tasks/{args.task_id}")

    async def update_todo_task(self, args: UpdateTodoTaskArgs) -> Any:
        body: dict[str, Any] = {}
        if args.title is not None:
            body["title"] = args.title
        if args.status is not None:
            body["status"] = args.status
        return await self._client.request(
            "PATCH",
            (
                f"/users/{args.user_id}/todo/lists/{args.list_id}"
                f"/tasks/{args.task_id}"
            ),
            json_data=body,
        )

    async def delete_todo_task(self, args: DeleteTodoTaskArgs) -> Any:
        return await self._client.request(
            "DELETE",
            (
                f"/users/{args.user_id}/todo/lists/{args.list_id}"
                f"/tasks/{args.task_id}"
            ),
        )

    async def cancel_booking_appointment(
        self, args: CancelBookingAppointmentArgs
    ) -> Any:
        body: dict[str, Any] = {}
        if args.cancellation_message:
            body["cancellationMessage"] = args.cancellation_message
        return await self._client.request(
            "POST",
            (
                f"/solutions/bookingBusinesses/{args.business_id}"
                f"/appointments/{args.appointment_id}/cancel"
            ),
            json_data=body,
        )

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

    async def list_lifecycle_workflows(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/identityGovernance/lifecycleWorkflows/workflows",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_workflow_runs(self, args: ListWorkflowRunsArgs) -> Any:
        return await self._client.request_collection(
            f"/identityGovernance/lifecycleWorkflows/workflows/{args.workflow_id}/runs",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def activate_workflow(self, args: ActivateWorkflowArgs) -> Any:
        body = {"subjects": [{"id": uid} for uid in args.subject_ids]}
        return await self._client.request(
            "POST",
            f"/identityGovernance/lifecycleWorkflows/workflows/{args.workflow_id}/activate",
            json_data=body,
        )

    async def list_administrative_units(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/directory/administrativeUnits",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def list_administrative_unit_members(
        self, args: ListAdministrativeUnitMembersArgs
    ) -> Any:
        return await self._client.request_collection(
            f"/directory/administrativeUnits/{args.au_id}/members",
            params=_pagination_params(args),
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def add_administrative_unit_member(self, args: AddAdministrativeUnitMemberArgs) -> Any:
        body = {
            "@odata.id": (f"https://graph.microsoft.com/v1.0/directoryObjects/{args.member_id}")
        }
        return await self._client.request(
            "POST",
            f"/directory/administrativeUnits/{args.au_id}/members/$ref",
            json_data=body,
        )

    async def list_guest_users(self, args: PaginationArgs) -> Any:
        return await self._client.request_collection(
            "/users",
            params={"$filter": "userType eq 'Guest'", "$top": args.top},
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )

    async def invite_guest_user(self, args: InviteGuestUserArgs) -> Any:
        body = {
            "invitedUserEmailAddress": args.email,
            "inviteRedirectUrl": args.redirect_url,
            "sendInvitationMessage": args.send_message,
        }
        return await self._client.request("POST", "/invitations", json_data=body)

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
