from typing import Any

import httpx

from job_tracker.models.posting import Posting, SalaryRange
from job_tracker.models.search_settings import WorkMode
from job_tracker.utils.html_text import html_to_text
from job_tracker.utils.salary_text import salary_from_text
from job_tracker.utils.timestamps import utc_timestamp

_WORK_MODES: dict[str, WorkMode] = {"remote": "remote", "hybrid": "hybrid", "onsite": "onsite"}


class LeverClient:
    """Reads the public Lever postings API (api.lever.co)."""

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def fetch(self, board_id: str) -> list[Posting]:
        response = self._http.get(f"https://api.lever.co/v0/postings/{board_id}", params={"mode": "json"})
        response.raise_for_status()
        return [_to_posting(board_id, job) for job in response.json()]


def _to_posting(board_id: str, job: dict[str, Any]) -> Posting:
    categories = job.get("categories") or {}
    locations = categories.get("allLocations") or ([categories["location"]] if categories.get("location") else [])
    # "unspecified" (or missing) means the company didn't say.
    work_mode = _WORK_MODES.get(job.get("workplaceType") or "")
    if work_mode is None:
        remote = True if any("remote" in where.lower() for where in locations) else None
    else:
        remote = work_mode == "remote"
    # The page shows the intro, then each titled list (responsibilities, requirements...), then closing notes.
    sections = [job.get("description") or ""]
    for section in job.get("lists") or []:
        sections.append(f"<h3>{section.get('text') or ''}</h3><ul>{section.get('content') or ''}</ul>")
    sections.append(job.get("additional") or "")
    description = html_to_text("".join(sections))
    return Posting(
        platform="lever",
        board_id=board_id,
        external_id=job["id"],
        title=job["text"].strip(),
        locations=locations,
        remote=remote,
        work_mode=work_mode,
        salary=_salary(job.get("salaryRange")) or salary_from_text(description),
        description=description,
        posting_url=job["hostedUrl"],
        application_url=job.get("applyUrl") or job["hostedUrl"],
        # Lever only publishes when a posting was created, in epoch milliseconds.
        updated_at=utc_timestamp(job["createdAt"]),
    )


def _salary(salary_range: dict[str, Any] | None) -> SalaryRange | None:
    if not salary_range or salary_range.get("interval") != "per-year-salary":
        return None
    low, high = salary_range.get("min"), salary_range.get("max")
    if low is None and high is None:
        return None
    return SalaryRange(low, high, salary_range.get("currency"))
