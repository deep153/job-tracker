import sqlite3

from job_tracker.models.answers import AnswerCategory, BankEntry


class AnswerBankRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list(self) -> list[BankEntry]:
        rows = self._conn.execute("SELECT * FROM answer_bank ORDER BY category, id").fetchall()
        return [_entry(row) for row in rows]

    def get(self, entry_id: int) -> BankEntry | None:
        row = self._conn.execute("SELECT * FROM answer_bank WHERE id = ?", (entry_id,)).fetchone()
        return None if row is None else _entry(row)

    def create(self, question: str, answer: str, category: AnswerCategory, now: str) -> int:
        entry_id = self._conn.execute(
            "INSERT INTO answer_bank (question, answer, category, created_at) VALUES (?, ?, ?, ?)",
            (question, answer, category, now),
        ).lastrowid
        assert entry_id is not None
        return entry_id

    def update(self, entry_id: int, question: str, answer: str, category: AnswerCategory) -> None:
        self._conn.execute(
            "UPDATE answer_bank SET question = ?, answer = ?, category = ? WHERE id = ?",
            (question, answer, category, entry_id),
        )

    def delete(self, entry_id: int) -> bool:
        return self._conn.execute("DELETE FROM answer_bank WHERE id = ?", (entry_id,)).rowcount > 0

    def mark_used(self, entry_ids: set[int], now: str) -> None:
        self._conn.executemany(
            "UPDATE answer_bank SET last_used_at = ? WHERE id = ?", [(now, entry_id) for entry_id in entry_ids]
        )


def _entry(row: sqlite3.Row) -> BankEntry:
    return BankEntry(
        id=row["id"],
        question=row["question"],
        answer=row["answer"],
        category=row["category"],
        created_at=row["created_at"],
        last_used_at=row["last_used_at"],
    )
