from dataclasses import dataclass

from job_tracker.models.platform import Platform


@dataclass(frozen=True)
class Company:
    id: int
    platform: Platform
    board_id: str
    discovered_at: str
    discovered_query: str
    blocked: bool
    last_fetched_at: str | None
    last_error: str | None
    open_jobs: int


@dataclass(frozen=True)
class DiscoveredBoard:
    """A company job board found by web search, and the query that found it."""

    platform: Platform
    board_id: str
    query: str
