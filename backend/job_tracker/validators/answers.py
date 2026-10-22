from typing import Annotated

from pydantic import BaseModel, Field

from job_tracker.models.answers import AnswerCategory

AnswerText = Annotated[str, Field(max_length=10_000)]


class BankEntryIn(BaseModel):
    question: str = Field(max_length=500)
    answer: AnswerText
    category: AnswerCategory


class ProfileAnswerIn(BaseModel):
    question: str = Field(max_length=500)
    category: AnswerCategory
    answer: AnswerText
    replace: bool = False


class ProfileIn(BaseModel):
    """My confirmed profile answers; empty ones are skipped."""

    answers: list[ProfileAnswerIn] = Field(max_length=100)


class FormAnswersIn(BaseModel):
    """Answers I typed in review, by question key; an empty or null answer clears it."""

    answers: dict[Annotated[str, Field(max_length=200)], AnswerText | None] = Field(max_length=500)


class SaveToBankIn(BaseModel):
    """The question whose current answer to save into my answer bank."""

    key: str = Field(max_length=200)
