from dataclasses import dataclass
from typing import Literal

from job_tracker.models.answers import FormAnswer
from job_tracker.models.resume import SkillLine

ApplicationStatus = Literal["drafting", "in_review", "submitting", "submitted", "needs_manual", "failed"]

# An application in one of these is still being worked on; applying to its job again returns it.
OPEN_STATUSES: tuple[ApplicationStatus, ...] = ("drafting", "in_review")

# An application in one of these has been (or is being) sent, so its job can't be applied to again. A job has at
# most one.
SENT_STATUSES: tuple[ApplicationStatus, ...] = ("submitting", "submitted", "needs_manual")


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
    submitted_at: str | None = None
    screenshot: bool = False  # of the form when submitting it failed
    cover_letter: str | None = None  # only when the form has a cover letter field

    @property
    def editable(self) -> bool:
        """In review, or back with me after sending it failed."""
        return self.status == "in_review" or self.submit_failed

    @property
    def submit_failed(self) -> bool:
        """Failed while submitting, after review (a tailoring failure has no resume); approving retries it."""
        return self.status == "failed" and self.resume is not None and self.answers is not None

    @property
    def cover_letter_file(self) -> bool:
        """Whether the cover letter is uploaded as a file (rather than only pasted into a text box)."""
        return any(a.source == "cover_letter" and a.field.kind == "file" for a in self.answers or [])

    @property
    def unanswered(self) -> list[FormAnswer]:
        """Questions that still need my input: required ones, and EEO questions I have no saved choice for."""
        return [answer for answer in self.answers or [] if answer.needs_input]

    @property
    def approval_problem(self) -> str | None:
        """Why the application can't be approved yet, or None when it can."""
        if self.status in SENT_STATUSES:
            return "This application has already been sent."
        if not self.editable or self.resume is None:
            return "Only an application in review can be approved."
        if self.form_error is not None:
            return self.form_error
        if self.unanswered:
            labels = ", ".join(f"“{answer.field.label}”" for answer in self.unanswered)
            return f"Answer these questions first: {labels}."
        if self.resume.page_count > self.resume.master_page_count:
            return (
                f"The tailored resume runs to {self.resume.page_count} pages, longer than your "
                f"{self.resume.master_page_count}-page master. Shorten it first."
            )
        return None
