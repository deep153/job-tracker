from dataclasses import dataclass, field
from typing import Literal

from job_tracker.models.job import Rule
from job_tracker.models.platform import Platform

RunStatus = Literal["running", "finished", "failed", "interrupted"]
RunStage = Literal["discovering", "fetching", "scoring"]
RunErrorKind = Literal["search", "board", "scoring"]


@dataclass(frozen=True)
class RunError:
    """Something that went wrong during a run without stopping it. Board errors name the board."""

    kind: RunErrorKind
    message: str
    platform: Platform | None = None
    board_id: str | None = None


@dataclass(frozen=True)
class Run:
    id: int
    status: RunStatus
    stage: RunStage
    started_at: str
    finished_at: str | None
    search_queries: int = 0
    search_queries_capped: bool = False
    companies_discovered: int = 0
    companies_total: int = 0
    companies_fetched: int = 0
    new_jobs: int = 0
    updated_jobs: int = 0
    closed_jobs: int = 0
    filtered_out: dict[Rule, int] = field(default_factory=dict)
    errors: list[RunError] = field(default_factory=list)
    scoring_total: int = 0
    scored_jobs: int = 0
    matched_jobs: int = 0
    ai_cost_usd: float = 0
