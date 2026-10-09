from job_tracker.database import Database
from job_tracker.models.company import Company
from job_tracker.models.job import Job
from job_tracker.services.errors import NotFoundError


class JobService:
    """The jobs and companies the dashboard shows."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def matches(self) -> list[Job]:
        """Jobs that passed the filters and scored at or above my threshold, best first."""
        with self._db.transaction() as uow:
            return uow.jobs.matches(uow.settings.search_settings().min_score)

    def below_threshold(self) -> list[Job]:
        """Jobs that passed the filters but aren't scored yet, or scored under my threshold."""
        with self._db.transaction() as uow:
            return uow.jobs.below_threshold(uow.settings.search_settings().min_score)

    def filtered_out(self) -> list[Job]:
        with self._db.transaction() as uow:
            return uow.jobs.filtered_out()

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
