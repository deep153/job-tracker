"""The composition root: builds every client and service once, wired together."""

import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from job_tracker.clients.brave_search import BraveSearch
from job_tracker.clients.claude import LLM, ClaudeLLM
from job_tracker.clients.forms import form_submitters
from job_tracker.clients.job_boards import job_board_clients
from job_tracker.clients.libreoffice import MISSING_MESSAGE, LibreOffice
from job_tracker.database import Database
from job_tracker.services.answer_bank_service import AnswerBankService
from job_tracker.services.answer_writer import AnswerWriter
from job_tracker.services.application_service import ApplicationService
from job_tracker.services.cost_service import CostService
from job_tracker.services.cover_letter_writer import CoverLetterWriter
from job_tracker.services.fit_scorer import FitScorer
from job_tracker.services.job_service import JobService
from job_tracker.services.resume_service import ResumeService
from job_tracker.services.resume_tailor import ResumeTailor
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
    applications: ApplicationService
    costs: CostService
    answer_bank: AnswerBankService


def build_services(
    db_path: Path, http: httpx.Client, office: LibreOffice | None, llm: LLM | None, visible_browser: bool
) -> Services:
    """`http` is used for every outside HTTP call except Claude's; resume files are kept next to the database.
    `visible_browser` shows the browser while it sends an application."""
    db = Database(db_path)
    db.initialize()
    office = office or LibreOffice.detect()
    if not office.available:
        log.warning(MISSING_MESSAGE)
    job_boards = job_board_clients(http)
    settings = SettingsService(db, job_boards.keys())
    files_dir = db_path.parent / "files"
    resumes = ResumeService(db, files_dir, office)
    llm = llm or ClaudeLLM()
    scorer = FitScorer(llm)
    runs = RunService(db, settings, resumes, BraveSearch(http), job_boards, scorer)
    jobs = JobService(db, settings, resumes, scorer)
    applications = ApplicationService(
        db,
        files_dir,
        settings,
        resumes,
        ResumeTailor(llm),
        AnswerWriter(llm),
        CoverLetterWriter(llm),
        office,
        form_submitters(visible_browser),
    )
    return Services(office, settings, resumes, jobs, runs, applications, CostService(db), AnswerBankService(db))
