import sqlite3

from job_tracker.repositories.company_repository import CompanyRepository
from job_tracker.repositories.job_repository import JobRepository
from job_tracker.repositories.resume_repository import ResumeRepository
from job_tracker.repositories.run_repository import RunRepository
from job_tracker.repositories.score_repository import ScoreRepository
from job_tracker.repositories.settings_repository import SettingsRepository


class UnitOfWork:
    """Every repository, sharing one connection: what's done through them commits or rolls back together."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.settings = SettingsRepository(conn)
        self.companies = CompanyRepository(conn)
        self.jobs = JobRepository(conn)
        self.runs = RunRepository(conn)
        self.scores = ScoreRepository(conn)
        self.resumes = ResumeRepository(conn)
