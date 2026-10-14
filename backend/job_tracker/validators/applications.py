from typing import Annotated, Literal

from pydantic import BaseModel, Field

from job_tracker.models.application import TrackedStatus

SummaryText = Annotated[str, Field(max_length=5000)]
Skill = Annotated[str, Field(max_length=200)]


class StatusIn(BaseModel):
    """`submitted` marks an application I finished by hand; the rest record what I heard back."""

    status: Literal["submitted", TrackedStatus]


class CoverLetterIn(BaseModel):
    text: str = Field(max_length=10_000)


class TailoredResumeIn(BaseModel):
    """My edits in review: one text per Summary paragraph, and the skills for each skills line."""

    summary: list[SummaryText] = Field(max_length=20)
    skills: list[Annotated[list[Skill], Field(max_length=200)]] = Field(max_length=50)
