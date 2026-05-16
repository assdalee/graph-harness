from graph_harness.agent.compaction import ContextCompactor
from graph_harness.core.config import Settings
from graph_harness.tools.results import ToolResult


def test_compactor_preserves_intent_recent_messages_and_identifiers() -> None:
    settings = Settings(agent_context_recent_messages=4, agent_context_max_tool_chars=2000)
    compactor = ContextCompactor(settings)
    tool_result = ToolResult.success(
        {
            "value": [
                {
                    "id": "user-1",
                    "displayName": "Ada Lovelace",
                    "userPrincipalName": "ada@example.com",
                }
            ]
        }
    )
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "Original request"},
        {"role": "assistant", "content": "old assistant note"},
        {
            "role": "tool",
            "name": "list_users",
            "tool_call_id": "1",
            "content": tool_result.model_dump_json(),
        },
        {"role": "user", "content": "middle"},
        {"role": "assistant", "content": "recent assistant"},
        {"role": "user", "content": "recent user"},
        {"role": "assistant", "content": "recent answer"},
    ]

    compacted, did_compact = compactor.compact(messages)

    assert did_compact is True
    joined = "\n".join(message.get("content", "") for message in compacted)
    assert "Original user intent: Original request" in joined
    assert "Ada Lovelace" in joined
    assert "user-1" in joined
    assert compacted[-1]["content"] == "recent answer"


def test_compactor_can_be_disabled() -> None:
    compactor = ContextCompactor(Settings(agent_enable_context_compaction=False))
    messages = [{"role": "user", "content": str(index)} for index in range(20)]

    compacted, did_compact = compactor.compact(messages)

    assert did_compact is False
    assert compacted == messages
