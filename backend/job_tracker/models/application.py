from dataclasses import dataclass
from typing import Literal

from job_tracker.models.answers import FormAnswer
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
    answers: list[FormAnswer] | None = None  # None until the form is read, or when it can't be
    form_error: str | None = None  # why the form couldn't be read, so the application can't be submitted

    @property
    def unanswered(self) -> list[FormAnswer]:
        """Required questions that still need my input."""
        return [answer for answer in self.answers or [] if answer.needs_input]

    @property
    def approval_problem(self) -> str | None:
        """Why the application can't be approved yet, or None when it can."""
        if self.status != "in_review" or self.resume is None:
            return "Only an application in review can be approved."
        if self.form_error is not None:
            return self.form_error
        if self.unanswered:
            labels = ", ".join(f"“{answer.field.label}”" for answer in self.unanswered)
            return f"Answer the required questions first: {labels}."
        if self.resume.page_count > self.resume.master_page_count:
            return (
                f"The tailored resume runs to {self.resume.page_count} pages, longer than your "
                f"{self.resume.master_page_count}-page master. Shorten it first."
            )
        return None
