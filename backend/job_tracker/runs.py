import json
import logging
import sqlite3
import threading
from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import httpx

from job_tracker.board_sync import sync_board
from job_tracker.companies import Platform
from job_tracker.db import Database
from job_tracker.postings import Posting
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


class RunService:
    """Executes job runs in the background, one at a time."""

    def __init__(self, db: Database, sources: Mapping[Platform, JobBoardSource]) -> None:
        self._db = db
        self._sources = sources
        self._start_lock = threading.Lock()
        with self._db.connect() as conn:
            # A run still marked running belongs to a backend process that has since stopped.
            conn.execute(
                "UPDATE runs SET status = 'interrupted', finished_at = ? WHERE status = 'running'", (_now(),)
            )

    def start(self) -> int:
        with self._start_lock, self._db.connect() as conn:
            if conn.execute("SELECT 1 FROM runs WHERE status = 'running'").fetchone():
                raise RunAlreadyActive
            companies = conn.execute("SELECT platform, board_id FROM companies WHERE enabled = 1").fetchall()
            run_id = conn.execute(
                "INSERT INTO runs (status, started_at, companies_total) VALUES ('running', ?, ?)",
                (_now(), len(companies)),
            ).lastrowid
        assert run_id is not None
        threading.Thread(target=self._execute, args=(run_id, companies), daemon=True).start()
        return run_id

    def _execute(self, run_id: int, companies: list[sqlite3.Row]) -> None:
        status = "finished"
        try:
            self._fetch_all(run_id, companies)
        except Exception:
            log.exception("run %s failed", run_id)
            status = "failed"
        with self._db.connect() as conn:
            conn.execute("UPDATE runs SET status = ?, finished_at = ? WHERE id = ?", (status, _now(), run_id))

    def _fetch_all(self, run_id: int, companies: list[sqlite3.Row]) -> None:
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_FETCHES) as pool:
            futures: dict[Future[list[Posting]], tuple[Platform, str]] = {
                pool.submit(self._sources[c["platform"]].fetch, c["board_id"]): (c["platform"], c["board_id"])
                for c in companies
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
            errors = json.loads(conn.execute("SELECT errors FROM runs WHERE id = ?", (run_id,)).fetchone()[0])
            errors.append({"platform": platform, "board_id": board_id, "message": message})
            conn.execute(
                "UPDATE runs SET companies_fetched = companies_fetched + 1, errors = ? WHERE id = ?",
                (json.dumps(errors), run_id),
            )
