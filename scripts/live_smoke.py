from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graph_harness.core.config import Settings
from graph_harness.core.errors import AuthenticationError
from graph_harness.graph.auth import GraphTokenProvider
from graph_harness.graph.client import GraphClient


REQUIRED_ENV = ("GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET")
REQUIRED_CHECKS = [
    ("users", "/users"),
    ("groups", "/groups"),
]
OPTIONAL_CHECKS = [
    ("security_alerts", "/security/alerts_v2"),
]


async def main() -> int:
    settings = Settings.from_env()
    settings_values = {
        "GRAPH_TENANT_ID": settings.graph_tenant_id,
        "GRAPH_CLIENT_ID": settings.graph_client_id,
        "GRAPH_CLIENT_SECRET": settings.graph_client_secret,
    }
    missing = [name for name in REQUIRED_ENV if not settings_values[name]]
    if missing:
        print(f"SKIP live smoke: missing {', '.join(missing)}")
        return 0

    shape_errors = []
    if not _looks_like_guid(settings.graph_tenant_id):
        shape_errors.append("GRAPH_TENANT_ID should be the tenant/directory GUID.")
    if not _looks_like_guid(settings.graph_client_id):
        shape_errors.append("GRAPH_CLIENT_ID should be the application/client GUID, not the client secret value.")
    if _looks_like_guid(settings.graph_client_secret):
        shape_errors.append("GRAPH_CLIENT_SECRET looks like a GUID. Use the client secret Value, not the Secret ID.")
    if shape_errors:
        print("FAIL live smoke: Microsoft Graph credential shape looks incorrect.")
        for error in shape_errors:
            print(f"  - {error}")
        return 1

    client = GraphClient(settings, GraphTokenProvider(settings))
    failed = False
    for name, endpoint in REQUIRED_CHECKS:
        result = await _run_check(client, name, endpoint, required=True)
        if result is False:
            failed = True

    for name, endpoint in OPTIONAL_CHECKS:
        await _run_check(client, name, endpoint, required=False)

    return 1 if failed else 0


async def _run_check(client: GraphClient, name: str, endpoint: str, *, required: bool) -> bool:
    try:
        result = await client.request_collection(endpoint, params={"$top": 1})
    except AuthenticationError as exc:
        print(f"FAIL auth: {exc}")
        if exc.details:
            print(f"  - provider_error: {exc.details.get('provider_error')}")
        return False
    if isinstance(result, dict) and "error" in result:
        message = result["error"].get("message") or "Unknown Graph error."
        if required:
            print(f"FAIL {name}: {message}")
            return False
        print(f"WARN optional {name}: {message}")
        return True

    count = len(result.get("value", [])) if isinstance(result, dict) else 0
    print(f"PASS {name}: {count} record(s)")
    return True


def _looks_like_guid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
