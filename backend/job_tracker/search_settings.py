import json
import sqlite3
from dataclasses import asdict, dataclass, field
from typing import Literal

from job_tracker.companies import Platform
from job_tracker.db import Database
from job_tracker.llm import DEFAULT_SCORING_MODEL, DEFAULT_TAILORING_MODEL

DEFAULT_MIN_SCORE = 70

WorkMode = Literal["remote", "hybrid", "onsite"]
Seniority = Literal["intern", "junior", "mid", "senior", "staff", "principal"]


@dataclass(frozen=True)
class SearchSettings:
    """What I'm looking for: drives company discovery and the hard filters."""

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


def read_search(conn: sqlite3.Connection) -> SearchSettings:
    """The saved search settings, read inside the caller's transaction."""
    row = conn.execute("SELECT value FROM settings WHERE key = 'search'").fetchone()
    return SearchSettings(**json.loads(row["value"])) if row else SearchSettings()


class SettingsStore:
    """Single-user settings and secrets, kept in the local database only."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def search(self) -> SearchSettings:
        with self._db.connect() as conn:
            return read_search(conn)

    def save_search(self, settings: SearchSettings) -> None:
        self._set("search", json.dumps(asdict(settings)))

    def search_api_key(self) -> str | None:
        return self._get("search_api_key") or None

    def set_search_api_key(self, key: str) -> None:
        self._set("search_api_key", key)

    def anthropic_api_key(self) -> str | None:
        return self._get("anthropic_api_key") or None

    def set_anthropic_api_key(self, key: str) -> None:
        self._set("anthropic_api_key", key)

    def scoring_model(self) -> str:
        return self._get("scoring_model") or DEFAULT_SCORING_MODEL

    def tailoring_model(self) -> str:
        return self._get("tailoring_model") or DEFAULT_TAILORING_MODEL

    def set_models(self, scoring: str, tailoring: str) -> None:
        self._set("scoring_model", scoring)
        self._set("tailoring_model", tailoring)

    def _get(self, key: str) -> str | None:
        with self._db.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row["value"])

    def _set(self, key: str, value: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
