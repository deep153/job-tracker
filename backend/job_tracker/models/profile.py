from dataclasses import dataclass
from typing import Literal

from job_tracker.models.answers import AnswerCategory

# Read from my resume, or a standard question a resume can't answer.
ProfileSection = Literal["resume", "questions"]


@dataclass(frozen=True)
class ProfileField:
    """One proposed answer-bank entry, worded the way application forms ask it."""

    question: str
    category: AnswerCategory
    value: str  # what my resume (or search settings) says; empty when nothing was found
    current: str | None  # my answer bank's answer to the same question, if I have one
    section: ProfileSection


@dataclass(frozen=True)
class ProfileProposal:
    fields: list[ProfileField]


@dataclass(frozen=True)
class ProfileAnswer:
    """My confirmed answer to one field. An existing answer to the same question is replaced only if `replace`."""

    question: str
    category: AnswerCategory
    answer: str
    replace: bool
