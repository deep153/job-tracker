from dataclasses import dataclass
from typing import Literal

from job_tracker.models.posting import Posting

Rule = Literal["role", "excluded_keyword", "location", "seniority", "experience", "sponsorship", "salary"]

RULES: tuple[Rule, ...] = ("role", "excluded_keyword", "location", "seniority", "experience", "sponsorship", "salary")


@dataclass(frozen=True)
class Rejection:
    """Why the hard filters dropped a job."""

    rule: Rule
    reason: str


@dataclass(frozen=True)
class FitResult:
    """The Fit Scorer's verdict on one job, with what the call used."""

    score: int
    reasons: list[str]
    matched_keywords: list[str]
    missing_keywords: list[str]
    model: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class FitScore:
    """A saved fit score for a job against one resume version."""

    score: int
    reasons: list[str]
    matched_keywords: list[str]
    missing_keywords: list[str]
    model: str
    resume_version: int
    scored_at: str


@dataclass(frozen=True)
class Job:
    """A stored posting with the hard filters' verdict and its latest fit score."""

    id: int
    posting: Posting
    content_hash: str
    closed: bool
    rejection: Rejection | None
    score: FitScore | None = None
