"""The composition root: builds every client and service once, wired together."""

import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from job_tracker.clients.brave_search import BraveSearch
from job_tracker.clients.claude import LLM, ClaudeLLM
from job_tracker.clients.job_boards import job_board_clients
from job_tracker.clients.libreoffice import MISSING_MESSAGE, LibreOffice
from job_tracker.database import Database
from job_tracker.services.cost_service import CostService
from job_tracker.services.fit_scorer import FitScorer
from job_tracker.services.job_service import JobService
from job_tracker.services.resume_service import ResumeService
from job_tracker.services.run_service import RunService
from job_tracker.services.settings_service import SettingsService

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Services:
    office: LibreOffice
    settings: SettingsService
    resumes: ResumeService
    jobs: JobService
    runs: RunService
    costs: CostService


def build_services(db_path: Path, http: httpx.Client, office: LibreOffice | None, llm: LLM | None) -> Services:
    """`http` is used for every outside HTTP call except Claude's; resume files are kept next to the database."""
    db = Database(db_path)
    db.initialize()
    office = office or LibreOffice.detect()
    if not office.available:
        log.warning(MISSING_MESSAGE)
    job_boards = job_board_clients(http)
    settings = SettingsService(db, job_boards.keys())
    resumes = ResumeService(db, db_path.parent / "files", office)
    runs = RunService(db, settings, resumes, BraveSearch(http), job_boards, FitScorer(llm or ClaudeLLM()))
    return Services(office, settings, resumes, JobService(db), runs, CostService(db))
