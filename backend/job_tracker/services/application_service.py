"""Applications: Apply tailors my resume for a job in the background, then the application waits for my review."""

import logging
import os
import re
import shutil
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader

from job_tracker.clients.claude import LLMError
from job_tracker.clients.forms import FormError, FormSubmitter, SubmitError
from job_tracker.clients.libreoffice import MISSING_MESSAGE, ConversionError, LibreOffice
from job_tracker.database import Database
from job_tracker.models.answers import FormAnswer
from job_tracker.models.application import SENT_STATUSES, Application, ApplicationStatus, TailoredResume
from job_tracker.models.job import Job
from job_tracker.models.platform import PLATFORM_NAMES, Platform
from job_tracker.models.resume import ResumeVersion, SkillLine
from job_tracker.services.answer_engine import draft_answers, exact_choice
from job_tracker.services.errors import ConflictError, InvalidRequestError, NotFoundError, SetupIncompleteError
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
SCREENSHOT = "screenshot.png"
INTERRUPTED = "Tailoring was interrupted because the server stopped. Try again."
SUBMIT_INTERRUPTED = (
    "Sending was interrupted because the server stopped. Check the company's site or your email to see whether "
    "it went through, and finish it by hand if not."
)
HANDOVER = "Finish the application in the browser window that opened, then close it."
ALREADY_APPLIED = "You've already applied to this job."


class TailoringError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _now() -> str:
    return datetime.now(UTC).isoformat()


def covered(keywords: list[str], text: str) -> list[bool]:
    """Which keywords the text mentions, as whole words and ignoring case."""
    return [re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text, re.I) is not None for keyword in keywords]


@dataclass(frozen=True)
class _Form:
    answers: list[FormAnswer] | None
    used: set[int]
    error: str | None


def _typed(current: FormAnswer, text: str | None) -> FormAnswer:
    field = current.field
    if field.kind == "file":
        if current.source == "resume":
            raise InvalidRequestError(f"“{field.label}” is filled with your tailored resume.")
        raise InvalidRequestError(f"Uploading a file for “{field.label}” isn't supported yet.")
    text = (text or "").strip()
    if not text:
        return current.answered(None, "none")
    answer = exact_choice(text, field)
    if answer is None:
        raise InvalidRequestError(f"Pick one of the options for “{field.label}”.")
    return current.answered(answer, "you")


def _lines(version: ResumeVersion) -> dict[int, SkillLine]:
    """The Skills paragraphs that list skills, by paragraph index, in order."""
    texts = [p.text for p in version.paragraphs]
    return {index: line for index in version.skills_paragraphs or [] if (line := skill_line(texts[index])) is not None}


def _edited_lines(master: list[SkillLine], edited: list[list[str]], allowed: list[str]) -> list[SkillLine]:
    """My edited skills for each line, under the master line's label and in the master list's spelling."""
    if len(edited) != len(master):
        lines = "skills line" if len(master) == 1 else "skills lines"
        raise InvalidRequestError(f"Your resume has {len(master)} {lines}; send the skills for each of them.")
    spelling = {" ".join(skill.split()).casefold(): skill for skill in allowed}
    result = []
    for line, skills in zip(master, edited, strict=True):
        kept: list[str] = []
        for skill in skills:
            name = " ".join(skill.split())
            if not name:
                continue
            if name.casefold() not in spelling:
                raise InvalidRequestError(
                    f"“{name}” isn't in your master skills list. Add it on the Resume page first, or remove it."
                )
            if spelling[name.casefold()] not in kept:
                kept.append(spelling[name.casefold()])
        if not kept:
            raise InvalidRequestError("Keep at least one skill on each skills line.")
        result.append(SkillLine(line.label, kept))
    return result


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
        forms: dict[Platform, FormSubmitter],
    ) -> None:
        self._db = db
        self._dir = files_dir / "applications"
        self._settings = settings
        self._resumes = resumes
        self._tailor = tailor
        self._office = office
        self._forms = forms
        self._apply_lock = threading.Lock()
        self._edit_lock = threading.Lock()
        with self._db.transaction() as uow:
            uow.applications.fail_drafting(INTERRUPTED, _now())
            uow.applications.interrupt_submitting(SUBMIT_INTERRUPTED, _now())

    def apply(self, job_id: int) -> tuple[Application, bool]:
        """The job's open application if it has one (and False), or a new one being tailored (and True)."""
        with self._apply_lock:
            with self._db.transaction() as uow:
                job = uow.jobs.get(job_id)
                existing = uow.applications.open_for_job(job_id)
                sent = uow.applications.sent_for_job(job_id)
            if job is None:
                raise NotFoundError("Job not found.")
            if existing is not None:
                return existing, False
            if sent is not None:
                raise ConflictError(ALREADY_APPLIED)
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
        """Discard the application and its files, as long as nothing has been sent anywhere."""
        application = self.get(application_id)
        if application.status in SENT_STATUSES:
            raise ConflictError("This application has already been sent, so it can't be cancelled.")
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
            form = self._read_form(job)
            resume = self._tailor_resume(application_id, job, directory)
        except (LLMError, TailoringError, ConversionError, FormError) as error:
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
                uow.applications.save_answers(application_id, form.answers, form.error, _now())
                uow.answer_bank.mark_used(form.used, _now())
        if not saved:
            shutil.rmtree(self._dir / directory, ignore_errors=True)

    def _read_form(self, job: Job) -> _Form:
        submitter = self._forms.get(job.posting.platform)
        if submitter is None:
            name = PLATFORM_NAMES[job.posting.platform]
            return _Form(None, set(), f"Filling in {name} application forms isn't supported yet.")
        fields = submitter.read_fields(job.posting.application_url)
        with self._db.transaction() as uow:
            bank = uow.answer_bank.list()
        drafted = draft_answers(fields, bank)
        return _Form(drafted.answers, drafted.used, None)

    def answer(self, application_id: int, answers: dict[str, str | None]) -> Application:
        """Save answers I typed in review; a blank answer clears the question."""
        with self._edit_lock:
            application = self.get(application_id)
            if not application.editable or application.answers is None:
                raise ConflictError("Only the questions of an application in review can be answered.")
            by_key = {answer.field.key: answer for answer in application.answers}
            for key, text in answers.items():
                current = by_key.get(key)
                if current is None:
                    raise InvalidRequestError(f"This form has no question “{key}”.")
                by_key[key] = _typed(current, text)
            with self._db.transaction() as uow:
                uow.applications.save_answers(application_id, list(by_key.values()), application.form_error, _now())
        return self.get(application_id)

    def approve(self, application_id: int) -> Application:
        """Start sending the application by filling in the company's form; it's `submitting` until that ends in
        `submitted`, `needs_manual` (handed over to me in the browser) or `failed`."""
        with self._apply_lock:
            application = self.get(application_id)
            problem = application.approval_problem
            if problem is not None:
                raise ConflictError(problem)
            with self._db.transaction() as uow:
                job = uow.jobs.get(application.job_id)
                if uow.applications.sent_for_job(application.job_id) is not None:
                    raise ConflictError(ALREADY_APPLIED)
                uow.applications.start_submitting(application_id, _now())
        assert job is not None
        threading.Thread(target=self._submit_in_background, args=(application, job), daemon=True).start()
        return self.get(application_id)

    def screenshot(self, application_id: int) -> Path:
        application = self.get(application_id)
        if not application.screenshot or application.resume is None:
            raise NotFoundError("This application has no screenshot.")
        return self._dir / application.resume.directory / SCREENSHOT

    def _submit_in_background(self, application: Application, job: Job) -> None:
        assert application.resume is not None and application.answers is not None
        directory = self._dir / application.resume.directory
        (directory / SCREENSHOT).unlink(missing_ok=True)

        def hand_over(reason: str) -> None:
            with self._db.transaction() as uow:
                uow.applications.finish_submitting(application.id, "needs_manual", _now(), f"{reason} {HANDOVER}")

        try:
            outcome = self._forms[job.posting.platform].submit(
                job.posting.application_url,
                application.answers,
                directory / TAILORED_PDF,
                directory / SCREENSHOT,
                hand_over,
            )
        except SubmitError as error:
            self._finish_submitting(application.id, "failed", error.message, error.screenshot)
            return
        except FormError as error:
            self._finish_submitting(application.id, "failed", error.message)
            return
        except Exception as error:
            log.exception("submitting application %s failed", application.id)
            self._finish_submitting(application.id, "failed", f"Unexpected error while submitting: {error}")
            return
        if outcome == "submitted":
            self._finish_submitting(application.id, "submitted")

    def _finish_submitting(
        self, application_id: int, status: ApplicationStatus, error: str | None = None, screenshot: bool = False
    ) -> None:
        with self._db.transaction() as uow:
            uow.applications.finish_submitting(application_id, status, _now(), error, screenshot)

    def _fail(self, application_id: int, directory: str, message: str) -> None:
        shutil.rmtree(self._dir / directory, ignore_errors=True)
        with self._db.transaction() as uow:
            uow.applications.set_status(application_id, "failed", _now(), message)

    def edit(self, application_id: int, summary: list[str], skills: list[list[str]]) -> Application:
        """Regenerate the tailored resume from my edits. The master-list rule still applies; a resume that grew
        past the master's page count is saved, and the review bundle flags it."""
        with self._edit_lock:
            application = self.get(application_id)
            resume = application.resume
            if not application.editable or resume is None:
                raise ConflictError("Only an application in review can be edited.")
            version = self._resumes.get(resume.master_version)
            summary = [" ".join(text.split()) for text in summary if text.strip()]
            if not summary:
                raise InvalidRequestError("Write a Summary before regenerating.")
            lines = _edited_lines(resume.master_skills, skills, version.skills or [])
            pages, text = self._render(version, summary, lines, self._dir / resume.directory)
            with self._db.transaction() as uow:
                uow.applications.update_resume(
                    application_id, summary, lines, covered(resume.keywords, text), pages, _now()
                )
        return self.get(application_id)

    def _render(
        self, version: ResumeVersion, summary: list[str], skills: list[SkillLine], target: Path
    ) -> tuple[int, str]:
        """Write the tailored .docx and PDF into `target`; returns the PDF's page count and the resume's text.

        The files are replaced only once both are made, so a failed conversion leaves the previous ones.
        """
        assert version.summary_paragraphs is not None
        master = self._resumes.file(version.version, MASTER_DOCX).read_bytes()
        tailored, text = render(
            master, version.summary_paragraphs, summary, dict(zip(_lines(version), skills, strict=True))
        )
        draft = target / f"{uuid.uuid4().hex}.docx"
        draft.write_bytes(tailored)
        try:
            pdf = self._office.convert_to_pdf(draft, target)
            pages = len(PdfReader(pdf).pages)
            os.replace(draft, target / TAILORED_DOCX)
            os.replace(pdf, target / TAILORED_PDF)
        finally:
            draft.unlink(missing_ok=True)
            draft.with_suffix(".pdf").unlink(missing_ok=True)
        return pages, text

    def _tailor_resume(self, application_id: int, job: Job, directory: str) -> TailoredResume:
        ai = self._settings.ai()
        version = self._resumes.current()
        if ai.anthropic_api_key is None or version is None or not version.ready or version.skills is None:
            raise TailoringError("Finish setting up your resume and Anthropic API key first.")
        assert version.summary_paragraphs is not None
        texts = [p.text for p in version.paragraphs]
        request = TailorRequest(
            resume_text="\n".join(text for text in texts if text),
            summary=[texts[index] for index in version.summary_paragraphs],
            skills=list(_lines(version).values()),
            allowed_skills=version.skills,
            job=job,
        )
        target = self._dir / directory
        target.mkdir(parents=True)

        shorten: Shorten | None = None
        for _ in range(2):
            result = self._tailor.tailor(ai.anthropic_api_key, ai.tailoring_model, request, shorten)
            self._record_usage(application_id, job.id, result)
            pages, text = self._render(version, result.summary, result.skills, target)
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
