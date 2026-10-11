"""Applications: Apply tailors my resume for a job in the background, then the application waits for my review."""

import logging
import re
import shutil
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader

from job_tracker.clients.claude import LLMError
from job_tracker.clients.libreoffice import MISSING_MESSAGE, ConversionError, LibreOffice
from job_tracker.database import Database
from job_tracker.models.application import Application, TailoredResume
from job_tracker.models.job import Job
from job_tracker.models.resume import SkillLine
from job_tracker.services.errors import ConflictError, NotFoundError, SetupIncompleteError
from job_tracker.services.pricing import estimate_cost
from job_tracker.services.resume_reader import skill_line
from job_tracker.services.resume_renderer import render
from job_tracker.services.resume_service import MASTER_DOCX, ResumeService
from job_tracker.services.resume_tailor import ResumeTailor, Shorten, TailorRequest, TailorResult
from job_tracker.services.run_service import scoring_missing
from job_tracker.services.settings_service import SettingsService

log = logging.getLogger(__name__)

TAILORED_DOCX = "resume.docx"
TAILORED_PDF = "resume.pdf"
INTERRUPTED = "Tailoring was interrupted because the server stopped. Try again."


class TailoringError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _now() -> str:
    return datetime.now(UTC).isoformat()


def covered(keywords: list[str], text: str) -> list[bool]:
    """Which keywords the text mentions, as whole words and ignoring case."""
    return [re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text, re.I) is not None for keyword in keywords]


class ApplicationService:
    """Each application's files live in their own directory under `files_dir/applications`."""

    def __init__(
        self,
        db: Database,
        files_dir: Path,
        settings: SettingsService,
        resumes: ResumeService,
        tailor: ResumeTailor,
        office: LibreOffice,
    ) -> None:
        self._db = db
        self._dir = files_dir / "applications"
        self._settings = settings
        self._resumes = resumes
        self._tailor = tailor
        self._office = office
        self._apply_lock = threading.Lock()
        with self._db.transaction() as uow:
            uow.applications.fail_drafting(INTERRUPTED, _now())

    def apply(self, job_id: int) -> tuple[Application, bool]:
        """The job's open application if it has one (and False), or a new one being tailored (and True)."""
        with self._apply_lock:
            with self._db.transaction() as uow:
                job = uow.jobs.get(job_id)
                existing = uow.applications.open_for_job(job_id)
            if job is None:
                raise NotFoundError("Job not found.")
            if existing is not None:
                return existing, False
            missing = scoring_missing(self._settings, self._resumes)
            if missing:
                raise SetupIncompleteError(missing)
            if not self._office.available:
                raise ConflictError(MISSING_MESSAGE)
            with self._db.transaction() as uow:
                for failed in uow.applications.failed_for_job(job_id):
                    uow.applications.delete(failed.id)
                application_id = uow.applications.create(job_id, _now())
        threading.Thread(target=self._tailor_in_background, args=(application_id, job), daemon=True).start()
        return self.get(application_id), True

    def get(self, application_id: int) -> Application:
        with self._db.transaction() as uow:
            application = uow.applications.get(application_id)
        if application is None:
            raise NotFoundError("Application not found.")
        return application

    def cancel(self, application_id: int) -> None:
        """Discard the application and its files; nothing has been sent anywhere."""
        application = self.get(application_id)
        with self._db.transaction() as uow:
            uow.applications.delete(application_id)
        if application.resume is not None:
            shutil.rmtree(self._dir / application.resume.directory, ignore_errors=True)

    def file(self, application_id: int, name: str) -> Path:
        resume = self.get(application_id).resume
        if resume is None:
            raise NotFoundError("This application has no tailored resume.")
        return self._dir / resume.directory / name

    def _tailor_in_background(self, application_id: int, job: Job) -> None:
        directory = uuid.uuid4().hex
        try:
            resume = self._tailor_resume(application_id, job, directory)
        except (LLMError, TailoringError, ConversionError) as error:
            self._fail(application_id, directory, error.message)
            return
        except Exception as error:
            log.exception("tailoring application %s failed", application_id)
            self._fail(application_id, directory, f"Unexpected error while tailoring: {error}")
            return
        with self._db.transaction() as uow:
            saved = uow.applications.set_status(application_id, "in_review", _now())
            if saved:
                uow.applications.save_resume(application_id, job.id, resume, _now())
        if not saved:
            shutil.rmtree(self._dir / directory, ignore_errors=True)

    def _fail(self, application_id: int, directory: str, message: str) -> None:
        shutil.rmtree(self._dir / directory, ignore_errors=True)
        with self._db.transaction() as uow:
            uow.applications.set_status(application_id, "failed", _now(), message)

    def _tailor_resume(self, application_id: int, job: Job, directory: str) -> TailoredResume:
        ai = self._settings.ai()
        version = self._resumes.current()
        if ai.anthropic_api_key is None or version is None or not version.ready or version.skills is None:
            raise TailoringError("Finish setting up your resume and Anthropic API key first.")
        assert version.summary_paragraphs is not None and version.skills_paragraphs is not None
        texts = [p.text for p in version.paragraphs]
        lines: dict[int, SkillLine] = {
            index: line for index in version.skills_paragraphs if (line := skill_line(texts[index])) is not None
        }
        request = TailorRequest(
            resume_text="\n".join(text for text in texts if text),
            summary=[texts[index] for index in version.summary_paragraphs],
            skills=list(lines.values()),
            allowed_skills=version.skills,
            job=job,
        )
        master = self._resumes.file(version.version, MASTER_DOCX).read_bytes()
        target = self._dir / directory
        target.mkdir(parents=True)

        shorten: Shorten | None = None
        for _ in range(2):
            result = self._tailor.tailor(ai.anthropic_api_key, ai.tailoring_model, request, shorten)
            self._record_usage(application_id, job.id, result)
            tailored, text = render(
                master, version.summary_paragraphs, result.summary, dict(zip(lines, result.skills, strict=True))
            )
            (target / TAILORED_DOCX).write_bytes(tailored)
            self._office.convert_to_pdf(target / TAILORED_DOCX, target)
            pages = len(PdfReader(target / TAILORED_PDF).pages)
            if pages <= version.page_count:
                break
            shorten = Shorten(pages, version.page_count, result.summary)
        else:
            assert shorten is not None
            raise TailoringError(
                f"The tailored resume ran to {shorten.pages} pages, longer than your {shorten.master_pages}-page "
                "master, even after shortening it. Try again, or shorten your master resume."
            )

        return TailoredResume(
            master_version=version.version,
            directory=directory,
            master_summary=request.summary,
            summary=result.summary,
            master_skills=request.skills,
            skills=result.skills,
            keywords=result.keywords,
            covered_before=covered(result.keywords, request.resume_text),
            covered_after=covered(result.keywords, text),
            page_count=pages,
            master_page_count=version.page_count,
        )

    def _record_usage(self, application_id: int, job_id: int, result: TailorResult) -> None:
        cost = estimate_cost(result.model, result.input_tokens, result.output_tokens)
        with self._db.transaction() as uow:
            uow.scores.record_usage(
                "tailoring", None, job_id, result.model, result.input_tokens, result.output_tokens, cost, _now()
            )
            uow.applications.add_cost(application_id, cost)
