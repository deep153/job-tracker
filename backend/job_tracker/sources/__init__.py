from typing import Protocol

import httpx

from job_tracker.companies import Platform
from job_tracker.postings import Posting
from job_tracker.sources.greenhouse import GreenhouseSource


class JobBoardSource(Protocol):
    def fetch(self, board_id: str) -> list[Posting]: ...


def job_board_sources(http: httpx.Client) -> dict[Platform, JobBoardSource]:
    return {"greenhouse": GreenhouseSource(http)}
