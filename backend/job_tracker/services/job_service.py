from datetime import UTC, datetime, timedelta

from job_tracker.clients.claude import LLMError
from job_tracker.database import Database
from job_tracker.models.company import Company
from job_tracker.models.job import Job, JobQuery, JobSort
from job_tracker.services.errors import AIRequestError, NotFoundError, SetupIncompleteError
from job_tracker.services.fit_scorer import FitScorer
from job_tracker.services.pricing import estimate_cost
from job_tracker.services.resume_service import ResumeService
from job_tracker.services.run_service import scoring_missing
from job_tracker.services.settings_service import SettingsService


def job_query(
    company: str | None = None,
    location: str | None = None,
    posted_within_days: int | None = None,
    sort: JobSort = "score",
) -> JobQuery:
    posted_since = None
    if posted_within_days is not None:
        posted_since = (datetime.now(UTC) - timedelta(days=posted_within_days)).isoformat()
    return JobQuery(company=company, location=location or None, posted_since=posted_since, sort=sort)


class JobService:
    """The jobs and companies the dashboard shows, and what I can do with a job."""

    def __init__(self, db: Database, settings: SettingsService, resumes: ResumeService, scorer: FitScorer) -> None:
        self._db = db
        self._settings = settings
        self._resumes = resumes
        self._scorer = scorer

    def matches(self, query: JobQuery) -> list[Job]:
        """Jobs that passed the filters and scored at or above my threshold."""
        with self._db.transaction() as uow:
            return uow.jobs.matches(uow.settings.search_settings().min_score, query)

    def below_threshold(self, query: JobQuery) -> list[Job]:
        """Jobs that passed the filters but aren't scored yet, or scored under my threshold."""
        with self._db.transaction() as uow:
            return uow.jobs.below_threshold(uow.settings.search_settings().min_score, query)

    def filtered_out(self) -> list[Job]:
        with self._db.transaction() as uow:
            return uow.jobs.filtered_out()

    def get(self, job_id: int) -> Job:
        with self._db.transaction() as uow:
            job = uow.jobs.get(job_id)
        if job is None:
            raise NotFoundError("Job not found.")
        return job

    def dismiss(self, job_id: int) -> None:
        """A dismissed job is hidden from every list and never scored again, even if its posting changes."""
        with self._db.transaction() as uow:
            if not uow.jobs.dismiss(job_id):
                raise NotFoundError("Job not found.")

    def rescore(self, job_id: int) -> Job:
        """Score the job again, now, against my current master resume; the new score replaces the shown one."""
        job = self.get(job_id)
        missing = scoring_missing(self._settings, self._resumes)
        ai, resume = self._settings.ai(), self._resumes.master()
        if missing or ai.anthropic_api_key is None or resume is None:
            raise SetupIncompleteError(missing)
        try:
            fit = self._scorer.score(ai.anthropic_api_key, ai.scoring_model, resume, self._settings.search(), job)
        except LLMError as error:
            raise AIRequestError(error.message) from error
        scored_at = datetime.now(UTC).isoformat()
        cost = estimate_cost(fit.model, fit.input_tokens, fit.output_tokens)
        with self._db.transaction() as uow:
            uow.scores.save(job.id, job.content_hash, resume.version, fit, scored_at)
            uow.scores.record_usage(
                "scoring", None, job.id, fit.model, fit.input_tokens, fit.output_tokens, cost, scored_at
            )
        return self.get(job_id)

    def companies(self) -> list[Company]:
        with self._db.transaction() as uow:
            return uow.companies.all()

    def set_company_blocked(self, company_id: int, blocked: bool) -> Company:
        """A blocked company isn't fetched and its jobs are hidden."""
        with self._db.transaction() as uow:
            company = uow.companies.get(company_id) if uow.companies.set_blocked(company_id, blocked) else None
        if company is None:
            raise NotFoundError("Company not found.")
        return company
