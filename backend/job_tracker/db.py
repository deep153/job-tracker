import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from job_tracker.timestamps import utc_timestamp

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY,
    platform TEXT NOT NULL,
    board_id TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    discovered_query TEXT NOT NULL,
    blocked INTEGER NOT NULL DEFAULT 0,
    last_fetched_at TEXT,
    last_error TEXT,
    UNIQUE (platform, board_id)
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    platform TEXT NOT NULL,
    board_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    locations TEXT NOT NULL,
    remote INTEGER,
    work_mode TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT,
    description TEXT NOT NULL,
    posting_url TEXT NOT NULL,
    application_url TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    closed INTEGER NOT NULL DEFAULT 0,
    rejected_rule TEXT,
    rejected_reason TEXT,
    UNIQUE (platform, external_id)
);

CREATE INDEX IF NOT EXISTS jobs_by_board_content ON jobs (platform, board_id, content_hash);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    status TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'discovering',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    search_queries INTEGER NOT NULL DEFAULT 0,
    search_queries_capped INTEGER NOT NULL DEFAULT 0,
    companies_discovered INTEGER NOT NULL DEFAULT 0,
    companies_total INTEGER NOT NULL DEFAULT 0,
    companies_fetched INTEGER NOT NULL DEFAULT 0,
    new_jobs INTEGER NOT NULL DEFAULT 0,
    updated_jobs INTEGER NOT NULL DEFAULT 0,
    closed_jobs INTEGER NOT NULL DEFAULT 0,
    filtered_out TEXT NOT NULL DEFAULT '{}',
    errors TEXT NOT NULL DEFAULT '[]',
    scoring_total INTEGER NOT NULL DEFAULT 0,
    scored_jobs INTEGER NOT NULL DEFAULT 0,
    matched_jobs INTEGER NOT NULL DEFAULT 0,
    ai_cost_usd REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs (id),
    resume_version INTEGER NOT NULL REFERENCES resume_master (id),
    content_hash TEXT NOT NULL,
    score INTEGER NOT NULL,
    reasons TEXT NOT NULL,
    matched_keywords TEXT NOT NULL,
    missing_keywords TEXT NOT NULL,
    model TEXT NOT NULL,
    scored_at TEXT NOT NULL,
    UNIQUE (job_id, resume_version)
);

CREATE TABLE IF NOT EXISTS ai_usage (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    run_id INTEGER REFERENCES runs (id),
    job_id INTEGER REFERENCES jobs (id),
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resume_master (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    directory TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    paragraphs TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    summary_paragraphs TEXT,
    skills_paragraphs TEXT,
    skills TEXT
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self._path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(_SCHEMA)
            _migrate(conn)


# Columns added since a table was first created, which older databases lack.
_ADDED_COLUMNS = {
    "jobs": {"work_mode": "TEXT"},
    "runs": {
        "scoring_total": "INTEGER NOT NULL DEFAULT 0",
        "scored_jobs": "INTEGER NOT NULL DEFAULT 0",
        "matched_jobs": "INTEGER NOT NULL DEFAULT 0",
        "ai_cost_usd": "REAL NOT NULL DEFAULT 0",
    },
}


def _migrate(conn: sqlite3.Connection) -> None:
    """Bring a database created by an earlier version up to the current schema."""
    for table, added in _ADDED_COLUMNS.items():
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, declaration in added.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")
    stale = conn.execute("SELECT id, updated_at FROM jobs WHERE updated_at NOT LIKE '%+00:00'").fetchall()
    conn.executemany(
        "UPDATE jobs SET updated_at = ? WHERE id = ?", [(utc_timestamp(row["updated_at"]), row["id"]) for row in stale]
    )
