import json
import logging
import sqlite3
import threading
from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

import httpx

from job_tracker.board_sync import sync_board
from job_tracker.companies import Platform
from job_tracker.db import Database
from job_tracker.discovery import WebSearch, discover
from job_tracker.postings import Posting
from job_tracker.search_settings import SearchSettings, SettingsStore
from job_tracker.sources import JobBoardSource

log = logging.getLogger(__name__)

MAX_PARALLEL_FETCHES = 8


def _now() -> str:
    return datetime.now(UTC).isoformat()


def describe_fetch_error(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        if status == 404:
            return "Board not found (HTTP 404)."
        return f"The board returned HTTP {status}."
    if isinstance(error, httpx.TimeoutException):
        return "The board took too long to respond."
    if isinstance(error, httpx.TransportError):
        return "Couldn't connect to the board."
    return f"Unexpected error: {error}"


class RunAlreadyActive(Exception):
    pass


class SearchSettingsIncomplete(Exception):
    def __init__(self, missing: list[str]) -> None:
        super().__init__(missing)
        self.missing = missing


class RunService:
    """Executes job runs in the background, one at a time: discover companies, then fetch them."""

    def __init__(
        self,
        db: Database,
        settings: SettingsStore,
        search: WebSearch,
        sources: Mapping[Platform, JobBoardSource],
    ) -> None:
        self._db = db
        self._settings = settings
        self._search = search
        self._sources = sources
        self._start_lock = threading.Lock()
        with self._db.connect() as conn:
            # A run still marked running belongs to a backend process that has since stopped.
            conn.execute(
                "UPDATE runs SET status = 'interrupted', finished_at = ? WHERE status = 'running'", (_now(),)
            )

    def start(self) -> int:
        search_settings = self._settings.search()
        api_key = self._settings.search_api_key()
        missing = search_settings.missing(has_search_key=api_key is not None)
        if missing or api_key is None:
            raise SearchSettingsIncomplete(missing)
        with self._start_lock, self._db.connect() as conn:
            if conn.execute("SELECT 1 FROM runs WHERE status = 'running'").fetchone():
                raise RunAlreadyActive
            run_id = conn.execute(
                "INSERT INTO runs (status, stage, started_at) VALUES ('running', 'discovering', ?)", (_now(),)
            ).lastrowid
        assert run_id is not None
        threading.Thread(target=self._execute, args=(run_id, search_settings, api_key), daemon=True).start()
        return run_id

    def _execute(self, run_id: int, search_settings: SearchSettings, api_key: str) -> None:
        status = "finished"
        try:
            self._discover(run_id, search_settings, api_key)
            self._fetch_all(run_id, self._companies_to_fetch(search_settings))
        except Exception:
            log.exception("run %s failed", run_id)
            status = "failed"
        with self._db.connect() as conn:
            conn.execute("UPDATE runs SET status = ?, finished_at = ? WHERE id = ?", (status, _now(), run_id))

    def _discover(self, run_id: int, search_settings: SearchSettings, api_key: str) -> None:
        result = discover(self._search, api_key, search_settings)
        found_at = _now()
        with self._db.connect() as conn:
            discovered = 0
            for board in result.boards:
                discovered += conn.execute(
                    """
                    INSERT OR IGNORE INTO companies (platform, board_id, discovered_at, discovered_query)
                    VALUES (?, ?, ?, ?)
                    """,
                    (board.platform, board.board_id, found_at, board.query),
                ).rowcount
            conn.execute(
                """
                UPDATE runs SET stage = 'fetching', search_queries = ?, search_queries_capped = ?,
                    companies_discovered = ?
                WHERE id = ?
                """,
                (result.queries_made, result.capped, discovered, run_id),
            )
            if result.error:
                _append_error(conn, run_id, {"kind": "search", "platform": None, "board_id": None, "message": result.error})

    def _companies_to_fetch(self, search_settings: SearchSettings) -> list[tuple[Platform, str]]:
        platforms = [p for p in search_settings.platforms if p in self._sources]
        if not platforms:
            return []
        with self._db.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT platform, board_id FROM companies
                WHERE blocked = 0 AND platform IN ({",".join("?" * len(platforms))})
                ORDER BY id
                """,
                platforms,
            ).fetchall()
        return [(row["platform"], row["board_id"]) for row in rows]

    def _fetch_all(self, run_id: int, companies: list[tuple[Platform, str]]) -> None:
        with self._db.connect() as conn:
            conn.execute("UPDATE runs SET companies_total = ? WHERE id = ?", (len(companies), run_id))
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_FETCHES) as pool:
            futures: dict[Future[list[Posting]], tuple[Platform, str]] = {
                pool.submit(self._sources[platform].fetch, board_id): (platform, board_id)
                for platform, board_id in companies
            }
            for future in as_completed(futures):
                platform, board_id = futures[future]
                try:
                    postings = future.result()
                except Exception as error:
                    self._record_failure(run_id, platform, board_id, describe_fetch_error(error))
                else:
                    self._record_success(run_id, platform, board_id, postings)

    def _record_success(self, run_id: int, platform: Platform, board_id: str, postings: list[Posting]) -> None:
        seen_at = _now()
        with self._db.connect() as conn:
            result = sync_board(conn, platform, board_id, postings, seen_at)
            conn.execute(
                "UPDATE companies SET last_fetched_at = ?, last_error = NULL WHERE platform = ? AND board_id = ?",
                (seen_at, platform, board_id),
            )
            conn.execute(
                """
                UPDATE runs SET companies_fetched = companies_fetched + 1, new_jobs = new_jobs + ?,
                    updated_jobs = updated_jobs + ?, closed_jobs = closed_jobs + ?
                WHERE id = ?
                """,
                (result.new, result.updated, result.closed, run_id),
            )

    def _record_failure(self, run_id: int, platform: Platform, board_id: str, message: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE companies SET last_error = ? WHERE platform = ? AND board_id = ?",
                (message, platform, board_id),
            )
            conn.execute("UPDATE runs SET companies_fetched = companies_fetched + 1 WHERE id = ?", (run_id,))
            _append_error(conn, run_id, {"kind": "board", "platform": platform, "board_id": board_id, "message": message})


def _append_error(conn: sqlite3.Connection, run_id: int, error: dict[str, Any]) -> None:
    errors = json.loads(conn.execute("SELECT errors FROM runs WHERE id = ?", (run_id,)).fetchone()[0])
    errors.append(error)
    conn.execute("UPDATE runs SET errors = ? WHERE id = ?", (json.dumps(errors), run_id))
