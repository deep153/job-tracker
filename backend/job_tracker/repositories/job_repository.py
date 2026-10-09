import json
import sqlite3

from job_tracker.models.job import FitScore, Job, Rejection
from job_tracker.models.posting import Posting, SalaryRange

# The newest score for each job, whichever resume version it was scored against.
_LATEST_SCORES = """
    SELECT scores.* FROM scores
    JOIN (SELECT job_id, MAX(id) AS id FROM scores GROUP BY job_id) AS newest ON newest.id = scores.id
"""

# Open jobs at companies that aren't blocked, with their latest score.
_VISIBLE = f"""
    SELECT jobs.*, latest.id AS score_id, latest.score, latest.reasons, latest.matched_keywords,
        latest.missing_keywords, latest.model, latest.resume_version, latest.scored_at
    FROM jobs
    JOIN companies ON companies.platform = jobs.platform AND companies.board_id = jobs.board_id
    LEFT JOIN ({_LATEST_SCORES}) AS latest ON latest.job_id = jobs.id
    WHERE jobs.closed = 0 AND companies.blocked = 0
"""


class JobRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def find_by_external_id(self, platform: str, external_id: str) -> Job | None:
        return self._one("SELECT * FROM jobs WHERE platform = ? AND external_id = ?", (platform, external_id))

    def find_by_content(self, platform: str, board_id: str, content_hash: str) -> Job | None:
        return self._one(
            "SELECT * FROM jobs WHERE platform = ? AND board_id = ? AND content_hash = ?",
            (platform, board_id, content_hash),
        )

    def insert(self, posting: Posting, content_hash: str, seen_at: str) -> int:
        job_id = self._conn.execute(
            """
            INSERT INTO jobs (
                external_id, title, locations, remote, work_mode, salary_min, salary_max, salary_currency,
                description, posting_url, application_url, updated_at,
                platform, board_id, content_hash, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*_posting_fields(posting), posting.platform, posting.board_id, content_hash, seen_at, seen_at),
        ).lastrowid
        assert job_id is not None
        return job_id

    def update(self, job_id: int, posting: Posting, content_hash: str, seen_at: str) -> None:
        """Store what the board says now, and reopen the job if it was closed."""
        self._conn.execute(
            """
            UPDATE jobs SET
                external_id = ?, title = ?, locations = ?, remote = ?, work_mode = ?, salary_min = ?,
                salary_max = ?, salary_currency = ?, description = ?, posting_url = ?, application_url = ?,
                updated_at = ?, content_hash = ?, last_seen_at = ?, closed = 0
            WHERE id = ?
            """,
            (*_posting_fields(posting), content_hash, seen_at, job_id),
        )

    def open_ids(self, platform: str, board_id: str) -> list[int]:
        rows = self._conn.execute(
            "SELECT id FROM jobs WHERE platform = ? AND board_id = ? AND closed = 0", (platform, board_id)
        ).fetchall()
        return [row["id"] for row in rows]

    def close(self, job_ids: list[int]) -> None:
        self._conn.executemany("UPDATE jobs SET closed = 1 WHERE id = ?", [(job_id,) for job_id in job_ids])

    def open_jobs(self, job_ids: list[int] | None = None) -> list[Job]:
        """Open jobs, or the jobs with these IDs (open or not)."""
        if job_ids is None:
            return self._many("SELECT * FROM jobs WHERE closed = 0")
        if not job_ids:
            return []
        return self._many(f"SELECT * FROM jobs WHERE id IN ({','.join('?' * len(job_ids))})", job_ids)

    def save_verdicts(self, verdicts: list[tuple[int, Rejection | None]]) -> None:
        self._conn.executemany(
            "UPDATE jobs SET rejected_rule = ?, rejected_reason = ? WHERE id = ?",
            [
                (rejection.rule if rejection else None, rejection.reason if rejection else None, job_id)
                for job_id, rejection in verdicts
            ],
        )

    def needing_score(self, resume_version: int) -> list[Job]:
        """Visible jobs that passed the filters and have no score for this resume version and their content."""
        return self._many(
            f"""
            {_VISIBLE} AND jobs.rejected_rule IS NULL AND NOT EXISTS (
                SELECT 1 FROM scores WHERE scores.job_id = jobs.id AND scores.resume_version = ?
                    AND scores.content_hash = jobs.content_hash
            )
            ORDER BY jobs.id
            """,
            (resume_version,),
        )

    def matches(self, min_score: int) -> list[Job]:
        """Visible jobs that passed the filters and scored at least `min_score`, best first."""
        return self._many(
            f"""
            {_VISIBLE} AND jobs.rejected_rule IS NULL AND latest.score >= ?
            ORDER BY latest.score DESC, jobs.updated_at DESC
            """,
            (min_score,),
        )

    def below_threshold(self, min_score: int) -> list[Job]:
        """Visible jobs that passed the filters but aren't scored yet (first) or scored under `min_score`."""
        return self._many(
            f"""
            {_VISIBLE} AND jobs.rejected_rule IS NULL AND (latest.score IS NULL OR latest.score < ?)
            ORDER BY latest.score IS NOT NULL, latest.score DESC, jobs.updated_at DESC
            """,
            (min_score,),
        )

    def filtered_out(self) -> list[Job]:
        return self._many(f"{_VISIBLE} AND jobs.rejected_rule IS NOT NULL ORDER BY jobs.updated_at DESC")

    def _one(self, sql: str, params: tuple[object, ...]) -> Job | None:
        row = self._conn.execute(sql, params).fetchone()
        return None if row is None else _job(row)

    def _many(self, sql: str, params: tuple[object, ...] | list[int] = ()) -> list[Job]:
        return [_job(row) for row in self._conn.execute(sql, params).fetchall()]


def _posting_fields(posting: Posting) -> tuple[object, ...]:
    salary = posting.salary
    return (
        posting.external_id,
        posting.title,
        json.dumps(posting.locations),
        posting.remote,
        posting.work_mode,
        salary.minimum if salary else None,
        salary.maximum if salary else None,
        salary.currency if salary else None,
        posting.description,
        posting.posting_url,
        posting.application_url,
        posting.updated_at,
    )


def _job(row: sqlite3.Row) -> Job:
    salary = None
    if row["salary_min"] is not None or row["salary_max"] is not None:
        salary = SalaryRange(row["salary_min"], row["salary_max"], row["salary_currency"])
    posting = Posting(
        platform=row["platform"],
        board_id=row["board_id"],
        external_id=row["external_id"],
        title=row["title"],
        locations=json.loads(row["locations"]),
        remote=None if row["remote"] is None else bool(row["remote"]),
        work_mode=row["work_mode"],
        salary=salary,
        description=row["description"],
        posting_url=row["posting_url"],
        application_url=row["application_url"],
        updated_at=row["updated_at"],
    )
    rejection = Rejection(row["rejected_rule"], row["rejected_reason"]) if row["rejected_rule"] else None
    return Job(
        id=row["id"],
        posting=posting,
        content_hash=row["content_hash"],
        closed=bool(row["closed"]),
        rejection=rejection,
        score=_score(row),
    )


def _score(row: sqlite3.Row) -> FitScore | None:
    if "score_id" not in row.keys() or row["score_id"] is None:
        return None
    return FitScore(
        score=row["score"],
        reasons=json.loads(row["reasons"]),
        matched_keywords=json.loads(row["matched_keywords"]),
        missing_keywords=json.loads(row["missing_keywords"]),
        model=row["model"],
        resume_version=row["resume_version"],
        scored_at=row["scored_at"],
    )
