from typing import Annotated

from pydantic import BaseModel, Field

SummaryText = Annotated[str, Field(max_length=5000)]
Skill = Annotated[str, Field(max_length=200)]


class TailoredResumeIn(BaseModel):
    """My edits in review: one text per Summary paragraph, and the skills for each skills line."""

    summary: list[SummaryText] = Field(max_length=20)
    skills: list[Annotated[list[Skill], Field(max_length=200)]] = Field(max_length=50)
