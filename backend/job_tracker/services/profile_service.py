"""My profile from my resume: proposed answer-bank entries for review, saved only when I confirm them."""

from datetime import UTC, datetime

from job_tracker.database import Database
from job_tracker.models.answers import AnswerCategory, BankEntry
from job_tracker.models.profile import ProfileAnswer, ProfileField, ProfileProposal, ProfileSection
from job_tracker.services.answer_engine import matching_entry
from job_tracker.services.errors import ConflictError
from job_tracker.services.profile_extractor import contact, hyperlinks
from job_tracker.services.resume_service import MASTER_DOCX, ResumeService
from job_tracker.services.settings_service import SettingsService

AUTHORIZED = "Are you legally authorized to work in the United States?"
SPONSORSHIP = "Will you now or in the future require sponsorship for employment visa status?"
HEARD = "How did you hear about this job?"
REFERRED = "Were you referred by a current employee?"


class ProfileService:
    def __init__(self, db: Database, settings: SettingsService, resumes: ResumeService) -> None:
        self._db = db
        self._settings = settings
        self._resumes = resumes

    def propose(self) -> ProfileProposal:
        """What my current resume says, next to my answer bank's current answers. Nothing is saved."""
        version = self._resumes.current()
        if version is None:
            raise ConflictError("Upload your resume first.")
        links = hyperlinks(self._resumes.file(version.version, MASTER_DOCX).read_bytes())
        found = contact([p.text for p in version.paragraphs if p.text], links)
        with self._db.transaction() as uow:
            bank = uow.answer_bank.list()

        def field(question: str, category: AnswerCategory, value: str | None, section: ProfileSection) -> ProfileField:
            current = matching_entry(question, bank)
            return ProfileField(question, category, value or "", current.answer if current else None, section)

        sponsorship = "Yes" if self._settings.search().needs_sponsorship else "No"
        return ProfileProposal(
            fields=[
                field("Email", "personal", found.email, "resume"),
                field("Phone", "personal", found.phone, "resume"),
                field("LinkedIn Profile", "links", found.linkedin, "resume"),
                field("GitHub", "links", found.github, "resume"),
                field("Website", "links", found.website, "resume"),
                field(AUTHORIZED, "work_authorization", None, "questions"),
                field(SPONSORSHIP, "sponsorship", sponsorship, "questions"),
                field(HEARD, "other", None, "questions"),
                field(REFERRED, "other", None, "questions"),
            ]
        )

    def apply(self, answers: list[ProfileAnswer]) -> list[BankEntry]:
        """Save my confirmed answers: a new question becomes an entry, an existing one changes only if I chose to
        replace it, and an empty answer is skipped. Returns the answer bank."""
        now = datetime.now(UTC).isoformat()
        with self._db.transaction() as uow:
            for answer in answers:
                question, text = " ".join(answer.question.split()), answer.answer.strip()
                if not question or not text:
                    continue
                existing = matching_entry(question, uow.answer_bank.list())
                if existing is None:
                    uow.answer_bank.create(question, text, answer.category, now)
                elif answer.replace and existing.answer != text:
                    uow.answer_bank.update(existing.id, existing.question, text, existing.category)
            return uow.answer_bank.list()
