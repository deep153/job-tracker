from typing import Protocol

import httpx

from job_tracker.clients.job_boards.ashby import AshbyClient
from job_tracker.clients.job_boards.greenhouse import GreenhouseClient
from job_tracker.clients.job_boards.lever import LeverClient
from job_tracker.models.platform import Platform
from job_tracker.models.posting import Posting


class JobBoardClient(Protocol):
    def fetch(self, board_id: str) -> list[Posting]:
        """Every posting on a company's board. Raises httpx errors when the board can't be read."""
        ...


def job_board_clients(http: httpx.Client) -> dict[Platform, JobBoardClient]:
    return {"greenhouse": GreenhouseClient(http), "lever": LeverClient(http), "ashby": AshbyClient(http)}
