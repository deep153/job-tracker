from typing import Any

import httpx

from job_tracker.models.posting import Posting, SalaryRange
from job_tracker.models.search_settings import WorkMode
from job_tracker.utils.html_text import html_to_text
from job_tracker.utils.salary_text import salary_from_text
from job_tracker.utils.timestamps import utc_timestamp

_WORK_MODES: dict[str, WorkMode] = {"Remote": "remote", "Hybrid": "hybrid", "OnSite": "onsite"}


class AshbyClient:
    """Reads the public Ashby job board API (api.ashbyhq.com/posting-api)."""

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def fetch(self, board_id: str) -> list[Posting]:
        response = self._http.get(
            f"https://api.ashbyhq.com/posting-api/job-board/{board_id}",
            params={"includeCompensation": "true"},
        )
        response.raise_for_status()
        # Unlisted jobs are only reachable by direct link; the company isn't advertising them.
        return [_to_posting(board_id, job) for job in response.json()["jobs"] if job.get("isListed", True)]


def _to_posting(board_id: str, job: dict[str, Any]) -> Posting:
    locations = [job["location"]] if job.get("location") else []
    locations += [extra["location"] for extra in job.get("secondaryLocations") or [] if extra.get("location")]
    work_mode = _WORK_MODES.get(job.get("workplaceType") or "")
    # A hybrid job can still be remote from some of its locations, so `isRemote` is kept separately.
    remote = job.get("isRemote")
    if remote is None and work_mode is not None:
        remote = work_mode == "remote"
    description = html_to_text(job.get("descriptionHtml") or "")
    return Posting(
        platform="ashby",
        board_id=board_id,
        external_id=job["id"],
        title=job["title"].strip(),
        locations=locations,
        remote=remote,
        work_mode=work_mode,
        salary=_salary(job.get("compensation")) or salary_from_text(description),
        description=description,
        posting_url=job["jobUrl"],
        application_url=job.get("applyUrl") or job["jobUrl"],
        updated_at=utc_timestamp(job["publishedAt"]),
    )


def _salary(compensation: dict[str, Any] | None) -> SalaryRange | None:
    for component in (compensation or {}).get("summaryComponents") or []:
        if component.get("compensationType") != "Salary" or component.get("interval") != "1 YEAR":
            continue
        low, high = component.get("minValue"), component.get("maxValue")
        if low is not None or high is not None:
            return SalaryRange(_whole(low), _whole(high), component.get("currencyCode"))
    return None


def _whole(amount: float | None) -> int | None:
    return None if amount is None else round(amount)
