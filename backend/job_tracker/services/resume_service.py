"""Resume master: the imported .docx, which of its paragraphs are the Summary and Skills, and the master skills list."""

import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader

from job_tracker.clients.libreoffice import MISSING_MESSAGE, ConversionError, LibreOffice
from job_tracker.database import Database
from job_tracker.models.resume import MasterResume, ResumeVersion
from job_tracker.services.errors import ConflictError, InvalidRequestError, NotFoundError
from job_tracker.services.resume_reader import MAX_SKILL_LENGTH, add_skill, read_paragraphs, skills_from_text

MAX_SKILLS = 200

MASTER_DOCX = "master.docx"
PREVIEW_PDF = "preview.pdf"


class ResumeService:
    """Versions of the master resume: each upload is a new version, and earlier versions are kept.

    Each version's files live in their own directory under `files_dir/resumes`.
    """

    def __init__(self, db: Database, files_dir: Path, office: LibreOffice) -> None:
        self._db = db
        self._dir = files_dir / "resumes"
        self._office = office

    def import_docx(self, filename: str, data: bytes) -> ResumeVersion:
        paragraphs = read_paragraphs(filename, data)
        if not self._office.available:
            raise ConflictError(MISSING_MESSAGE)
        directory = uuid.uuid4().hex
        target = self._dir / directory
        target.mkdir(parents=True)
        try:
            (target / MASTER_DOCX).write_bytes(data)
            self._office.convert_to_pdf(target / MASTER_DOCX, target).rename(target / PREVIEW_PDF)
            page_count = len(PdfReader(target / PREVIEW_PDF).pages)
        except ConversionError as error:
            shutil.rmtree(target, ignore_errors=True)
            raise InvalidRequestError(error.message) from None
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise
        uploaded_at = datetime.now(UTC).isoformat()
        with self._db.transaction() as uow:
            version = uow.resumes.add(Path(filename).name, directory, uploaded_at, paragraphs, page_count)
        return self.get(version)

    def current(self) -> ResumeVersion | None:
        with self._db.transaction() as uow:
            return uow.resumes.current()

    def get(self, version: int) -> ResumeVersion:
        with self._db.transaction() as uow:
            resume = uow.resumes.get(version)
        if resume is None:
            raise NotFoundError("Resume version not found.")
        return resume

    def versions(self) -> list[ResumeVersion]:
        with self._db.transaction() as uow:
            return uow.resumes.all()

    def file(self, version: int, name: str) -> Path:
        return self._dir / self.get(version).directory / name

    def master(self) -> MasterResume | None:
        """The current version, or None until it's uploaded and its Summary and Skills are marked."""
        resume = self.current()
        if resume is None or not resume.ready or resume.skills is None:
            return None
        text = "\n".join(p.text for p in resume.paragraphs if p.text)
        return MasterResume(resume.version, text, resume.skills)

    def save_mapping(self, summary: list[int], skills: list[int]) -> ResumeVersion:
        resume = self._current()
        summary, skills = sorted(set(summary)), sorted(set(skills))
        if not summary:
            raise InvalidRequestError("Mark at least one paragraph as your Summary.")
        if not skills:
            raise InvalidRequestError("Mark at least one paragraph as your Skills section.")
        if set(summary) & set(skills):
            raise InvalidRequestError("A paragraph can be part of the Summary or the Skills section, not both.")
        for index in summary + skills:
            if not 0 <= index < len(resume.paragraphs):
                raise InvalidRequestError(f"Paragraph {index} isn't in this resume.")
            if not resume.paragraphs[index].text:
                raise InvalidRequestError("Blank paragraphs can't be part of the Summary or Skills section.")
        listed = skills_from_text([resume.paragraphs[i].text for i in skills])
        if not listed:
            raise InvalidRequestError("The paragraphs marked as Skills don't list any skills.")
        # Keep my edits to the skills list unless the Skills section itself changed.
        keep = resume.skills is not None and resume.skills_paragraphs == skills
        with self._db.transaction() as uow:
            uow.resumes.save_mapping(
                resume.version, summary, skills, resume.skills if keep and resume.skills else listed
            )
        return self.get(resume.version)

    def save_skills(self, skills: list[str]) -> ResumeVersion:
        resume = self._current()
        if not resume.mapped:
            raise ConflictError("Mark your Summary and Skills paragraphs first.")
        cleaned: list[str] = []
        for skill in skills:
            if len(" ".join(skill.split())) > MAX_SKILL_LENGTH:
                raise InvalidRequestError(f"Keep each skill under {MAX_SKILL_LENGTH} characters.")
            add_skill(cleaned, skill)
        if not cleaned:
            raise InvalidRequestError("Keep at least one skill in your master skills list.")
        if len(cleaned) > MAX_SKILLS:
            raise InvalidRequestError(f"Keep your master skills list to {MAX_SKILLS} skills or fewer.")
        with self._db.transaction() as uow:
            uow.resumes.save_skills(resume.version, cleaned)
        return self.get(resume.version)

    def _current(self) -> ResumeVersion:
        resume = self.current()
        if resume is None:
            raise NotFoundError("Upload your resume first.")
        return resume
