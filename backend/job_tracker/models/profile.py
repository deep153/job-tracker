from dataclasses import dataclass, field
from typing import Literal

from job_tracker.models.answers import AnswerCategory

# Read from my resume, taken from the chosen education entry, or a standard question a resume can't answer.
ProfileSection = Literal["resume", "education", "questions"]


@dataclass(frozen=True)
class ProfileField:
    """One proposed answer-bank entry, worded the way application forms ask it."""

    question: str
    category: AnswerCategory
    value: str  # what my resume (or search settings) says; empty when nothing was found
    current: str | None  # my answer bank's answer to the same question, if I have one
    section: ProfileSection


@dataclass(frozen=True)
class Education:
    school: str
    degree: str  # written in full, such as "Master of Science"
    discipline: str
    end_month: str  # the month's full name
    end_year: str


@dataclass(frozen=True)
class ProfileProposal:
    fields: list[ProfileField]
    education: list[Education] = field(default_factory=list)  # as the resume lists them
    selected_education: int | None = None  # the entry the education fields come from: the highest degree
    ai_note: str | None = None  # why my name, location and education weren't read, if they weren't


@dataclass(frozen=True)
class ProfileAnswer:
    """My confirmed answer to one field. An existing answer to the same question is replaced only if `replace`."""

    question: str
    category: AnswerCategory
    answer: str
    replace: bool
