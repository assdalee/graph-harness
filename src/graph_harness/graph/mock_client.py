"""No-credential in-memory Microsoft Graph backend for local harness testing."""
from __future__ import annotations

from typing import Any
class MockGraphClient:
    """Deterministic in-memory Microsoft Graph stand-in for local harness testing."""

    def __init__(self) -> None:
        """Seed fixed in-memory directory, security, and identity fixtures."""
        self.users = [
            {
                "id": "user-ada",
                "displayName": "Ada Lovelace",
                "userPrincipalName": "ada@example.com",
                "mail": "ada@example.com",
                "jobTitle": "Engineer",
            },
            {
                "id": "user-sarah",
                "displayName": "Sarah Chen",
                "userPrincipalName": "sarah@example.com",
                "mail": "sarah@example.com",
                "jobTitle": "Analyst",
            },
            {
                "id": "user-alex-1",
                "displayName": "Alex Kim",
                "userPrincipalName": "alex.kim@example.com",
                "mail": "alex.kim@example.com",
            },
            {
                "id": "user-alex-2",
                "displayName": "Alex Kim",
                "userPrincipalName": "alex.security@example.com",
                "mail": "alex.security@example.com",
            },
        ]
        self.groups = [
            {
                "id": "group-finance",
                "displayName": "Finance",
                "mail": "finance@example.com",
                "mailNickname": "finance",
            }
        ]
        self.alerts = [
            {
                "id": "alert-1",
                "title": "Suspicious PowerShell activity",
                "severity": "high",
                "status": "new",
                "createdDateTime": "2026-05-13T10:00:00Z",
            },
            {
                "id": "alert-2",
                "title": "Low risk sign-in",
                "severity": "low",
                "status": "resolved",
                "createdDateTime": "2026-05-12T10:00:00Z",
            },
        ]
        self.sign_ins = [
            {
                "id": "signin-1",
                "userPrincipalName": "sarah@example.com",
                "createdDateTime": "2026-05-13T09:00:00Z",
                "status": {"errorCode": 50126, "failureReason": "Invalid username or password."},
            }
        ]
        self.service_principals = [
            {
                "id": "sp-risky",
                "appId": "app-risky",
                "displayName": "Risky App",
                "accountEnabled": True,
            }
        ]
        self.oauth_grants = [
            {
                "id": "grant-risky",
                "clientId": "sp-risky",
                "consentType": "AllPrincipals",
                "scope": "Mail.Read Files.Read.All",
            }
        ]
        self.directory_roles = [
            {
                "id": "role-ga",
                "displayName": "Global Administrator",
                "roleTemplateId": "62e90394-69f5-4237-9190-012177145e10",
            },
            {
                "id": "role-helpdesk",
                "displayName": "Helpdesk Administrator",
                "roleTemplateId": "729827e3-9c14-49f7-bb1b-9608f156bbb8",
            },
        ]
        self.role_definitions = [
            {"id": "def-ga", "displayName": "Global Administrator", "isBuiltIn": True},
            {"id": "def-reader", "displayName": "Global Reader", "isBuiltIn": True},
        ]
        self.role_assignments = [
            {
                "id": "ra-1",
                "principalId": "user-ada",
                "roleDefinitionId": "def-reader",
                "directoryScopeId": "/",
            }
        ]
        self.conditional_access_policies = [
            {"id": "ca-1", "displayName": "Require MFA for admins", "state": "enabled"},
            {
                "id": "ca-2",
                "displayName": "Block legacy authentication",
                "state": "enabledForReportingButNotEnforced",
            },
        ]
        self.subscribed_skus = [
            {
                "id": "sku-e5",
                "skuId": "sku-e5-id",
                "skuPartNumber": "ENTERPRISEPREMIUM",
                "prepaidUnits": {"enabled": 100},
                "consumedUnits": 42,
            }
        ]
        self.license_details = [
            {"id": "lic-e5", "skuId": "sku-e5-id", "skuPartNumber": "ENTERPRISEPREMIUM"}
        ]
        self.applications = [
            {
                "id": "app-obj-1",
                "appId": "11111111-1111-1111-1111-111111111111",
                "displayName": "Internal API",
                "signInAudience": "AzureADMyOrg",
            }
        ]
        self.messages_fixture = [
            {
                "id": "msg-1",
                "subject": "Q2 planning",
                "from": {"emailAddress": {"address": "sarah@example.com"}},
                "receivedDateTime": "2026-05-20T08:00:00Z",
                "isRead": False,
            },
            {
                "id": "msg-2",
                "subject": "Lunch?",
                "from": {"emailAddress": {"address": "alex.kim@example.com"}},
                "receivedDateTime": "2026-05-21T12:00:00Z",
                "isRead": True,
            },
        ]
        self.mail_folders = [
            {"id": "folder-inbox", "displayName": "Inbox", "totalItemCount": 2},
            {"id": "folder-sent", "displayName": "Sent Items", "totalItemCount": 5},
        ]
        self.events = [
            {
                "id": "event-1",
                "subject": "Sprint review",
                "start": {"dateTime": "2026-06-01T09:00:00", "timeZone": "UTC"},
                "end": {"dateTime": "2026-06-01T10:00:00", "timeZone": "UTC"},
            },
            {
                "id": "event-2",
                "subject": "1:1 with Sarah",
                "start": {"dateTime": "2026-06-02T14:00:00", "timeZone": "UTC"},
                "end": {"dateTime": "2026-06-02T14:30:00", "timeZone": "UTC"},
            },
        ]
        self.joined_teams = [
            {"id": "team-eng", "displayName": "Engineering", "description": "Engineering team"},
            {"id": "team-ops", "displayName": "Operations", "description": "Ops team"},
        ]
        self.channels = [
            {"id": "channel-general", "displayName": "General", "membershipType": "standard"},
            {"id": "channel-incidents", "displayName": "Incidents", "membershipType": "private"},
        ]
        self.channel_messages = [
            {
                "id": "cmsg-1",
                "body": {"content": "Deploy is green."},
                "from": {"user": {"displayName": "Ada Lovelace"}},
            },
            {
                "id": "cmsg-2",
                "body": {"content": "Thanks all!"},
                "from": {"user": {"displayName": "Sarah Chen"}},
            },
        ]
        self.drive_items = [
            {"id": "item-budget", "name": "Budget.xlsx", "size": 20480, "folder": None},
            {"id": "item-notes", "name": "Notes.docx", "size": 10240, "folder": None},
        ]
        self.managed_devices = [
            {
                "id": "md-laptop",
                "deviceName": "ADA-LAPTOP",
                "operatingSystem": "Windows",
                "complianceState": "compliant",
            },
            {
                "id": "md-phone",
                "deviceName": "SARAH-IPHONE",
                "operatingSystem": "iOS",
                "complianceState": "noncompliant",
            },
        ]
        self.compliance_policies = [
            {"id": "cp-win", "displayName": "Windows compliance baseline"},
            {"id": "cp-ios", "displayName": "iOS compliance baseline"},
        ]
        self.device_configurations = [
            {"id": "dc-wifi", "displayName": "Corp Wi-Fi profile"},
            {"id": "dc-vpn", "displayName": "Corp VPN profile"},
        ]
        self.chats = [
            {"id": "chat-1", "topic": "Project Apollo", "chatType": "group"},
        ]
        self.chat_messages = [
            {"id": "cm-1", "body": {"content": "Standup at 10?"}, "from": "ada@example.com"},
        ]
        self.sites = [
            {
                "id": "site-root",
                "displayName": "Communication site",
                "webUrl": "https://contoso.sharepoint.com",
            },
        ]
        self.site_lists = [
            {"id": "list-docs", "displayName": "Documents"},
        ]
        self.list_items = [
            {"id": "item-1", "fields": {"Title": "Q2 plan"}},
        ]
        self.notebooks = [
            {"id": "nb-1", "displayName": "Team Notebook"},
        ]
        self.notebook_sections = [
            {"id": "sec-1", "displayName": "Meetings"},
        ]
        self.section_pages = [
            {"id": "pg-1", "title": "Kickoff notes"},
        ]
        self.contacts_fixture = [
            {
                "id": "contact-1",
                "displayName": "Grace Hopper",
                "givenName": "Grace",
                "surname": "Hopper",
            },
        ]
        self.planner_plans = [
            {"id": "plan-1", "title": "Launch plan"},
        ]
        self.planner_tasks = [
            {"id": "ptask-1", "planId": "plan-1", "title": "Draft brief"},
        ]
        self.todo_lists = [
            {"id": "tdl-1", "displayName": "Tasks"},
        ]
        self.todo_tasks = [
            {"id": "tdt-1", "title": "Review PR"},
        ]
        self.service_health_overviews = [
            {"id": "Exchange", "service": "Exchange Online", "status": "serviceOperational"},
        ]
        self.service_health_issues = [
            {"id": "EX123", "title": "Delays in email delivery", "status": "serviceDegradation"},
        ]
        self.service_messages = [
            {"id": "MC123", "title": "Upcoming change to Teams", "category": "planForChange"},
        ]
        self.secure_scores = [
            {"id": "score-2026-05-13", "currentScore": 412, "maxScore": 600},
        ]
        self.secure_score_control_profiles = [
            {"id": "MFARegistrationV2", "title": "Require MFA registration", "maxScore": 30},
        ]
        self.ediscovery_cases = [
            {"id": "case-1", "displayName": "Acme litigation", "status": "active"},
        ]
        self.ediscovery_custodians = [
            {"id": "cust-1", "email": "sarah@example.com", "status": "active"},
        ]
        self.sensitivity_labels = [
            {"id": "label-conf", "name": "Confidential", "isActive": True},
        ]
        self.label_policy_settings = [
            {"id": "settings", "moreInfoUrl": "https://contoso.example/labels"},
        ]
        self.threat_intel_articles = [
            {"id": "ti-article-1", "title": "Emerging phishing campaign"},
        ]
        self.intel_profiles = [
            {"id": "actor-1", "title": "Storm-0123", "kind": "actor"},
        ]
        self.threat_intel_hosts = [
            {"id": "contoso.example", "firstSeenDateTime": "2026-04-01T00:00:00Z"},
        ]
        self.vulnerabilities = [
            {"id": "CVE-2026-0001", "severity": "high"},
        ]
        self.online_meetings = [
            {"id": "meeting-1", "subject": "Customer sync", "joinWebUrl": "https://teams.example"},
        ]
        self.meeting_attendance_reports = [
            {"id": "report-1", "totalParticipantCount": 5},
        ]
        self.booking_businesses = [
            {"id": "booking-contoso", "displayName": "Contoso Clinic"},
        ]
        self.booking_services = [
            {"id": "svc-checkup", "displayName": "Checkup", "defaultDuration": "PT30M"},
        ]
        self.booking_appointments = [
            {"id": "appt-1", "serviceId": "svc-checkup", "customerName": "Grace Hopper"},
        ]
        self.search_hits = [
            {"hitId": "msg-1", "rank": 1, "summary": "Q2 planning"},
        ]

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        api_version: str | None = None,
        advanced_query: bool = False,
    ) -> Any:
        """Route a request to the matching fixture handler, mimicking Graph responses.

        ``advanced_query`` is accepted to match the live client interface but
        ignored: the mock returns fixtures and sends no consistency headers.
        """
        method = method.upper()
        endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        params = params or {}

        if method == "GET" and endpoint == "/directoryRoles":
            return {"value": self._top(self.directory_roles, params)}
        if method == "GET" and endpoint == "/roleManagement/directory/roleDefinitions":
            return {"value": self._top(self.role_definitions, params)}
        if method == "GET" and endpoint == "/roleManagement/directory/roleAssignments":
            return {"value": self._top(self.role_assignments, params)}
        if method == "GET" and endpoint == "/identity/conditionalAccess/policies":
            return {"value": self._top(self.conditional_access_policies, params)}
        if method == "GET" and endpoint.startswith("/identity/conditionalAccess/policies/"):
            return self._get_by_identifier(
                self.conditional_access_policies,
                endpoint.removeprefix("/identity/conditionalAccess/policies/"),
            )
        if method == "GET" and endpoint == "/subscribedSkus":
            return {"value": self._top(self.subscribed_skus, params)}
        if (
            method == "GET"
            and endpoint.startswith("/users/")
            and endpoint.endswith("/licenseDetails")
        ):
            return {"value": self.license_details}
        if method == "GET" and endpoint == "/deviceManagement/managedDevices":
            return {"value": self._top(self.managed_devices, params)}
        if method == "GET" and endpoint.startswith("/deviceManagement/managedDevices/"):
            return self._get_by_identifier(
                self.managed_devices,
                endpoint.removeprefix("/deviceManagement/managedDevices/"),
            )
        if method == "GET" and endpoint == "/deviceManagement/deviceCompliancePolicies":
            return {"value": self._top(self.compliance_policies, params)}
        if method == "GET" and endpoint == "/deviceManagement/deviceConfigurations":
            return {"value": self._top(self.device_configurations, params)}
        if method == "GET" and endpoint == "/applications":
            return {"value": self._top(self.applications, params)}
        if method == "GET" and endpoint.startswith("/applications/"):
            return self._get_by_identifier(
                self.applications, endpoint.removeprefix("/applications/")
            )

        # Microsoft 365 productivity user-scoped reads must be routed before the
        # generic "/users/{id}" get-by-id branch, which would otherwise shadow them.
        if method == "GET" and endpoint.startswith("/users/"):
            tail = endpoint.removeprefix("/users/")
            if "/" in tail:
                _user, rest = tail.split("/", 1)
                if rest == "messages":
                    return {"value": self._top(self.messages_fixture, params)}
                if rest.startswith("messages/"):
                    return self._get_by_identifier(
                        self.messages_fixture, rest.removeprefix("messages/")
                    )
                if rest == "mailFolders":
                    return {"value": self._top(self.mail_folders, params)}
                if rest == "events":
                    return {"value": self._top(self.events, params)}
                if rest.startswith("events/"):
                    return self._get_by_identifier(self.events, rest.removeprefix("events/"))
                if rest == "joinedTeams":
                    return {"value": self._top(self.joined_teams, params)}
                if rest == "drive/root/children":
                    return {"value": self._top(self.drive_items, params)}
                if rest.startswith("drive/root/search"):
                    return {"value": self._top(self.drive_items, params)}
                if rest.startswith("drive/items/"):
                    return self._get_by_identifier(
                        self.drive_items, rest.removeprefix("drive/items/")
                    )
                if rest == "chats":
                    return {"value": self._top(self.chats, params)}
                if rest == "contacts":
                    return {"value": self._top(self.contacts_fixture, params)}
                if rest.startswith("contacts/"):
                    return self._get_by_identifier(
                        self.contacts_fixture, rest.removeprefix("contacts/")
                    )
                if rest == "onenote/notebooks":
                    return {"value": self._top(self.notebooks, params)}
                if rest.startswith("onenote/notebooks/") and rest.endswith("/sections"):
                    return {"value": self._top(self.notebook_sections, params)}
                if rest.startswith("onenote/sections/") and rest.endswith("/pages"):
                    return {"value": self._top(self.section_pages, params)}
                if rest == "todo/lists":
                    return {"value": self._top(self.todo_lists, params)}
                if rest.startswith("todo/lists/") and rest.endswith("/tasks"):
                    return {"value": self._top(self.todo_tasks, params)}
                if rest.startswith("onlineMeetings/") and rest.endswith("/attendanceReports"):
                    return {"value": self._top(self.meeting_attendance_reports, params)}
                if rest.startswith("onlineMeetings/"):
                    return self._get_by_identifier(
                        self.online_meetings, rest.removeprefix("onlineMeetings/")
                    )
        if method == "GET" and endpoint.startswith("/teams/"):
            tail = endpoint.removeprefix("/teams/")
            if tail.endswith("/channels"):
                return {"value": self._top(self.channels, params)}
            if "/channels/" in tail and tail.endswith("/messages"):
                return {"value": self._top(self.channel_messages, params)}

        if method == "GET" and endpoint.startswith("/chats/") and endpoint.endswith("/messages"):
            return {"value": self._top(self.chat_messages, params)}
        if method == "GET" and endpoint == "/sites":
            return {"value": self._top(self.sites, params)}
        if method == "GET" and endpoint.startswith("/sites/"):
            tail = endpoint.removeprefix("/sites/")
            if tail.endswith("/lists"):
                return {"value": self._top(self.site_lists, params)}
            if "/lists/" in tail and tail.endswith("/items"):
                return {"value": self._top(self.list_items, params)}
            return self._get_by_identifier(self.sites, tail)
        if method == "GET" and endpoint.startswith("/planner/plans/"):
            tail = endpoint.removeprefix("/planner/plans/")
            if tail.endswith("/tasks"):
                return {"value": self._top(self.planner_tasks, params)}
            return self._get_by_identifier(self.planner_plans, tail)
        if method == "GET" and endpoint.startswith("/reports/"):
            return {"value": [{"reportRefreshDate": "2026-05-13", "note": "mock usage report"}]}
        if method == "GET" and endpoint == "/admin/serviceAnnouncement/healthOverviews":
            return {"value": self._top(self.service_health_overviews, params)}
        if method == "GET" and endpoint == "/admin/serviceAnnouncement/issues":
            return {"value": self._top(self.service_health_issues, params)}
        if method == "GET" and endpoint == "/admin/serviceAnnouncement/messages":
            return {"value": self._top(self.service_messages, params)}

        if method == "GET" and endpoint == "/security/secureScores":
            return {"value": self._top(self.secure_scores, params)}
        if method == "GET" and endpoint == "/security/secureScoreControlProfiles":
            return {"value": self._top(self.secure_score_control_profiles, params)}
        if method == "GET" and endpoint == "/security/cases/ediscoveryCases":
            return {"value": self._top(self.ediscovery_cases, params)}
        if method == "GET" and endpoint.startswith("/security/cases/ediscoveryCases/"):
            tail = endpoint.removeprefix("/security/cases/ediscoveryCases/")
            if tail.endswith("/custodians"):
                return {"value": self._top(self.ediscovery_custodians, params)}
            return self._get_by_identifier(self.ediscovery_cases, tail)
        if method == "GET" and endpoint == "/security/informationProtection/sensitivityLabels":
            return {"value": self._top(self.sensitivity_labels, params)}
        if method == "GET" and endpoint.startswith(
            "/security/informationProtection/sensitivityLabels/"
        ):
            return self._get_by_identifier(
                self.sensitivity_labels,
                endpoint.removeprefix("/security/informationProtection/sensitivityLabels/"),
            )
        if method == "GET" and endpoint == "/security/informationProtection/labelPolicySettings":
            return {"value": self._top(self.label_policy_settings, params)}
        if method == "GET" and endpoint == "/security/threatIntelligence/articles":
            return {"value": self._top(self.threat_intel_articles, params)}
        if method == "GET" and endpoint == "/security/threatIntelligence/intelProfiles":
            return {"value": self._top(self.intel_profiles, params)}
        if method == "GET" and endpoint.startswith("/security/threatIntelligence/hosts/"):
            return self._get_by_identifier(
                self.threat_intel_hosts,
                endpoint.removeprefix("/security/threatIntelligence/hosts/"),
            )
        if method == "GET" and endpoint.startswith("/security/threatIntelligence/vulnerabilities/"):
            return self._get_by_identifier(
                self.vulnerabilities,
                endpoint.removeprefix("/security/threatIntelligence/vulnerabilities/"),
            )
        if method == "GET" and endpoint == "/solutions/bookingBusinesses":
            return {"value": self._top(self.booking_businesses, params)}
        if method == "GET" and endpoint.startswith("/solutions/bookingBusinesses/"):
            tail = endpoint.removeprefix("/solutions/bookingBusinesses/")
            if tail.endswith("/services"):
                return {"value": self._top(self.booking_services, params)}
            if tail.endswith("/appointments"):
                return {"value": self._top(self.booking_appointments, params)}
            return self._get_by_identifier(self.booking_businesses, tail)
        if method == "POST" and endpoint == "/search/query":
            return {"value": [{"hitsContainers": [{"hits": self.search_hits, "total": 1}]}]}

        if method == "GET" and endpoint == "/users":
            result = self._filter_entities(self.users, params)
            return result if isinstance(result, dict) and "error" in result else {"value": result}
        if method == "GET" and endpoint.startswith("/users/"):
            return self._get_by_identifier(self.users, endpoint.removeprefix("/users/"))
        if method == "GET" and endpoint == "/groups":
            return {"value": self._filter_entities(self.groups, params)}
        if (
            method == "GET"
            and endpoint.startswith("/groups/")
            and endpoint.endswith("/planner/plans")
        ):
            return {"value": self._top(self.planner_plans, params)}
        if method == "GET" and endpoint.startswith("/groups/"):
            return self._get_by_identifier(self.groups, endpoint.removeprefix("/groups/"))
        if method == "GET" and endpoint == "/security/alerts_v2":
            result = self._filter_alerts(params)
            return result if isinstance(result, dict) and "error" in result else {"value": result}
        if method == "GET" and endpoint == "/security/incidents":
            return {
                "error": {
                    "status_code": 403,
                    "message": "Insufficient privileges to list security incidents.",
                    "payload": {},
                }
            }
        if method == "GET" and endpoint == "/auditLogs/signIns":
            return {"value": self._filter_sign_ins(params)}
        if method == "GET" and endpoint == "/servicePrincipals":
            return {"value": self._filter_entities(self.service_principals, params)}
        if method == "GET" and endpoint == "/oauth2PermissionGrants":
            return {"value": self._filter_oauth_grants(params)}
        if method == "DELETE" and endpoint.startswith("/oauth2PermissionGrants/"):
            return {"success": True, "message": f"Mock DELETE {endpoint} completed."}
        if method in {"POST", "PATCH", "DELETE"}:
            return {"success": True, "message": f"Mock {method} {endpoint} completed."}
        return {
            "error": {
                "status_code": 404,
                "message": f"Mock endpoint not found: {method} {endpoint}",
                "payload": {},
            }
        }

    async def request_collection(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        api_version: str | None = None,
        all_pages: bool = False,
        max_pages: int = 1,
        advanced_query: bool = False,
    ) -> Any:
        """Return a single page; the mock never paginates so paging args are ignored."""
        return await self.request(
            "GET",
            endpoint,
            params=params,
            api_version=api_version,
            advanced_query=advanced_query,
        )

    def _filter_entities(self, entities: list[dict[str, Any]], params: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any]:
        """Match entities by quoted filter term, with magic terms to simulate rate limits and errors."""
        filter_expr = str(params.get("$filter") or "")
        if "ratelimit" in filter_expr.lower():
            return {
                "error": {
                    "status_code": 429,
                    "message": "Mock Microsoft Graph rate limit.",
                    "payload": {},
                }
            }
        if "unsupported" in filter_expr.lower():
            return []
        filtered = entities
        quoted = self._quoted_values(filter_expr)
        if quoted:
            needle = quoted[0].lower()
            filtered = [
                item
                for item in filtered
                if needle
                in " ".join(
                    str(item.get(key) or "")
                    for key in ("id", "displayName", "userPrincipalName", "mail", "mailNickname")
                ).lower()
            ]
        return self._top(filtered, params)

    def _filter_alerts(self, params: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any]:
        """Filter security alerts by severity/status, returning a 400 for unsupported properties."""
        filter_expr = str(params.get("$filter") or "")
        if "badUnsupported" in filter_expr or "unsupported" in filter_expr.lower():
            return {
                "error": {
                    "status_code": 400,
                    "message": "Unsupported OData filter property.",
                    "payload": {},
                }
            }
        filtered = self.alerts
        if "severity eq 'high'" in filter_expr:
            filtered = [item for item in filtered if item["severity"] == "high"]
        if "status eq 'new'" in filter_expr:
            filtered = [item for item in filtered if item["status"] == "new"]
        return self._top(filtered, params)

    def _filter_sign_ins(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Filter sign-in logs by error code and quoted user principal name."""
        filter_expr = str(params.get("$filter") or "")
        filtered = self.sign_ins
        if "status/errorCode eq 50126" in filter_expr:
            filtered = [item for item in filtered if item.get("status", {}).get("errorCode") == 50126]
        quoted = self._quoted_values(filter_expr)
        if quoted:
            needle = quoted[0].lower()
            filtered = [item for item in filtered if item.get("userPrincipalName", "").lower() == needle]
        return self._top(filtered, params)

    def _filter_oauth_grants(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Filter OAuth permission grants by clientId and consentType."""
        filter_expr = str(params.get("$filter") or "")
        filtered = self.oauth_grants
        quoted = self._quoted_values(filter_expr)
        if "clientId eq" in filter_expr and quoted:
            filtered = [item for item in filtered if item.get("clientId") == quoted[0]]
        if "consentType eq" in filter_expr and quoted:
            filtered = [item for item in filtered if item.get("consentType") in quoted]
        return self._top(filtered, params)

    def _get_by_identifier(self, entities: list[dict[str, Any]], identifier: str) -> Any:
        """Look up one entity by id, UPN, mail, or nickname, returning a 404 error if absent."""
        for item in entities:
            if identifier in {
                item.get("id"),
                item.get("userPrincipalName"),
                item.get("mail"),
                item.get("mailNickname"),
            }:
                return item
        return {
            "error": {
                "status_code": 404,
                "message": f"Object not found: {identifier}",
                "payload": {},
            }
        }

    @staticmethod
    def _quoted_values(filter_expr: str) -> list[str]:
        """Extract single-quoted literals from an OData filter expression."""
        values: list[str] = []
        parts = filter_expr.split("'")
        for index in range(1, len(parts), 2):
            values.append(parts[index])
        return values

    @staticmethod
    def _top(items: list[dict[str, Any]], params: dict[str, Any]) -> list[dict[str, Any]]:
        """Apply an $top limit, ignoring malformed values."""
        top = params.get("$top")
        try:
            return items[: int(top)] if top else items
        except (TypeError, ValueError):
            return items
