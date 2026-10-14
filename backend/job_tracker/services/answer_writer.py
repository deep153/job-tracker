"""The Answer Writer: drafts answers to an application form's open-ended questions from my resume and the job."""

import json
from dataclasses import dataclass
from typing import Any

from job_tracker.clients.claude import LLM, LLMError
from job_tracker.models.answers import FormField
from job_tracker.models.job import Job
from job_tracker.services.fit_scorer import job_text

MAX_OUTPUT_TOKENS = 4_000
MAX_ANSWER_CHARS = 5_000

SYSTEM_PROMPT = """You draft answers to the open-ended questions on one job application, for the job seeker \
whose resume you're given. They will review and edit every draft before anything is sent.

Rules:
- Never invent experience, employers, job titles, dates, metrics, education, skills or personal facts. Use only \
what the resume and the job posting state.
- Write in the first person, plainly and specifically, connecting the resume to what the posting asks for. Keep \
each answer short: a few sentences unless the question asks for more.
- Give no answer (null) for a question you can't answer from the resume and the posting alone, such as one \
asking for a personal fact, a preference, a salary, a date, or a link the resume doesn't give, or an optional \
"anything else?" box with nothing useful to add."""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "The question's key, as given."},
                    "answer": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                },
                "required": ["key", "answer"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["answers"],
    "additionalProperties": False,
}

_INVALID = "Claude's drafted answers didn't have the expected fields."


@dataclass(frozen=True)
class DraftResult:
    answers: dict[str, str]  # by question key; questions it couldn't answer are left out
    model: str
    input_tokens: int
    output_tokens: int


def build_prompt(resume_text: str, job: Job, questions: list[FormField]) -> str:
    listed = json.dumps([{"key": field.key, "question": field.label} for field in questions], ensure_ascii=False)
    return "\n\n".join(
        [
            f"<resume>\n{resume_text}\n</resume>",
            f"<job>\n{job_text(job)}\n</job>",
            f"<questions>\n{listed}\n</questions>",
            "Draft my answer to each question.",
        ]
    )


class AnswerWriter:
    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    def draft(self, api_key: str, model: str, resume_text: str, job: Job, questions: list[FormField]) -> DraftResult:
        """Raises LLMError if the call fails or the answer doesn't make sense."""
        response = self._llm.generate(
            api_key=api_key,
            model=model,
            system=SYSTEM_PROMPT,
            prompt=build_prompt(resume_text, job, questions),
            schema=SCHEMA,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        drafts = response.data.get("answers")
        if not isinstance(drafts, list):
            raise LLMError(_INVALID)
        asked = {field.key for field in questions}
        answers: dict[str, str] = {}
        for draft in drafts:
            if not isinstance(draft, dict) or not isinstance(draft.get("key"), str):
                raise LLMError(_INVALID)
            text = draft.get("answer")
            if draft["key"] in asked and isinstance(text, str) and text.strip():
                answers[draft["key"]] = text.strip()[:MAX_ANSWER_CHARS]
        return DraftResult(answers, response.model, response.input_tokens, response.output_tokens)
