import json
from typing import Any

import httpx2
import pytest

from job_tracker.clients.claude import ClaudeLLM, LLMError, LLMResponse

API_KEY = "sk-ant-test-key-5678"


def claude(handler: Any) -> ClaudeLLM:
    return ClaudeLLM(http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))


def generate(llm: ClaudeLLM) -> LLMResponse:
    return llm.generate(
        api_key=API_KEY,
        model="claude-haiku-5-5",
        system="Be brief.",
        prompt="Score this.",
        schema={"type": "object"},
        max_tokens=100,
    )


def test_claude_is_asked_for_structured_output_and_its_answer_parsed() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": "claude-haiku-5-5-20260901",
                "content": [{"type": "text", "text": '{"score": 77}'}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1234, "output_tokens": 56},
            },
        )

    response = generate(claude(handler))

    assert (response.data, response.model) == ({"score": 77}, "claude-haiku-5-5-20260901")
    assert (response.input_tokens, response.output_tokens) == (1234, 56)
    [request] = requests
    body = json.loads(request.content)
    assert request.headers["x-api-key"] == API_KEY
    assert body["output_config"] == {"format": {"type": "json_schema", "schema": {"type": "object"}}}
    assert (body["model"], body["system"], body["max_tokens"]) == ("claude-haiku-5-5", "Be brief.", 100)


@pytest.mark.parametrize(
    ("status", "error", "message", "fatal"),
    [
        (401, "authentication_error", "Claude rejected your Anthropic API key. Check it in Settings.", True),
        (
            404,
            "not_found_error",
            "Claude has no model called “claude-haiku-5-5”. Check the model names in Settings.",
            True,
        ),
        (400, "invalid_request_error", "Your Anthropic account is out of credit.", True),
    ],
)
def test_claude_errors_are_explained(status: int, error: str, message: str, fatal: bool) -> None:
    detail = "Your credit balance is too low." if status == 400 else "nope"
    body = {"type": "error", "error": {"type": error, "message": detail}}

    with pytest.raises(LLMError) as raised:
        generate(claude(lambda _: httpx2.Response(status, json=body)))

    assert (raised.value.message, raised.value.fatal) == (message, fatal)
