import json
import logging
import sqlite3
import threading
from collections import Counter
from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from job_tracker.board_sync import sync_board
from job_tracker.companies import Platform
from job_tracker.db import Database
from job_tracker.discovery import WebSearch, discover
from job_tracker.filtering import refilter_jobs
from job_tracker.llm import LLM, LLMError
from job_tracker.postings import Posting
from job_tracker.resume import MasterResume, ResumeStore
from job_tracker.scoring import FitScore, record_usage, save_score, score_job
from job_tracker.search_settings import SearchSettings, SettingsStore
from job_tracker.sources import JobBoardSource

log = logging.getLogger(__name__)

MAX_PARALLEL_FETCHES = 8
MAX_PARALLEL_SCORES = 4


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


class SetupIncomplete(Exception):
    def __init__(self, missing: list[str]) -> None:
        super().__init__(missing)
        self.missing = missing


@dataclass(frozen=True)
class RunInputs:
    """Everything a run uses, as it was when the run started."""

    search_settings: SearchSettings
    search_api_key: str
    anthropic_api_key: str
    scoring_model: str
    resume: MasterResume


class RunService:
    """Executes job runs in the background, one at a time: discover companies, fetch and filter their jobs,
    then score the jobs that passed the filters."""

    def __init__(
        self,
        db: Database,
        settings: SettingsStore,
        resumes: ResumeStore,
        search: WebSearch,
        sources: Mapping[Platform, JobBoardSource],
        llm: LLM,
    ) -> None:
        self._db = db
        self._settings = settings
        self._resumes = resumes
        self._search = search
        self._sources = sources
        self._llm = llm
        self._start_lock = threading.Lock()
        with self._db.connect() as conn:
            # A run still marked running belongs to a backend process that has since stopped.
            conn.execute(
                "UPDATE runs SET status = 'interrupted', finished_at = ? WHERE status = 'running'", (_now(),)
            )

    def missing(self) -> list[str]:
        """Human-readable list of what still has to be set up before a run can start."""
        missing = self._settings.search().missing(has_search_key=self._settings.search_api_key() is not None)
        if self._settings.anthropic_api_key() is None:
            missing.append("Add your Anthropic API key in Settings.")
        if self._resumes.current() is None:
            missing.append("Upload your resume and mark its Summary and Skills.")
        elif self._resumes.master() is None:
            missing.append("Mark your resume's Summary and Skills.")
        return missing

    def start(self) -> int:
        inputs = self._inputs()
        with self._start_lock, self._db.connect() as conn:
            if conn.execute("SELECT 1 FROM runs WHERE status = 'running'").fetchone():
                raise RunAlreadyActive
            run_id = conn.execute(
                "INSERT INTO runs (status, stage, started_at) VALUES ('running', 'discovering', ?)", (_now(),)
            ).lastrowid
        assert run_id is not None
        threading.Thread(target=self._execute, args=(run_id, inputs), daemon=True).start()
        return run_id

    def _inputs(self) -> RunInputs:
        missing = self.missing()
        search_api_key = self._settings.search_api_key()
        anthropic_api_key = self._settings.anthropic_api_key()
        resume = self._resumes.master()
        if missing or search_api_key is None or anthropic_api_key is None or resume is None:
            raise SetupIncomplete(missing)
        return RunInputs(
            self._settings.search(), search_api_key, anthropic_api_key, self._settings.scoring_model(), resume
        )

    def _execute(self, run_id: int, inputs: RunInputs) -> None:
        status = "finished"
        try:
            self._discover(run_id, inputs.search_settings, inputs.search_api_key)
            self._fetch_all(run_id, self._companies_to_fetch(inputs.search_settings))
            self._score_all(run_id, inputs)
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
            rejected = refilter_jobs(conn, result.to_filter)
            if rejected:
                row = conn.execute("SELECT filtered_out FROM runs WHERE id = ?", (run_id,)).fetchone()
                totals = Counter(json.loads(row["filtered_out"])) + rejected
                conn.execute("UPDATE runs SET filtered_out = ? WHERE id = ?", (json.dumps(totals), run_id))
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

    def _score_all(self, run_id: int, inputs: RunInputs) -> None:
        """Score every open job that passed the filters and has no score for this resume version and content."""
        with self._db.connect() as conn:
            jobs = conn.execute(
                """
                SELECT jobs.* FROM jobs
                JOIN companies ON companies.platform = jobs.platform AND companies.board_id = jobs.board_id
                WHERE jobs.closed = 0 AND companies.blocked = 0 AND jobs.rejected_rule IS NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM scores WHERE scores.job_id = jobs.id AND scores.resume_version = ?
                            AND scores.content_hash = jobs.content_hash
                    )
                ORDER BY jobs.id
                """,
                (inputs.resume.version,),
            ).fetchall()
            conn.execute("UPDATE runs SET stage = 'scoring', scoring_total = ? WHERE id = ?", (len(jobs), run_id))
        failed: list[str] = []
        stopped = False
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_SCORES) as pool:
            futures: dict[Future[FitScore], sqlite3.Row] = {
                pool.submit(
                    score_job,
                    self._llm,
                    inputs.anthropic_api_key,
                    inputs.scoring_model,
                    inputs.resume,
                    inputs.search_settings,
                    job,
                ): job
                for job in jobs
            }
            for future in as_completed(futures):
                if future.cancelled():
                    continue
                job = futures[future]
                try:
                    fit = future.result()
                except LLMError as error:
                    if error.fatal and not stopped:
                        # Every later call would fail the same way; keep the answers already on their way.
                        stopped = True
                        for pending in futures:
                            pending.cancel()
                        with self._db.connect() as conn:
                            _append_error(conn, run_id, _scoring_error(f"Scoring stopped: {error.message}"))
                    elif not error.fatal:
                        failed.append(error.message)
                    continue
                except Exception as error:
                    log.exception("scoring job %s failed", job["id"])
                    failed.append(f"Unexpected error: {error}")
                    continue
                self._record_score(run_id, job, inputs, fit)
        if failed:
            noun = "job" if len(failed) == 1 else "jobs"
            message = f"Couldn't score {len(failed)} {noun}; they'll be tried again next run. {failed[0]}"
            with self._db.connect() as conn:
                _append_error(conn, run_id, _scoring_error(message))

    def _record_score(self, run_id: int, job: sqlite3.Row, inputs: RunInputs, fit: FitScore) -> None:
        scored_at = _now()
        with self._db.connect() as conn:
            save_score(conn, job["id"], job["content_hash"], inputs.resume.version, fit, scored_at)
            cost = record_usage(
                conn, "scoring", run_id, job["id"], fit.model, fit.input_tokens, fit.output_tokens, scored_at
            )
            conn.execute(
                """
                UPDATE runs SET scored_jobs = scored_jobs + 1, matched_jobs = matched_jobs + ?,
                    ai_cost_usd = ai_cost_usd + ?
                WHERE id = ?
                """,
                (fit.score >= inputs.search_settings.min_score, cost, run_id),
            )

    def _record_failure(self, run_id: int, platform: Platform, board_id: str, message: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE companies SET last_error = ? WHERE platform = ? AND board_id = ?",
                (message, platform, board_id),
            )
            conn.execute("UPDATE runs SET companies_fetched = companies_fetched + 1 WHERE id = ?", (run_id,))
            _append_error(conn, run_id, {"kind": "board", "platform": platform, "board_id": board_id, "message": message})


def _scoring_error(message: str) -> dict[str, Any]:
    return {"kind": "scoring", "platform": None, "board_id": None, "message": message}


def _append_error(conn: sqlite3.Connection, run_id: int, error: dict[str, Any]) -> None:
    errors = json.loads(conn.execute("SELECT errors FROM runs WHERE id = ?", (run_id,)).fetchone()[0])
    errors.append(error)
    conn.execute("UPDATE runs SET errors = ? WHERE id = ?", (json.dumps(errors), run_id))
