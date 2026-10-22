"""Applications: Apply tailors my resume for a job in the background, then the application waits for my review."""

import logging
import os
import shutil
import threading
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader

from job_tracker.clients.claude import LLMError
from job_tracker.clients.forms import FormError, FormSubmitter, SubmitError
from job_tracker.clients.libreoffice import MISSING_MESSAGE, ConversionError, LibreOffice
from job_tracker.database import Database
from job_tracker.models.answers import AnswerCategory, FormAnswer
from job_tracker.models.application import (
    APPLIED_STATUSES,
    SENT_STATUSES,
    Application,
    ApplicationStatus,
    BulletEdit,
    RevertedBullet,
    TailoredResume,
)
from job_tracker.models.job import Job
from job_tracker.models.platform import PLATFORM_NAMES, Platform
from job_tracker.models.resume import Bullet, MasterResume, ResumeVersion, SkillLine
from job_tracker.services import bullet_guard
from job_tracker.services.answer_engine import draft_answers, exact_choice, open_ended
from job_tracker.services.answer_writer import AnswerWriter
from job_tracker.services.cover_letter_writer import CoverLetterWriter, as_docx, tidy
from job_tracker.services.errors import ConflictError, InvalidRequestError, NotFoundError, SetupIncompleteError
from job_tracker.services.fit_scorer import FitScorer
from job_tracker.services.keywords import covered
from job_tracker.services.pricing import estimate_cost
from job_tracker.services.resume_reader import bullet, skill_line
from job_tracker.services.resume_renderer import render
from job_tracker.services.resume_service import MASTER_DOCX, ResumeService
from job_tracker.services.resume_tailor import ResumeTailor, Shorten, TailorRequest
from job_tracker.services.run_service import scoring_missing
from job_tracker.services.settings_service import SettingsService

log = logging.getLogger(__name__)

TAILORED_DOCX = "resume.docx"
TAILORED_PDF = "resume.pdf"
COVER_LETTER_PDF = "cover-letter.pdf"
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


@dataclass(frozen=True)
class _Form:
    answers: list[FormAnswer] | None
    used: set[int]
    error: str | None


def _typed(current: FormAnswer, text: str | None) -> FormAnswer:
    field = current.field
    if current.source == "cover_letter":
        raise InvalidRequestError(f"“{field.label}” is filled with your cover letter; edit the letter instead.")
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


def _resume_text(version: ResumeVersion) -> str:
    return "\n".join(p.text for p in version.paragraphs if p.text)


def _target_keywords(job: Job) -> list[str]:
    """The Fit Scorer's matched and missing keywords for the job, or none if it hasn't been scored."""
    if job.score is None:
        return []
    keywords: list[str] = []
    for keyword in [*job.score.matched_keywords, *job.score.missing_keywords]:
        if keyword.casefold() not in {k.casefold() for k in keywords}:
            keywords.append(keyword)
    return keywords


def _bullets(version: ResumeVersion) -> list[Bullet]:
    """The marked experience bullets, in order."""
    return [bullet(index, version.paragraphs[index].text) for index in version.bullet_paragraphs or []]


def _checked_bullets(
    bullets: list[BulletEdit], rewrites: dict[int, str], allowed_skills: list[str], keywords: list[str]
) -> list[BulletEdit]:
    """The bullets with `rewrites` (new text after the label, by paragraph) applied, except those the fact check
    turns down: those go back to the master's text and record the rewrite and why."""
    result = []
    for edit in bullets:
        rewrite = rewrites.get(edit.index)
        if rewrite is None or rewrite == edit.tailored:
            result.append(edit)
        elif reason := bullet_guard.problem(edit.master, rewrite, allowed_skills, keywords):
            result.append(replace(edit, tailored=edit.master, reverted=RevertedBullet(rewrite, reason)))
        else:
            result.append(replace(edit, tailored=rewrite, reverted=None))
    return result


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
        scorer: FitScorer,
        writer: AnswerWriter,
        letters: CoverLetterWriter,
        office: LibreOffice,
        forms: dict[Platform, FormSubmitter],
    ) -> None:
        self._db = db
        self._dir = files_dir / "applications"
        self._settings = settings
        self._resumes = resumes
        self._tailor = tailor
        self._scorer = scorer
        self._writer = writer
        self._letters = letters
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

    def list_all(self) -> list[tuple[Application, Job]]:
        """Every application with its job, newest first."""
        with self._db.transaction() as uow:
            applications = uow.applications.list_all()
            jobs = {job_id: uow.jobs.get(job_id) for job_id in {a.job_id for a in applications}}
        return [(application, job) for application in applications if (job := jobs[application.job_id]) is not None]

    def track(self, application_id: int, status: ApplicationStatus) -> Application:
        """Set the status by hand as I hear back. Only a submitted application has one to set, except that one
        handed over to me can be marked submitted once I've finished it."""
        application = self.get(application_id)
        finished_by_hand = application.status == "needs_manual" and status == "submitted"
        if application.status not in APPLIED_STATUSES and not finished_by_hand:
            raise ConflictError("You can update the status once the application has been submitted.")
        with self._db.transaction() as uow:
            uow.applications.track(application_id, status, _now())
        return self.get(application_id)

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
            answers = self._draft_open_ended(application_id, job, form.answers)
            cover_letter = self._write_cover_letter(application_id, job, answers, directory)
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
                uow.applications.save_answers(application_id, answers, form.error, _now())
                uow.applications.save_cover_letter(application_id, cover_letter, _now())
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

    def _draft_open_ended(
        self, application_id: int, job: Job, answers: list[FormAnswer] | None
    ) -> list[FormAnswer] | None:
        """The answers with AI drafts for the open-ended questions the bank didn't answer. EEO questions are never
        sent; if drafting fails, the questions are left for me."""
        questions = [answer.field for answer in answers or [] if open_ended(answer)]
        if answers is None or not questions:
            return answers
        ai = self._settings.ai()
        version = self._resumes.current()
        assert ai.anthropic_api_key is not None and version is not None
        try:
            result = self._writer.draft(ai.anthropic_api_key, ai.tailoring_model, _resume_text(version), job, questions)
        except LLMError as error:
            log.warning("drafting answers for application %s failed: %s", application_id, error.message)
            return answers
        self._record_usage("answers", application_id, job.id, result.model, result.input_tokens, result.output_tokens)
        return [
            answer.answered(result.answers[answer.field.key], "ai")
            if open_ended(answer) and answer.field.key in result.answers
            else answer
            for answer in answers
        ]

    def _write_cover_letter(
        self, application_id: int, job: Job, answers: list[FormAnswer] | None, directory: str
    ) -> str | None:
        """A cover letter, only when the form has a field for it; also as a PDF when the form takes a file."""
        fields = [answer.field for answer in answers or [] if answer.source == "cover_letter"]
        if not fields:
            return None
        ai = self._settings.ai()
        version = self._resumes.current()
        assert ai.anthropic_api_key is not None and version is not None
        result = self._letters.write(ai.anthropic_api_key, ai.tailoring_model, _resume_text(version), job)
        self._record_usage(
            "cover_letter", application_id, job.id, result.model, result.input_tokens, result.output_tokens
        )
        if any(field.kind == "file" for field in fields):
            self._cover_letter_pdf(result.text, self._dir / directory)
        return result.text

    def _cover_letter_pdf(self, text: str, target: Path) -> None:
        draft = target / f"{uuid.uuid4().hex}.docx"
        draft.write_bytes(as_docx(text))
        try:
            os.replace(self._office.convert_to_pdf(draft, target), target / COVER_LETTER_PDF)
        finally:
            draft.unlink(missing_ok=True)
            draft.with_suffix(".pdf").unlink(missing_ok=True)

    def edit_cover_letter(self, application_id: int, text: str) -> Application:
        """Save my edited cover letter (and remake its PDF when the form takes a file)."""
        with self._edit_lock:
            application = self.get(application_id)
            if not application.editable or application.resume is None:
                raise ConflictError("Only the cover letter of an application in review can be edited.")
            if application.cover_letter is None:
                raise ConflictError("This application form has no cover letter field.")
            text = tidy(text)
            if not text:
                raise InvalidRequestError("Write the cover letter.")
            if application.cover_letter_file:
                self._cover_letter_pdf(text, self._dir / application.resume.directory)
            with self._db.transaction() as uow:
                uow.applications.save_cover_letter(application_id, text, _now())
        return self.get(application_id)

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

    def save_to_bank(self, application_id: int, key: str) -> Application:
        """Save the question's current answer into my answer bank, replacing my saved answer to the same question;
        an EEO question's answer is saved as an EEO choice."""
        with self._edit_lock:
            application = self.get(application_id)
            if not application.editable or application.answers is None:
                raise ConflictError("Only the answers of an application in review can be saved.")
            current = next((answer for answer in application.answers if answer.field.key == key), None)
            if current is None:
                raise InvalidRequestError(f"This form has no question “{key}”.")
            if current.field.kind == "file" or current.answer is None:
                raise InvalidRequestError(f"Answer “{current.field.label}” before saving it.")
            question = current.field.label
            category: AnswerCategory = "eeo" if current.eeo else "other"
            answers = [
                answer.answered(answer.answer, "bank") if answer is current else answer
                for answer in application.answers
            ]
            with self._db.transaction() as uow:
                same = next((e for e in uow.answer_bank.list() if e.question.casefold() == question.casefold()), None)
                if same is None:
                    entry_id = uow.answer_bank.create(question, current.answer, category, _now())
                else:
                    entry_id = same.id
                    uow.answer_bank.update(same.id, same.question, current.answer, same.category)
                uow.answer_bank.mark_used({entry_id}, _now())
                uow.applications.save_answers(application_id, answers, application.form_error, _now())
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

    def cover_letter_pdf(self, application_id: int) -> Path:
        application = self.get(application_id)
        if not application.cover_letter_file or application.resume is None:
            raise NotFoundError("This application has no cover letter file.")
        return self._dir / application.resume.directory / COVER_LETTER_PDF

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

        # A cover letter text box gets the letter itself, as it is now.
        answers = [
            answer.answered(application.cover_letter, "cover_letter")
            if answer.source == "cover_letter" and answer.field.kind != "file"
            else answer
            for answer in application.answers
        ]
        try:
            outcome = self._forms[job.posting.platform].submit(
                job.posting.application_url,
                answers,
                directory / TAILORED_PDF,
                directory / COVER_LETTER_PDF if application.cover_letter_file else None,
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

    def edit(
        self, application_id: int, summary: list[str], skills: list[list[str]], bullets: dict[int, str] | None = None
    ) -> Application:
        """Regenerate the tailored resume from my edits, then re-score it. `bullets` are the bullets I changed (text
        after the label, by paragraph); they go through the same fact check as the tailor's rewrites. The
        master-list rule still applies; a resume that grew past the master's page count is saved, and the review
        bundle flags it."""
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
            marked = {edit.index for edit in resume.bullets or []}
            rewrites: dict[int, str] = {}
            for index, text in (bullets or {}).items():
                if index not in marked:
                    raise InvalidRequestError(f"Paragraph {index} isn't one of your experience bullets.")
                if not text.strip():
                    raise InvalidRequestError("Write each bullet, or use the original.")
                rewrites[index] = " ".join(text.split())
            edits = _checked_bullets(resume.bullets or [], rewrites, version.skills or [], resume.keywords)
            pages, text = self._render(version, summary, lines, edits, self._dir / resume.directory)
            job = self._job(application.job_id)
            score = self._rescore(application_id, job, version, text, lines)
            with self._db.transaction() as uow:
                uow.applications.update_resume(
                    application_id,
                    summary,
                    lines,
                    None if resume.bullets is None else edits,
                    covered(resume.keywords, text),
                    pages,
                    score,
                    _now(),
                )
        return self.get(application_id)

    def _job(self, job_id: int) -> Job:
        with self._db.transaction() as uow:
            job = uow.jobs.get(job_id)
        if job is None:
            raise NotFoundError("Job not found.")
        return job

    def _render(
        self,
        version: ResumeVersion,
        summary: list[str],
        skills: list[SkillLine],
        bullets: list[BulletEdit],
        target: Path,
    ) -> tuple[int, str]:
        """Write the tailored .docx and PDF into `target`; returns the PDF's page count and the resume's text.

        The files are replaced only once both are made, so a failed conversion leaves the previous ones.
        """
        assert version.summary_paragraphs is not None
        master = self._resumes.file(version.version, MASTER_DOCX).read_bytes()
        reworded = [Bullet(b.index, b.label, b.tailored) for b in bullets if b.tailored != b.master]
        tailored, text = render(
            master, version.summary_paragraphs, summary, dict(zip(_lines(version), skills, strict=True)), reworded
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
            resume_text=_resume_text(version),
            summary=[texts[index] for index in version.summary_paragraphs],
            skills=list(_lines(version).values()),
            allowed_skills=version.skills,
            job=job,
            target_keywords=_target_keywords(job),
            bullets=_bullets(version),
        )
        target = self._dir / directory
        target.mkdir(parents=True)

        shorten: Shorten | None = None
        for _ in range(2):
            result = self._tailor.tailor(ai.anthropic_api_key, ai.tailoring_model, request, shorten)
            self._record_usage(
                "tailoring", application_id, job.id, result.model, result.input_tokens, result.output_tokens
            )
            bullets = _checked_bullets(
                [BulletEdit(b.index, b.label, b.text, b.text) for b in request.bullets],
                {request.bullets[n].index: text for n, text in result.bullets.items()},
                version.skills,
                result.keywords,
            )
            pages, text = self._render(version, result.summary, result.skills, bullets, target)
            if pages <= version.page_count:
                break
            shorten = Shorten(pages, version.page_count, result.summary, result.bullets)
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
            gaps=result.gaps,
            score_before=job.score.score if job.score is not None else None,
            score_after=self._rescore(application_id, job, version, text, result.skills),
            bullets=bullets,
        )

    def _rescore(
        self, application_id: int, job: Job, version: ResumeVersion, text: str, skills: list[SkillLine]
    ) -> int | None:
        """The Fit Scorer's score for the tailored resume, or None if the call fails. The job's own score (against
        the master) stays as it is."""
        ai = self._settings.ai()
        assert ai.anthropic_api_key is not None
        tailored = MasterResume(version.version, text, [skill for line in skills for skill in line.skills])
        try:
            fit = self._scorer.score(ai.anthropic_api_key, ai.scoring_model, tailored, self._settings.search(), job)
        except LLMError as error:
            log.warning("re-scoring the tailored resume of application %s failed: %s", application_id, error.message)
            return None
        self._record_usage("rescoring", application_id, job.id, fit.model, fit.input_tokens, fit.output_tokens)
        return fit.score

    def _record_usage(
        self, kind: str, application_id: int, job_id: int, model: str, input_tokens: int, output_tokens: int
    ) -> None:
        cost = estimate_cost(model, input_tokens, output_tokens)
        with self._db.transaction() as uow:
            uow.scores.record_usage(kind, None, job_id, model, input_tokens, output_tokens, cost, _now())
            uow.applications.add_cost(application_id, cost)
