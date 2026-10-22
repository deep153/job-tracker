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


class BulletIn(BaseModel):
    """An experience bullet's text after its label, by paragraph index."""

    index: int
    text: str = Field(max_length=2000)


class GapIn(BaseModel):
    """A gap to add to my skills, and the Skills line (counted from 0) to put it on."""

    keyword: Skill
    line: int


class TailoredResumeIn(BaseModel):
    """My edits in review: one text per Summary paragraph, the skills for each skills line, and the bullets I
    changed (the others keep their text)."""

    summary: list[SummaryText] = Field(max_length=20)
    skills: list[Annotated[list[Skill], Field(max_length=200)]] = Field(max_length=50)
    bullets: list[BulletIn] = Field(default_factory=list, max_length=200)
