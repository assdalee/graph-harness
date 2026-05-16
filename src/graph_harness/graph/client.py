import asyncio
from typing import Any

import httpx

from graph_harness.core.config import Settings
from graph_harness.core.errors import UpstreamServiceError
from graph_harness.graph.auth import GraphTokenProvider


class GraphClient:
    """Low-level async Microsoft Graph HTTP client."""

    _retry_statuses = {429, 500, 502, 503, 504}

    def __init__(self, settings: Settings, token_provider: GraphTokenProvider) -> None:
        self._settings = settings
        self._token_provider = token_provider

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        api_version: str | None = None,
    ) -> Any:
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        version = api_version or self._settings.graph_default_api_version
        url = f"https://graph.microsoft.com/{version}{clean_endpoint}"

        last_error: Exception | None = None
        for attempt in range(3):
            token = await asyncio.to_thread(self._token_provider.get_token)
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            try:
                async with httpx.AsyncClient(timeout=self._settings.graph_timeout_seconds) as client:
                    response = await client.request(
                        method.upper(),
                        url,
                        headers=headers,
                        json=json_data,
                        params=params,
                    )
            except httpx.TransportError as exc:
                last_error = exc
                await asyncio.sleep(1.5 * (2**attempt))
                continue

            if response.status_code == 204:
                return {"success": True, "message": "Operation completed successfully"}

            if response.status_code in self._retry_statuses:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 1.5 * (2**attempt)
                await asyncio.sleep(min(delay, 30))
                continue

            try:
                payload = response.json()
            except ValueError:
                payload = {"raw": response.text}

            if response.is_error:
                return {
                    "error": {
                        "status_code": response.status_code,
                        "message": self._extract_error_message(payload),
                        "payload": payload,
                    }
                }
            return payload

        raise UpstreamServiceError(
            f"Microsoft Graph request failed after retries: {method.upper()} {clean_endpoint}",
            details={"last_error": str(last_error) if last_error else None},
        )

    async def request_collection(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        api_version: str | None = None,
        all_pages: bool = False,
        max_pages: int = 1,
    ) -> Any:
        first_page = await self.request("GET", endpoint, params=params, api_version=api_version)
        if not all_pages or not isinstance(first_page, dict) or "error" in first_page:
            return first_page

        merged = dict(first_page)
        values = list(first_page.get("value") or [])
        next_link = first_page.get("@odata.nextLink")
        pages_read = 1

        while next_link and pages_read < max_pages:
            page = await self._request_absolute_url(next_link)
            pages_read += 1
            if not isinstance(page, dict) or "error" in page:
                return page
            values.extend(page.get("value") or [])
            next_link = page.get("@odata.nextLink")

        merged["value"] = values
        if next_link:
            merged["@odata.nextLink"] = next_link
        else:
            merged.pop("@odata.nextLink", None)
        merged["@agent.pagesRead"] = pages_read
        return merged

    async def _request_absolute_url(self, url: str) -> Any:
        token = await asyncio.to_thread(self._token_provider.get_token)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self._settings.graph_timeout_seconds) as client:
            response = await client.get(url, headers=headers)
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}
        if response.is_error:
            return {
                "error": {
                    "status_code": response.status_code,
                    "message": self._extract_error_message(payload),
                    "payload": payload,
                }
            }
        return payload

    @staticmethod
    def _extract_error_message(payload: Any) -> str:
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error)
            if error:
                return str(error)
        return str(payload)
