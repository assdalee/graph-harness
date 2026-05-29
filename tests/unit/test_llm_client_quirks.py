import pytest

from graph_harness.core.config import Settings
from graph_harness.llm.client import LiteLLMClient

TOOL_HISTORY = [
    {"role": "assistant", "content": "", "tool_calls": [{"id": "call-1"}]},
    {"role": "tool", "tool_call_id": "call-1", "content": "{}"},
    {"role": "user", "content": "Write final answer."},
]


def _capture(monkeypatch):
    captured: dict = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return {"choices": [{"message": {"content": "done"}}]}

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    return captured


# --- Layer 1: drop_params + opt-in temperature -------------------------


def test_kwargs_enable_drop_params() -> None:
    client = LiteLLMClient(Settings(llm_model="openai/gpt-4o-mini"))
    kwargs = client._completion_kwargs([{"role": "user", "content": "hi"}])
    assert kwargs["drop_params"] is True


def test_temperature_omitted_by_default() -> None:
    client = LiteLLMClient(Settings(llm_model="openai/gpt-4o-mini"))
    kwargs = client._completion_kwargs([{"role": "user", "content": "hi"}])
    assert "temperature" not in kwargs


def test_temperature_included_when_configured() -> None:
    client = LiteLLMClient(Settings(llm_model="openai/gpt-4o-mini", litellm_temperature=0.2))
    kwargs = client._completion_kwargs([{"role": "user", "content": "hi"}])
    assert kwargs["temperature"] == 0.2


# --- Layer 2: profile-driven proactive workaround ----------------------


@pytest.mark.asyncio
async def test_anthropic_profile_adds_dummy_tool(monkeypatch) -> None:
    captured = _capture(monkeypatch)
    client = LiteLLMClient(Settings(llm_model="claude-opus-4-7"))
    await client.complete(messages=TOOL_HISTORY, tools=None, tool_choice=None)
    assert captured["tool_choice"] == "none"
    assert captured["tools"][0]["function"]["name"] == "final_answer_context"


@pytest.mark.asyncio
async def test_override_disables_workaround_for_anthropic(monkeypatch) -> None:
    captured = _capture(monkeypatch)
    client = LiteLLMClient(
        Settings(llm_model="claude-opus-4-7", llm_requires_tools_with_tool_history=False)
    )
    await client.complete(messages=TOOL_HISTORY, tools=None, tool_choice=None)
    assert "tools" not in captured


@pytest.mark.asyncio
async def test_override_enables_workaround_for_openai(monkeypatch) -> None:
    captured = _capture(monkeypatch)
    client = LiteLLMClient(
        Settings(llm_model="openai/gpt-4o-mini", llm_requires_tools_with_tool_history=True)
    )
    await client.complete(messages=TOOL_HISTORY, tools=None, tool_choice=None)
    assert captured["tools"][0]["function"]["name"] == "final_answer_context"


# --- Layer 3: error-reactive fallback ----------------------------------


@pytest.mark.asyncio
async def test_retries_with_dummy_tool_on_missing_tools_error(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError("messages: `tool_use` blocks require the tools field to be provided")
        return {"choices": [{"message": {"content": "recovered"}}]}

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    # Non-anthropic model so the profile does NOT proactively adapt.
    client = LiteLLMClient(Settings(llm_model="openai/gpt-4o-mini"))

    response = await client.complete(messages=TOOL_HISTORY, tools=None, tool_choice=None)

    assert response.content == "recovered"
    assert len(calls) == 2
    assert "tools" not in calls[0]
    assert calls[1]["tools"][0]["function"]["name"] == "final_answer_context"


@pytest.mark.asyncio
async def test_unrelated_error_is_not_retried(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("rate limit exceeded")

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    client = LiteLLMClient(Settings(llm_model="openai/gpt-4o-mini"))

    with pytest.raises(RuntimeError, match="rate limit"):
        await client.complete(messages=TOOL_HISTORY, tools=None, tool_choice=None)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_no_retry_when_workaround_already_applied(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("tools field required")

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    # Anthropic model: proactive workaround already adds tools, so no retry loop.
    client = LiteLLMClient(Settings(llm_model="claude-opus-4-7"))

    with pytest.raises(RuntimeError):
        await client.complete(messages=TOOL_HISTORY, tools=None, tool_choice=None)
    assert len(calls) == 1


# --- Response normalization: relies on LiteLLM's OpenAI-shaped output --------


def test_normalize_reads_openai_tool_call_shape() -> None:
    client = LiteLLMClient(Settings(llm_model="openai/gpt-4o-mini"))
    raw = {
        "choices": [
            {
                "message": {
                    "content": "ok",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {"name": "list_users", "arguments": '{"top": 5}'},
                        }
                    ],
                }
            }
        ]
    }
    response = client._normalize_response(raw)
    assert response.content == "ok"
    assert response.tool_calls[0].name == "list_users"
    assert response.tool_calls[0].args == {"top": 5}
