import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime

from job_tracker.companies import Platform
from job_tracker.postings import Posting
from job_tracker.sources import JobBoardSource


def _now() -> str:
    return datetime.now(UTC).isoformat()


def execute_run(conn: sqlite3.Connection, sources: Mapping[Platform, JobBoardSource]) -> int:
    """Fetch every enabled company's board and store its postings. Returns the run ID."""
    run_id = conn.execute("INSERT INTO runs (started_at) VALUES (?)", (_now(),)).lastrowid
    assert run_id is not None
    companies = conn.execute("SELECT platform, board_id FROM companies WHERE enabled = 1").fetchall()
    for company in companies:
        postings = sources[company["platform"]].fetch(company["board_id"])
        seen_at = _now()
        for posting in postings:
            _store(conn, posting, seen_at)
        conn.execute(
            "UPDATE companies SET last_fetched_at = ? WHERE platform = ? AND board_id = ?",
            (seen_at, company["platform"], company["board_id"]),
        )
    conn.execute("UPDATE runs SET finished_at = ? WHERE id = ?", (_now(), run_id))
    return run_id


def _store(conn: sqlite3.Connection, posting: Posting, seen_at: str) -> None:
    salary = posting.salary
    conn.execute(
        """
        INSERT INTO jobs (
            platform, board_id, external_id, title, locations, remote,
            salary_min, salary_max, salary_currency, description,
            posting_url, application_url, updated_at, first_seen_at, last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (platform, external_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
        """,
        (
            posting.platform,
            posting.board_id,
            posting.external_id,
            posting.title,
            json.dumps(posting.locations),
            posting.remote,
            salary.minimum if salary else None,
            salary.maximum if salary else None,
            salary.currency if salary else None,
            posting.description,
            posting.posting_url,
            posting.application_url,
            posting.updated_at,
            seen_at,
            seen_at,
        ),
    )
