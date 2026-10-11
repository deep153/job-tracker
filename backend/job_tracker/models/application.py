from dataclasses import dataclass
from typing import Literal

from job_tracker.models.resume import SkillLine

ApplicationStatus = Literal["drafting", "in_review", "failed"]

# An application in one of these is still being worked on; applying to its job again returns it.
OPEN_STATUSES: tuple[ApplicationStatus, ...] = ("drafting", "in_review")


@dataclass(frozen=True)
class ApplicationRef:
    """Which application a job has, as the job list shows it."""

    id: int
    status: ApplicationStatus


@dataclass(frozen=True)
class TailoredResume:
    """The resume version tailored for one application: the edits next to the master's text, and its files."""

    master_version: int
    directory: str
    master_summary: list[str]
    summary: list[str]
    master_skills: list[SkillLine]
    skills: list[SkillLine]
    keywords: list[str]
    covered_before: list[bool]
    covered_after: list[bool]
    page_count: int
    master_page_count: int


@dataclass(frozen=True)
class Application:
    id: int
    job_id: int
    status: ApplicationStatus
    created_at: str
    updated_at: str
    error: str | None
    cost_usd: float
    resume: TailoredResume | None
