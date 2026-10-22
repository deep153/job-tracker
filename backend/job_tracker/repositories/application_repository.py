import json
import sqlite3
from dataclasses import asdict

from job_tracker.models.answers import FormAnswer, FormField
from job_tracker.models.application import (
    OPEN_STATUSES,
    SENT_STATUSES,
    Application,
    ApplicationStatus,
    TailoredResume,
)
from job_tracker.models.resume import SkillLine

_WITH_RESUME = """
    SELECT applications.*, resume_versions.master_version, resume_versions.directory,
        resume_versions.master_summary, resume_versions.summary, resume_versions.master_skills,
        resume_versions.skills, resume_versions.keywords, resume_versions.covered_before,
        resume_versions.covered_after, resume_versions.page_count, resume_versions.master_page_count,
        resume_versions.gaps, resume_versions.score_before, resume_versions.score_after
    FROM applications
    LEFT JOIN resume_versions ON resume_versions.application_id = applications.id
"""


class ApplicationRepository:
    """Applications, and the resume version tailored for each (the `resume_versions` table)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, job_id: int, now: str) -> int:
        application_id = self._conn.execute(
            "INSERT INTO applications (job_id, status, created_at, updated_at) VALUES (?, 'drafting', ?, ?)",
            (job_id, now, now),
        ).lastrowid
        assert application_id is not None
        return application_id

    def get(self, application_id: int) -> Application | None:
        row = self._conn.execute(f"{_WITH_RESUME} WHERE applications.id = ?", (application_id,)).fetchone()
        return None if row is None else _application(row)

    def list_all(self) -> list[Application]:
        """Newest first, by when each was submitted (or started, if it hasn't been)."""
        rows = self._conn.execute(
            f"{_WITH_RESUME} ORDER BY COALESCE(applications.submitted_at, applications.created_at) DESC,"
            " applications.id DESC"
        ).fetchall()
        return [_application(row) for row in rows]

    def track(self, application_id: int, status: ApplicationStatus, now: str) -> None:
        """Sets a status I chose by hand; marking it `submitted` (I finished it myself) records when."""
        self._conn.execute(
            "UPDATE applications SET status = ?, error = NULL, updated_at = ?,"
            " submitted_at = CASE WHEN ? = 'submitted' THEN ? ELSE submitted_at END WHERE id = ?",
            (status, now, status, now, application_id),
        )

    def open_for_job(self, job_id: int) -> Application | None:
        placeholders = ",".join("?" * len(OPEN_STATUSES))
        row = self._conn.execute(
            f"{_WITH_RESUME} WHERE applications.job_id = ? AND applications.status IN ({placeholders})"
            " ORDER BY applications.id DESC LIMIT 1",
            (job_id, *OPEN_STATUSES),
        ).fetchone()
        return None if row is None else _application(row)

    def sent_for_job(self, job_id: int) -> Application | None:
        placeholders = ",".join("?" * len(SENT_STATUSES))
        row = self._conn.execute(
            f"{_WITH_RESUME} WHERE applications.job_id = ? AND applications.status IN ({placeholders})",
            (job_id, *SENT_STATUSES),
        ).fetchone()
        return None if row is None else _application(row)

    def start_submitting(self, application_id: int, now: str) -> None:
        self._conn.execute(
            "UPDATE applications SET status = 'submitting', error = NULL, screenshot = 0, updated_at = ? WHERE id = ?",
            (now, application_id),
        )

    def finish_submitting(
        self,
        application_id: int,
        status: ApplicationStatus,
        now: str,
        error: str | None = None,
        screenshot: bool = False,
    ) -> None:
        submitted_at = now if status == "submitted" else None
        self._conn.execute(
            "UPDATE applications SET status = ?, error = ?, screenshot = ?, submitted_at = ?, updated_at = ?"
            " WHERE id = ?",
            (status, error, screenshot, submitted_at, now, application_id),
        )

    def interrupt_submitting(self, message: str, now: str) -> None:
        self._conn.execute(
            "UPDATE applications SET status = 'needs_manual', error = ?, updated_at = ? WHERE status = 'submitting'",
            (message, now),
        )

    def failed_for_job(self, job_id: int) -> list[Application]:
        rows = self._conn.execute(
            f"{_WITH_RESUME} WHERE applications.job_id = ? AND applications.status = 'failed'", (job_id,)
        ).fetchall()
        return [_application(row) for row in rows]

    def set_status(self, application_id: int, status: ApplicationStatus, now: str, error: str | None = None) -> bool:
        """False if the application is gone (it was cancelled)."""
        cursor = self._conn.execute(
            "UPDATE applications SET status = ?, error = ?, updated_at = ? WHERE id = ?",
            (status, error, now, application_id),
        )
        return cursor.rowcount > 0

    def add_cost(self, application_id: int, cost_usd: float) -> None:
        self._conn.execute("UPDATE applications SET cost_usd = cost_usd + ? WHERE id = ?", (cost_usd, application_id))

    def save_resume(self, application_id: int, job_id: int, resume: TailoredResume, now: str) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO resume_versions (application_id, job_id, master_version, directory,
                master_summary, summary, master_skills, skills, keywords, covered_before, covered_after,
                page_count, master_page_count, created_at, gaps, score_before, score_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application_id,
                job_id,
                resume.master_version,
                resume.directory,
                json.dumps(resume.master_summary),
                json.dumps(resume.summary),
                json.dumps([asdict(line) for line in resume.master_skills]),
                json.dumps([asdict(line) for line in resume.skills]),
                json.dumps(resume.keywords),
                json.dumps(resume.covered_before),
                json.dumps(resume.covered_after),
                resume.page_count,
                resume.master_page_count,
                now,
                None if resume.gaps is None else json.dumps(resume.gaps),
                resume.score_before,
                resume.score_after,
            ),
        )

    def update_resume(
        self,
        application_id: int,
        summary: list[str],
        skills: list[SkillLine],
        covered_after: list[bool],
        page_count: int,
        now: str,
    ) -> None:
        self._conn.execute(
            """
            UPDATE resume_versions SET summary = ?, skills = ?, covered_after = ?, page_count = ?
            WHERE application_id = ?
            """,
            (
                json.dumps(summary),
                json.dumps([asdict(line) for line in skills]),
                json.dumps(covered_after),
                page_count,
                application_id,
            ),
        )
        self._conn.execute("UPDATE applications SET updated_at = ? WHERE id = ?", (now, application_id))

    def save_cover_letter(self, application_id: int, cover_letter: str | None, now: str) -> None:
        self._conn.execute(
            "UPDATE applications SET cover_letter = ?, updated_at = ? WHERE id = ?", (cover_letter, now, application_id)
        )

    def save_answers(
        self, application_id: int, answers: list[FormAnswer] | None, form_error: str | None, now: str
    ) -> None:
        stored = None if answers is None else json.dumps([asdict(answer) for answer in answers])
        self._conn.execute(
            "UPDATE applications SET answers = ?, form_error = ?, updated_at = ? WHERE id = ?",
            (stored, form_error, now, application_id),
        )

    def delete(self, application_id: int) -> None:
        self._conn.execute("DELETE FROM resume_versions WHERE application_id = ?", (application_id,))
        self._conn.execute("DELETE FROM applications WHERE id = ?", (application_id,))

    def fail_drafting(self, message: str, now: str) -> None:
        self._conn.execute(
            "UPDATE applications SET status = 'failed', error = ?, updated_at = ? WHERE status = 'drafting'",
            (message, now),
        )


def _lines(value: str) -> list[SkillLine]:
    return [SkillLine(**line) for line in json.loads(value)]


def _application(row: sqlite3.Row) -> Application:
    resume = None
    if row["directory"] is not None:
        resume = TailoredResume(
            master_version=row["master_version"],
            directory=row["directory"],
            master_summary=json.loads(row["master_summary"]),
            summary=json.loads(row["summary"]),
            master_skills=_lines(row["master_skills"]),
            skills=_lines(row["skills"]),
            keywords=json.loads(row["keywords"]),
            covered_before=json.loads(row["covered_before"]),
            covered_after=json.loads(row["covered_after"]),
            page_count=row["page_count"],
            master_page_count=row["master_page_count"],
            gaps=None if row["gaps"] is None else json.loads(row["gaps"]),
            score_before=row["score_before"],
            score_after=row["score_after"],
        )
    return Application(
        id=row["id"],
        job_id=row["job_id"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        error=row["error"],
        cost_usd=row["cost_usd"],
        resume=resume,
        answers=None if row["answers"] is None else _answers(row["answers"]),
        form_error=row["form_error"],
        submitted_at=row["submitted_at"],
        screenshot=bool(row["screenshot"]),
        cover_letter=row["cover_letter"],
    )


def _answers(value: str) -> list[FormAnswer]:
    return [
        FormAnswer(
            field=FormField(**answer["field"]),
            answer=answer["answer"],
            source=answer["source"],
            eeo=answer.get("eeo", False),
        )
        for answer in json.loads(value)
    ]
