"""My profile from my resume: proposed answer-bank entries for review, saved only when I confirm them."""

import logging
from datetime import UTC, datetime

from job_tracker.clients.claude import LLMError
from job_tracker.database import Database
from job_tracker.models.answers import AnswerCategory, BankEntry
from job_tracker.models.profile import (
    Education,
    ProfileAnswer,
    ProfileField,
    ProfileProposal,
    ProfileSection,
)
from job_tracker.services.answer_engine import matching_entry
from job_tracker.services.errors import ConflictError
from job_tracker.services.pricing import estimate_cost
from job_tracker.services.profile_extractor import contact, hyperlinks
from job_tracker.services.profile_reader import ProfileReader, ProfileReading, preferred
from job_tracker.services.resume_service import MASTER_DOCX, ResumeService
from job_tracker.services.settings_service import SettingsService

log = logging.getLogger(__name__)

AUTHORIZED = "Are you legally authorized to work in the United States?"
SPONSORSHIP = "Will you now or in the future require sponsorship for employment visa status?"
HEARD = "How did you hear about this job?"
REFERRED = "Were you referred by a current employee?"

NO_KEY = "Add your Anthropic API key in Settings to also read your name, location and education."


class ProfileService:
    def __init__(self, db: Database, settings: SettingsService, resumes: ResumeService, reader: ProfileReader) -> None:
        self._db = db
        self._settings = settings
        self._resumes = resumes
        self._reader = reader

    def propose(self) -> ProfileProposal:
        """What my current resume says, next to my answer bank's current answers. Nothing is saved."""
        version = self._resumes.current()
        if version is None:
            raise ConflictError("Upload your resume first.")
        texts = [p.text for p in version.paragraphs if p.text]
        found = contact(texts, hyperlinks(self._resumes.file(version.version, MASTER_DOCX).read_bytes()))
        reading, note = self._read("\n".join(texts))
        education = reading.education if reading else []
        selected = preferred(education)
        chosen = education[selected] if selected is not None else Education("", "", "", "", "")
        with self._db.transaction() as uow:
            bank = uow.answer_bank.list()

        def field(question: str, category: AnswerCategory, value: str | None, section: ProfileSection) -> ProfileField:
            current = matching_entry(question, bank)
            return ProfileField(question, category, value or "", current.answer if current else None, section)

        sponsorship = "Yes" if self._settings.search().needs_sponsorship else "No"
        return ProfileProposal(
            fields=[
                field("First Name", "personal", reading.first_name if reading else None, "resume"),
                field("Last Name", "personal", reading.last_name if reading else None, "resume"),
                field("Email", "personal", found.email, "resume"),
                field("Phone", "personal", found.phone, "resume"),
                field("Location (City)", "personal", reading.location if reading else None, "resume"),
                field("Country", "personal", reading.country if reading else None, "resume"),
                field("LinkedIn Profile", "links", found.linkedin, "resume"),
                field("GitHub", "links", found.github, "resume"),
                field("Website", "links", found.website, "resume"),
                field("School", "other", chosen.school, "education"),
                field("Degree", "other", chosen.degree, "education"),
                field("Discipline", "other", chosen.discipline, "education"),
                field("End date month", "other", chosen.end_month, "education"),
                field("End date year", "other", chosen.end_year, "education"),
                field(AUTHORIZED, "work_authorization", None, "questions"),
                field(SPONSORSHIP, "sponsorship", sponsorship, "questions"),
                field(HEARD, "other", None, "questions"),
                field(REFERRED, "other", None, "questions"),
            ],
            education=education,
            selected_education=selected,
            ai_note=note,
        )

    def _read(self, resume_text: str) -> tuple[ProfileReading | None, str | None]:
        """My name, location and education read by AI, or why they couldn't be."""
        ai = self._settings.ai()
        if ai.anthropic_api_key is None:
            return None, NO_KEY
        try:
            reading = self._reader.read(ai.anthropic_api_key, ai.tailoring_model, resume_text)
        except LLMError as error:
            log.warning("reading the profile from the resume failed: %s", error.message)
            return None, f"Couldn't read your name, location and education: {error.message}"
        cost = estimate_cost(reading.model, reading.input_tokens, reading.output_tokens)
        now = datetime.now(UTC).isoformat()
        with self._db.transaction() as uow:
            uow.scores.record_usage(
                "profile", None, None, reading.model, reading.input_tokens, reading.output_tokens, cost, now
            )
        return reading, None

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
