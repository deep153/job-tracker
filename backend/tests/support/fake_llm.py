import json
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

    @property
    def is_tailoring(self) -> bool:
        return "summary" in self.schema.get("properties", {})

    @property
    def is_answering(self) -> bool:
        return "answers" in self.schema.get("properties", {})

    @property
    def is_cover_letter(self) -> bool:
        return "cover_letter" in self.schema.get("properties", {})

    @property
    def is_profile(self) -> bool:
        return "education" in self.schema.get("properties", {})

    @property
    def is_scoring(self) -> bool:
        return not (self.is_tailoring or self.is_answering or self.is_cover_letter or self.is_profile)

    @property
    def questions(self) -> list[str]:
        """The questions an answering prompt asks to draft."""
        return [question["question"] for question in _questions(self.prompt)]


DEFAULT_TAILORED_SUMMARY = "Backend engineer who builds reliable payment APIs in Python and Go."
DEFAULT_COVER_LETTER = (
    "Dear Globex hiring team,\n\nI have spent six years building payment systems in Python and Go, and I would "
    "like to bring that to your backend team.\n\nSincerely,\nJordan Rivera"
)
# Read the way Claude might read `full_resume()`: the name as the resume shows it, abbreviated degrees, and the
# lower degree first.
DEFAULT_PROFILE: dict[str, Any] = {
    "first_name": "JORDAN",
    "last_name": "RIVERA",
    "city": "Brooklyn",
    "region": "NY",
    "country": "United States",
    "education": [
        {
            "school": "University of Mumbai",
            "degree": "B.Tech.",
            "discipline": "Computer Engineering",
            "end_month": "June",
            "end_year": "2017",
        },
        {
            "school": "Columbia University",
            "degree": "MS",
            "discipline": "Computer Science",
            "end_month": "05",
            "end_year": "2020",
        },
    ],
}


class FakeLLM:
    """Answers with scripted structured outputs instead of calling Claude.

    Scoring prompts are answered by the job's title (the prompt's "Title: ..." line): a fit score of 80 with
    stock reasons and keywords unless `score` or `answer` scripted something else for that title, or
    `score_resume` scripted a score for the resume being scored.
    Tailoring prompts get the answers queued with `tailor` (which may reword bullets and list gaps), in order,
    then a stock answer that rewrites the summary and leaves the skills lines and bullets as they are.
    Answering prompts get the drafts scripted with `draft` for their questions, and no answer for the rest.
    Cover letter prompts get DEFAULT_COVER_LETTER.
    Profile prompts get DEFAULT_PROFILE.
    """

    INPUT_TOKENS = 1000
    OUTPUT_TOKENS = 200

    def __init__(self) -> None:
        self._answers: dict[str, dict[str, Any] | LLMError] = {}
        self._resume_scores: dict[str, int] = {}
        self._tailorings: list[dict[str, Any] | LLMError] = []
        self._drafts: dict[str, str] = {}
        self._failure: LLMError | None = None
        self._release: threading.Event | None = None
        self._lock = threading.Lock()
        self.calls: list[LLMCall] = []

    def score(self, title: str, score: int, reasons: list[str] | None = None) -> None:
        self._answers[title] = {
            "score": score,
            "reasons": reasons or [f"Scored {score}."],
            "matched_keywords": ["Python"],
            "missing_keywords": ["Kafka"],
        }

    def score_resume(self, containing: str, score: int) -> None:
        """Score `score` whenever the resume being scored contains `containing` (such as a tailored Summary),
        whatever the job's title."""
        self._resume_scores[containing] = score

    def answer(self, title: str, answer: dict[str, Any] | LLMError) -> None:
        """Answer with exactly this output (or raise this error) for jobs with this title."""
        self._answers[title] = answer

    def tailor(self, *answers: dict[str, Any] | LLMError) -> None:
        """Answer the next tailoring prompts with these outputs (or raise these errors), in order."""
        self._tailorings.extend(answers)

    def draft(self, question: str, answer: str) -> None:
        """Answer this question with `answer` when asked to draft it."""
        self._drafts[question] = answer

    def fail(self, error: LLMError | None) -> None:
        """Every call raises `error` from now on (or, given None, answers normally again)."""
        self._failure = error

    def hold(self) -> threading.Event:
        """Block every call until the returned event is set."""
        self._release = threading.Event()
        return self._release

    def scored_titles(self) -> list[str]:
        return sorted(_title(call.prompt) for call in self.calls if call.is_scoring)

    def tailoring_calls(self) -> list[LLMCall]:
        return [call for call in self.calls if call.is_tailoring]

    def answering_calls(self) -> list[LLMCall]:
        return [call for call in self.calls if call.is_answering]

    def cover_letter_calls(self) -> list[LLMCall]:
        return [call for call in self.calls if call.is_cover_letter]

    def profile_calls(self) -> list[LLMCall]:
        return [call for call in self.calls if call.is_profile]

    def generate(
        self, *, api_key: str, model: str, system: str, prompt: str, schema: dict[str, Any], max_tokens: int
    ) -> LLMResponse:
        call = LLMCall(api_key, model, system, prompt, schema)
        if self._release is not None:
            self._release.wait(timeout=10)
        with self._lock:
            self.calls.append(call)
            tailored = self._tailorings.pop(0) if call.is_tailoring and self._tailorings else None
        if self._failure is not None:
            raise self._failure
        if call.is_answering:
            drafts = [
                {"key": question["key"], "answer": self._drafts.get(question["question"])}
                for question in _questions(prompt)
            ]
            return LLMResponse({"answers": drafts}, model, self.INPUT_TOKENS, self.OUTPUT_TOKENS)
        if call.is_cover_letter:
            return LLMResponse({"cover_letter": DEFAULT_COVER_LETTER}, model, self.INPUT_TOKENS, self.OUTPUT_TOKENS)
        if call.is_profile:
            return LLMResponse(DEFAULT_PROFILE, model, self.INPUT_TOKENS, self.OUTPUT_TOKENS)
        answer = tailored if call.is_tailoring else self._resume_score(prompt) or self._answers.get(_title(prompt))
        if isinstance(answer, LLMError):
            raise answer
        if answer is None and call.is_tailoring:
            answer = {
                "summary": [DEFAULT_TAILORED_SUMMARY],
                "skills": [],
                "bullets": [],
                "keywords": ["Python", "Kafka"],
                "gaps": [],
            }
        if answer is None:
            answer = {
                "score": 80,
                "reasons": ["Your Python experience matches the role."],
                "matched_keywords": ["Python", "PostgreSQL"],
                "missing_keywords": ["Kafka"],
            }
        return LLMResponse(answer, model, self.INPUT_TOKENS, self.OUTPUT_TOKENS)

    def _resume_score(self, prompt: str) -> dict[str, Any] | None:
        resume = re.search(r"<resume>\n(.*?)\n</resume>", prompt, re.S)
        for containing, score in self._resume_scores.items():
            if resume and containing in resume[1]:
                return {
                    "score": score,
                    "reasons": [f"Scored {score}."],
                    "matched_keywords": ["Python"],
                    "missing_keywords": [],
                }
        return None


def _questions(prompt: str) -> list[dict[str, str]]:
    match = re.search(r"<questions>\n(.+)\n</questions>", prompt, re.S)
    assert match, "not an answering prompt"
    questions: list[dict[str, str]] = json.loads(match[1])
    return questions


def _title(prompt: str) -> str:
    match = re.search(r"^Title: (.+)$", prompt, re.M)
    assert match, "not a scoring prompt"
    return match[1]
