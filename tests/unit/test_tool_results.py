from graph_harness.tools.results import ToolResult


def test_tool_result_extracts_identifiers_from_odata_payload() -> None:
    result = ToolResult.from_payload(
        {
            "value": [
                {
                    "id": "user-1",
                    "displayName": "Ada Lovelace",
                    "userPrincipalName": "ada@example.com",
                    "jobTitle": "Engineer",
                }
            ]
        }
    )

    assert result.ok is True
    assert result.summary.startswith("Returned 1 record")
    assert result.identifiers == [
        {
            "id": "user-1",
            "displayName": "Ada Lovelace",
            "userPrincipalName": "ada@example.com",
        }
    ]


def test_tool_result_classifies_graph_permission_error() -> None:
    result = ToolResult.from_payload(
        {
            "error": {
                "status_code": 403,
                "message": "Insufficient privileges to complete the operation.",
                "payload": {},
            }
        }
    )

    assert result.ok is False
    assert result.error.code == "permission_denied"

