from dataclasses import dataclass

from job_tracker.companies import Platform


@dataclass(frozen=True)
class SalaryRange:
    minimum: int | None
    maximum: int | None
    currency: str | None


@dataclass(frozen=True)
class Posting:
    """A job posting normalized from any job board platform."""

    platform: Platform
    board_id: str
    external_id: str
    title: str
    locations: list[str]
    remote: bool | None
    salary: SalaryRange | None
    description: str
    posting_url: str
    application_url: str
    updated_at: str
