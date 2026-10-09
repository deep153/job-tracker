from dataclasses import dataclass, field
from typing import Literal

from job_tracker.models.platform import Platform

DEFAULT_MIN_SCORE = 70

WorkMode = Literal["remote", "hybrid", "onsite"]
Seniority = Literal["intern", "junior", "mid", "senior", "staff", "principal"]


@dataclass(frozen=True)
class SearchSettings:
    """What I'm looking for: drives company discovery, the hard filters and which scores count as matches."""

    roles: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    work_modes: list[WorkMode] = field(default_factory=list)
    platforms: list[Platform] = field(default_factory=list)
    excluded_keywords: list[str] = field(default_factory=list)
    seniority: Seniority | None = None
    years_experience: int | None = None
    needs_sponsorship: bool = False
    min_salary: int | None = None
    min_score: int = DEFAULT_MIN_SCORE

    def missing(self, has_search_key: bool) -> list[str]:
        """Human-readable list of what still has to be set before a run can start."""
        missing = []
        if not self.roles:
            missing.append("Add at least one role.")
        if not self.locations and "remote" not in self.work_modes:
            missing.append("Add a location or choose remote.")
        if not self.platforms:
            missing.append("Turn on at least one job board platform.")
        if not has_search_key:
            missing.append("Add your search API key.")
        return missing
