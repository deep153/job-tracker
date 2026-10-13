from typing import Annotated

from pydantic import BaseModel, Field

from job_tracker.models.answers import AnswerCategory

AnswerText = Annotated[str, Field(max_length=10_000)]


class BankEntryIn(BaseModel):
    question: str = Field(max_length=500)
    answer: AnswerText
    category: AnswerCategory


class FormAnswersIn(BaseModel):
    """Answers I typed in review, by question key; an empty or null answer clears it."""

    answers: dict[Annotated[str, Field(max_length=200)], AnswerText | None] = Field(max_length=500)
