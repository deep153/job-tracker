import logging
import threading
from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from job_tracker.clients.brave_search import WebSearch
from job_tracker.clients.claude import LLMError
from job_tracker.clients.job_boards import JobBoardClient
from job_tracker.database import Database
from job_tracker.models.job import FitResult, Job
from job_tracker.models.platform import Platform
from job_tracker.models.posting import Posting
from job_tracker.models.resume import MasterResume
from job_tracker.models.run import Run, RunError, RunStatus
from job_tracker.models.search_settings import SearchSettings
from job_tracker.services.board_sync import sync_board
from job_tracker.services.discovery import discover
from job_tracker.services.errors import NotFoundError, RunAlreadyActiveError, SetupIncompleteError
from job_tracker.services.filtering import refilter_jobs
from job_tracker.services.fit_scorer import FitScorer
from job_tracker.services.pricing import estimate_cost
from job_tracker.services.resume_service import ResumeService
from job_tracker.services.settings_service import SettingsService

log = logging.getLogger(__name__)

MAX_PARALLEL_FETCHES = 8
MAX_PARALLEL_SCORES = 4
RECENT_RUNS = 20


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
        settings: SettingsService,
        resumes: ResumeService,
        search: WebSearch,
        job_boards: Mapping[Platform, JobBoardClient],
        scorer: FitScorer,
    ) -> None:
        self._db = db
        self._settings = settings
        self._resumes = resumes
        self._search = search
        self._job_boards = job_boards
        self._scorer = scorer
        self._start_lock = threading.Lock()
        with self._db.transaction() as uow:
            # A run still marked running belongs to a backend process that has since stopped.
            uow.runs.mark_running_as_interrupted(_now())

    def missing(self) -> list[str]:
        """Human-readable list of what still has to be set up before a run can start."""
        missing = self._settings.search().missing(has_search_key=self._settings.search_api_key() is not None)
        if self._settings.ai().anthropic_api_key is None:
            missing.append("Add your Anthropic API key in Settings.")
        if self._resumes.current() is None:
            missing.append("Upload your resume and mark its Summary and Skills.")
        elif self._resumes.master() is None:
            missing.append("Mark your resume's Summary and Skills.")
        return missing

    def get(self, run_id: int) -> Run:
        with self._db.transaction() as uow:
            run = uow.runs.get(run_id)
        if run is None:
            raise NotFoundError("Run not found.")
        return run

    def recent(self) -> list[Run]:
        with self._db.transaction() as uow:
            return uow.runs.recent(RECENT_RUNS)

    def start(self) -> Run:
        inputs = self._inputs()
        with self._start_lock, self._db.transaction() as uow:
            if uow.runs.any_running():
                raise RunAlreadyActiveError
            run_id = uow.runs.create(_now())
        threading.Thread(target=self._execute, args=(run_id, inputs), daemon=True).start()
        return self.get(run_id)

    def _inputs(self) -> RunInputs:
        missing = self.missing()
        search_api_key = self._settings.search_api_key()
        ai = self._settings.ai()
        resume = self._resumes.master()
        if missing or search_api_key is None or ai.anthropic_api_key is None or resume is None:
            raise SetupIncompleteError(missing)
        return RunInputs(self._settings.search(), search_api_key, ai.anthropic_api_key, ai.scoring_model, resume)

    def _execute(self, run_id: int, inputs: RunInputs) -> None:
        status: RunStatus = "finished"
        try:
            self._discover(run_id, inputs.search_settings, inputs.search_api_key)
            self._fetch_all(run_id, inputs.search_settings)
            self._score_all(run_id, inputs)
        except Exception:
            log.exception("run %s failed", run_id)
            status = "failed"
        with self._db.transaction() as uow:
            uow.runs.finish(run_id, status, _now())

    def _discover(self, run_id: int, search_settings: SearchSettings, api_key: str) -> None:
        result = discover(self._search, api_key, search_settings)
        with self._db.transaction() as uow:
            discovered = uow.companies.add_discovered(result.boards, _now())
            uow.runs.record_discovery(run_id, result.queries_made, result.capped, discovered)
            if result.error:
                uow.runs.append_error(run_id, RunError("search", result.error))

    def _fetch_all(self, run_id: int, search_settings: SearchSettings) -> None:
        platforms = [p for p in search_settings.platforms if p in self._job_boards]
        with self._db.transaction() as uow:
            companies = uow.companies.boards_to_fetch(platforms)
            uow.runs.start_stage(run_id, "fetching", len(companies))
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_FETCHES) as pool:
            futures: dict[Future[list[Posting]], tuple[Platform, str]] = {
                pool.submit(self._job_boards[platform].fetch, board_id): (platform, board_id)
                for platform, board_id in companies
            }
            for future in as_completed(futures):
                platform, board_id = futures[future]
                try:
                    postings = future.result()
                except Exception as error:
                    self._record_fetch_failure(run_id, platform, board_id, describe_fetch_error(error))
                else:
                    self._record_fetch(run_id, platform, board_id, postings)

    def _record_fetch(self, run_id: int, platform: Platform, board_id: str, postings: list[Posting]) -> None:
        seen_at = _now()
        with self._db.transaction() as uow:
            result = sync_board(uow.jobs, platform, board_id, postings, seen_at)
            uow.runs.add_filtered_out(run_id, refilter_jobs(uow, result.to_filter))
            uow.companies.record_fetched(platform, board_id, seen_at)
            uow.runs.record_board_fetched(run_id, result.new, result.updated, result.closed)

    def _record_fetch_failure(self, run_id: int, platform: Platform, board_id: str, message: str) -> None:
        with self._db.transaction() as uow:
            uow.companies.record_error(platform, board_id, message)
            uow.runs.record_board_failed(run_id)
            uow.runs.append_error(run_id, RunError("board", message, platform, board_id))

    def _score_all(self, run_id: int, inputs: RunInputs) -> None:
        """Score every open job that passed the filters and has no score for this resume version and content."""
        with self._db.transaction() as uow:
            jobs = uow.jobs.needing_score(inputs.resume.version)
            uow.runs.start_stage(run_id, "scoring", len(jobs))
        failed: list[str] = []
        stopped = False
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_SCORES) as pool:
            futures: dict[Future[FitResult], Job] = {
                pool.submit(
                    self._scorer.score,
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
                        self._append_error(run_id, RunError("scoring", f"Scoring stopped: {error.message}"))
                    elif not error.fatal:
                        failed.append(error.message)
                    continue
                except Exception as error:
                    log.exception("scoring job %s failed", job.id)
                    failed.append(f"Unexpected error: {error}")
                    continue
                self._record_score(run_id, job, inputs, fit)
        if failed:
            noun = "job" if len(failed) == 1 else "jobs"
            message = f"Couldn't score {len(failed)} {noun}; they'll be tried again next run. {failed[0]}"
            self._append_error(run_id, RunError("scoring", message))

    def _record_score(self, run_id: int, job: Job, inputs: RunInputs, fit: FitResult) -> None:
        scored_at = _now()
        cost = estimate_cost(fit.model, fit.input_tokens, fit.output_tokens)
        with self._db.transaction() as uow:
            uow.scores.save(job.id, job.content_hash, inputs.resume.version, fit, scored_at)
            uow.scores.record_usage(
                "scoring", run_id, job.id, fit.model, fit.input_tokens, fit.output_tokens, cost, scored_at
            )
            uow.runs.record_scored(run_id, fit.score >= inputs.search_settings.min_score, cost)

    def _append_error(self, run_id: int, error: RunError) -> None:
        with self._db.transaction() as uow:
            uow.runs.append_error(run_id, error)
