import re
import threading
from dataclasses import dataclass
from typing import Any

from job_tracker.clients.claude import LLMError, LLMResponse


@dataclass(frozen=True)
class LLMCall:
    api_key: str
    model: str
    system: str
    prompt: str
    schema: dict[str, Any]


class FakeLLM:
    """Answers with scripted structured outputs instead of calling Claude.

    Scoring prompts are answered by the job's title (the prompt's "Title: ..." line): a fit score of 80 with
    stock reasons and keywords unless `score` or `answer` scripted something else for that title.
    """

    INPUT_TOKENS = 1000
    OUTPUT_TOKENS = 200

    def __init__(self) -> None:
        self._answers: dict[str, dict[str, Any] | LLMError] = {}
        self._failure: LLMError | None = None
        self._lock = threading.Lock()
        self.calls: list[LLMCall] = []

    def score(self, title: str, score: int, reasons: list[str] | None = None) -> None:
        self._answers[title] = {
            "score": score,
            "reasons": reasons or [f"Scored {score}."],
            "matched_keywords": ["Python"],
            "missing_keywords": ["Kafka"],
        }

    def answer(self, title: str, answer: dict[str, Any] | LLMError) -> None:
        """Answer with exactly this output (or raise this error) for jobs with this title."""
        self._answers[title] = answer

    def fail(self, error: LLMError | None) -> None:
        """Every call raises `error` from now on (or, given None, answers normally again)."""
        self._failure = error

    def scored_titles(self) -> list[str]:
        return sorted(_title(call.prompt) for call in self.calls)

    def generate(
        self, *, api_key: str, model: str, system: str, prompt: str, schema: dict[str, Any], max_tokens: int
    ) -> LLMResponse:
        with self._lock:
            self.calls.append(LLMCall(api_key, model, system, prompt, schema))
        if self._failure is not None:
            raise self._failure
        answer = self._answers.get(_title(prompt))
        if isinstance(answer, LLMError):
            raise answer
        if answer is None:
            answer = {
                "score": 80,
                "reasons": ["Your Python experience matches the role."],
                "matched_keywords": ["Python", "PostgreSQL"],
                "missing_keywords": ["Kafka"],
            }
        return LLMResponse(answer, model, self.INPUT_TOKENS, self.OUTPUT_TOKENS)


def _title(prompt: str) -> str:
    match = re.search(r"^Title: (.+)$", prompt, re.M)
    assert match, "not a scoring prompt"
    return match[1]
