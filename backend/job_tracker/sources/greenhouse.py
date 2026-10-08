import html
from typing import Any

import httpx

from job_tracker.html_text import html_to_text
from job_tracker.postings import Posting
from job_tracker.salary_text import salary_from_text


class GreenhouseSource:
    """Reads the public Greenhouse job board API (boards-api.greenhouse.io)."""

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def fetch(self, board_id: str) -> list[Posting]:
        response = self._http.get(
            f"https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs",
            params={"content": "true"},
        )
        response.raise_for_status()
        return [_to_posting(board_id, job) for job in response.json()["jobs"]]


def _to_posting(board_id: str, job: dict[str, Any]) -> Posting:
    location = (job.get("location") or {}).get("name") or ""
    # Greenhouse entity-escapes the HTML in `content`.
    description = html_to_text(html.unescape(job.get("content") or ""))
    return Posting(
        platform="greenhouse",
        board_id=board_id,
        external_id=str(job["id"]),
        title=job["title"],
        locations=[location] if location else [],
        remote=True if "remote" in location.lower() else None,
        # The board API has no pay field; companies state pay ranges in the description.
        salary=salary_from_text(description),
        description=description,
        posting_url=job["absolute_url"],
        application_url=job["absolute_url"],
        updated_at=job["updated_at"],
    )
