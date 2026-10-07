import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from job_tracker.companies import Company

_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY,
    platform TEXT NOT NULL,
    board_id TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
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
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT,
    description TEXT NOT NULL,
    posting_url TEXT NOT NULL,
    application_url TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE (platform, external_id)
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self._path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def initialize(self, starter_companies: list[Company]) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA)
            if conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO companies (platform, board_id) VALUES (?, ?)",
                    [(c.platform, c.board_id) for c in starter_companies],
                )
