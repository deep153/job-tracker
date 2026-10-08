import hashlib
import json
import sqlite3
from dataclasses import dataclass, field

from job_tracker.companies import Platform
from job_tracker.postings import Posting, SalaryRange


@dataclass
class SyncResult:
    new: int = 0
    updated: int = 0
    closed: int = 0
    # New, changed and reopened jobs: the ones whose filter verdict may have changed.
    to_filter: list[int] = field(default_factory=list)


def content_hash(posting: Posting) -> str:
    """Identifies a posting by what it says, so a repost under a new ID is recognized."""
    content = json.dumps([posting.title.strip(), posting.locations, posting.description.strip()])
    return hashlib.sha256(content.encode()).hexdigest()


def sync_board(
    conn: sqlite3.Connection, platform: Platform, board_id: str, postings: list[Posting], seen_at: str
) -> SyncResult:
    """Bring stored jobs for one board in line with what the board lists right now."""
    result = SyncResult()
    seen: set[int] = set()
    for posting in postings:
        digest = content_hash(posting)
        existing = conn.execute(
            "SELECT id, content_hash, closed FROM jobs WHERE platform = ? AND external_id = ?",
            (platform, posting.external_id),
        ).fetchone()
        if existing is None:
            existing = conn.execute(
                "SELECT id, content_hash, closed FROM jobs WHERE platform = ? AND board_id = ? AND content_hash = ?",
                (platform, board_id, digest),
            ).fetchone()
            if existing is not None and existing["id"] in seen:
                continue  # the same job listed twice on this board
        if existing is None:
            job_id = _insert(conn, posting, digest, seen_at)
            seen.add(job_id)
            result.new += 1
            result.to_filter.append(job_id)
            continue
        if existing["content_hash"] != digest:
            result.updated += 1
        if existing["content_hash"] != digest or existing["closed"]:
            result.to_filter.append(existing["id"])
        _update(conn, existing["id"], posting, digest, seen_at)
        seen.add(existing["id"])

    open_ids = conn.execute(
        "SELECT id FROM jobs WHERE platform = ? AND board_id = ? AND closed = 0", (platform, board_id)
    ).fetchall()
    gone = [row["id"] for row in open_ids if row["id"] not in seen]
    conn.executemany("UPDATE jobs SET closed = 1 WHERE id = ?", [(job_id,) for job_id in gone])
    result.closed = len(gone)
    return result


def _fields(posting: Posting) -> tuple[object, ...]:
    salary = posting.salary
    return (
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
    )


def stored_posting(row: sqlite3.Row) -> Posting:
    """The posting a `jobs` row was stored from."""
    salary = None
    if row["salary_min"] is not None or row["salary_max"] is not None:
        salary = SalaryRange(row["salary_min"], row["salary_max"], row["salary_currency"])
    return Posting(
        platform=row["platform"],
        board_id=row["board_id"],
        external_id=row["external_id"],
        title=row["title"],
        locations=json.loads(row["locations"]),
        remote=None if row["remote"] is None else bool(row["remote"]),
        salary=salary,
        description=row["description"],
        posting_url=row["posting_url"],
        application_url=row["application_url"],
        updated_at=row["updated_at"],
    )


def _insert(conn: sqlite3.Connection, posting: Posting, digest: str, seen_at: str) -> int:
    job_id = conn.execute(
        """
        INSERT INTO jobs (
            external_id, title, locations, remote, salary_min, salary_max, salary_currency,
            description, posting_url, application_url, updated_at,
            platform, board_id, content_hash, first_seen_at, last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (*_fields(posting), posting.platform, posting.board_id, digest, seen_at, seen_at),
    ).lastrowid
    assert job_id is not None
    return job_id


def _update(conn: sqlite3.Connection, job_id: int, posting: Posting, digest: str, seen_at: str) -> None:
    conn.execute(
        """
        UPDATE jobs SET
            external_id = ?, title = ?, locations = ?, remote = ?, salary_min = ?, salary_max = ?,
            salary_currency = ?, description = ?, posting_url = ?, application_url = ?, updated_at = ?,
            content_hash = ?, last_seen_at = ?, closed = 0
        WHERE id = ?
        """,
        (*_fields(posting), digest, seen_at, job_id),
    )
