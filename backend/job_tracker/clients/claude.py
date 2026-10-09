"""The LLM port, and Claude behind it through the official Anthropic SDK with JSON-schema structured output."""

import json
import threading
from dataclasses import dataclass
from typing import Any, Protocol

import anthropic
import httpx2


@dataclass(frozen=True)
class LLMResponse:
    data: dict[str, Any]
    model: str
    input_tokens: int
    output_tokens: int


class LLMError(Exception):
    """A failed LLM call. `fatal` errors (bad key, unknown model, no connection) would fail every later call too."""

    def __init__(self, message: str, fatal: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.fatal = fatal


class LLM(Protocol):
    def generate(
        self, *, api_key: str, model: str, system: str, prompt: str, schema: dict[str, Any], max_tokens: int
    ) -> LLMResponse:
        """Ask the model for one JSON object matching `schema`."""
        ...


class ClaudeLLM:
    def __init__(self, http_client: httpx2.Client | None = None) -> None:
        self._http_client = http_client
        self._clients: dict[str, anthropic.Anthropic] = {}
        self._lock = threading.Lock()

    def _client(self, api_key: str) -> anthropic.Anthropic:
        with self._lock:
            if api_key not in self._clients:
                client = anthropic.Anthropic(api_key=api_key, max_retries=3, timeout=120, http_client=self._http_client)
                self._clients = {api_key: client}
            return self._clients[api_key]

    def generate(
        self, *, api_key: str, model: str, system: str, prompt: str, schema: dict[str, Any], max_tokens: int
    ) -> LLMResponse:
        try:
            message = self._client(api_key).messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except anthropic.AuthenticationError:
            raise LLMError("Claude rejected your Anthropic API key. Check it in Settings.", fatal=True) from None
        except anthropic.PermissionDeniedError:
            raise LLMError(f"Your Anthropic API key isn't allowed to use {model}.", fatal=True) from None
        except anthropic.NotFoundError:
            raise LLMError(
                f"Claude has no model called “{model}”. Check the model names in Settings.", fatal=True
            ) from None
        except anthropic.RateLimitError:
            raise LLMError("Claude's rate limit was reached. Try again in a few minutes.", fatal=True) from None
        except anthropic.APIConnectionError:
            raise LLMError("Couldn't reach the Claude API.", fatal=True) from None
        except anthropic.BadRequestError as error:
            if "credit balance" in str(error).lower():
                raise LLMError("Your Anthropic account is out of credit.", fatal=True) from None
            raise LLMError(f"Claude refused the request: {_api_message(error)}") from None
        except anthropic.APIStatusError as error:
            raise LLMError(f"The Claude API returned HTTP {error.status_code}.") from None
        if message.stop_reason == "refusal":
            raise LLMError("Claude declined to answer.")
        if message.stop_reason == "max_tokens":
            raise LLMError("Claude's answer was cut off.")
        text = "".join(block.text for block in message.content if block.type == "text")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            raise LLMError("Claude's answer wasn't valid JSON.") from None
        if not isinstance(data, dict):
            raise LLMError("Claude's answer wasn't a JSON object.")
        return LLMResponse(data, message.model, message.usage.input_tokens, message.usage.output_tokens)


def _api_message(error: anthropic.APIStatusError) -> str:
    body = error.body
    if isinstance(body, dict):
        detail = body.get("error")
        if isinstance(detail, dict) and isinstance(detail.get("message"), str):
            return str(detail["message"])
    return str(error)
