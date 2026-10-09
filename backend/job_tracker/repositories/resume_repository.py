import json
import sqlite3
from dataclasses import asdict
from typing import Any

from job_tracker.models.resume import ParagraphInfo, ResumeVersion


class ResumeRepository:
    """Versions of the master resume (the `resume_master` table); the newest version is the current one."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(
        self, filename: str, directory: str, uploaded_at: str, paragraphs: list[ParagraphInfo], page_count: int
    ) -> int:
        version = self._conn.execute(
            """
            INSERT INTO resume_master (filename, directory, uploaded_at, paragraphs, page_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (filename, directory, uploaded_at, json.dumps([asdict(p) for p in paragraphs]), page_count),
        ).lastrowid
        assert version is not None
        return version

    def current(self) -> ResumeVersion | None:
        row = self._conn.execute("SELECT * FROM resume_master ORDER BY id DESC LIMIT 1").fetchone()
        return None if row is None else _version(row)

    def get(self, version: int) -> ResumeVersion | None:
        row = self._conn.execute("SELECT * FROM resume_master WHERE id = ?", (version,)).fetchone()
        return None if row is None else _version(row)

    def all(self) -> list[ResumeVersion]:
        return [_version(row) for row in self._conn.execute("SELECT * FROM resume_master ORDER BY id DESC")]

    def save_mapping(self, version: int, summary: list[int], skills_paragraphs: list[int], skills: list[str]) -> None:
        self._conn.execute(
            "UPDATE resume_master SET summary_paragraphs = ?, skills_paragraphs = ?, skills = ? WHERE id = ?",
            (json.dumps(summary), json.dumps(skills_paragraphs), json.dumps(skills), version),
        )

    def save_skills(self, version: int, skills: list[str]) -> None:
        self._conn.execute("UPDATE resume_master SET skills = ? WHERE id = ?", (json.dumps(skills), version))


def _optional_json(value: str | None) -> Any:
    return None if value is None else json.loads(value)


def _version(row: sqlite3.Row) -> ResumeVersion:
    return ResumeVersion(
        version=row["id"],
        filename=row["filename"],
        directory=row["directory"],
        uploaded_at=row["uploaded_at"],
        paragraphs=[ParagraphInfo(**p) for p in json.loads(row["paragraphs"])],
        page_count=row["page_count"],
        summary_paragraphs=_optional_json(row["summary_paragraphs"]),
        skills_paragraphs=_optional_json(row["skills_paragraphs"]),
        skills=_optional_json(row["skills"]),
    )
