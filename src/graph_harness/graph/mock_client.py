from __future__ import annotations

from typing import Any
class MockGraphClient:
    """Deterministic in-memory Microsoft Graph stand-in for local harness testing."""

    def __init__(self) -> None:
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

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        api_version: str | None = None,
    ) -> Any:
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
        if method == "GET" and endpoint == "/applications":
            return {"value": self._top(self.applications, params)}
        if method == "GET" and endpoint.startswith("/applications/"):
            return self._get_by_identifier(
                self.applications, endpoint.removeprefix("/applications/")
            )

        if method == "GET" and endpoint == "/users":
            result = self._filter_entities(self.users, params)
            return result if isinstance(result, dict) and "error" in result else {"value": result}
        if method == "GET" and endpoint.startswith("/users/"):
            return self._get_by_identifier(self.users, endpoint.removeprefix("/users/"))
        if method == "GET" and endpoint == "/groups":
            return {"value": self._filter_entities(self.groups, params)}
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
    ) -> Any:
        return await self.request("GET", endpoint, params=params, api_version=api_version)

    def _filter_entities(self, entities: list[dict[str, Any]], params: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any]:
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
        filter_expr = str(params.get("$filter") or "")
        filtered = self.oauth_grants
        quoted = self._quoted_values(filter_expr)
        if "clientId eq" in filter_expr and quoted:
            filtered = [item for item in filtered if item.get("clientId") == quoted[0]]
        if "consentType eq" in filter_expr and quoted:
            filtered = [item for item in filtered if item.get("consentType") in quoted]
        return self._top(filtered, params)

    def _get_by_identifier(self, entities: list[dict[str, Any]], identifier: str) -> Any:
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
        values: list[str] = []
        parts = filter_expr.split("'")
        for index in range(1, len(parts), 2):
            values.append(parts[index])
        return values

    @staticmethod
    def _top(items: list[dict[str, Any]], params: dict[str, Any]) -> list[dict[str, Any]]:
        top = params.get("$top")
        try:
            return items[: int(top)] if top else items
        except (TypeError, ValueError):
            return items
