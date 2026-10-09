from dataclasses import replace
from typing import Any

from job_tracker.models.posting import Posting

_POSTING = Posting(
    platform="greenhouse",
    board_id="acme",
    external_id="1",
    title="Backend Engineer",
    locations=["New York, NY"],
    remote=False,
    work_mode=None,
    salary=None,
    description="Build payment APIs in Python.",
    posting_url="https://job-boards.greenhouse.io/acme/jobs/1",
    application_url="https://job-boards.greenhouse.io/acme/jobs/1#app",
    updated_at="2026-10-01T09:00:00+00:00",
)


def posting(**changes: Any) -> Posting:
    return replace(_POSTING, **changes)
