"""My answer bank: saved answers to the standard questions application forms ask."""

from datetime import UTC, datetime

from job_tracker.database import Database
from job_tracker.models.answers import AnswerCategory, BankEntry
from job_tracker.services.errors import InvalidRequestError, NotFoundError


def _clean(text: str) -> str:
    return " ".join(text.split())


class AnswerBankService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list(self) -> list[BankEntry]:
        with self._db.transaction() as uow:
            return uow.answer_bank.list()

    def create(self, question: str, answer: str, category: AnswerCategory) -> BankEntry:
        question, answer = self._checked(None, question, answer)
        with self._db.transaction() as uow:
            entry_id = uow.answer_bank.create(question, answer, category, datetime.now(UTC).isoformat())
        return self._get(entry_id)

    def update(self, entry_id: int, question: str, answer: str, category: AnswerCategory) -> BankEntry:
        self._get(entry_id)
        question, answer = self._checked(entry_id, question, answer)
        with self._db.transaction() as uow:
            uow.answer_bank.update(entry_id, question, answer, category)
        return self._get(entry_id)

    def delete(self, entry_id: int) -> None:
        with self._db.transaction() as uow:
            deleted = uow.answer_bank.delete(entry_id)
        if not deleted:
            raise NotFoundError("Answer not found.")

    def _get(self, entry_id: int) -> BankEntry:
        with self._db.transaction() as uow:
            entry = uow.answer_bank.get(entry_id)
        if entry is None:
            raise NotFoundError("Answer not found.")
        return entry

    def _checked(self, entry_id: int | None, question: str, answer: str) -> tuple[str, str]:
        question = _clean(question)
        answer = answer.strip()
        if not question:
            raise InvalidRequestError("Write the question.")
        if not answer:
            raise InvalidRequestError("Write the answer.")
        if any(e.question.casefold() == question.casefold() and e.id != entry_id for e in self.list()):
            raise InvalidRequestError(f"You already have an answer for “{question}”.")
        return question, answer
