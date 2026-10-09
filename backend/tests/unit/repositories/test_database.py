import sqlite3
from pathlib import Path

from job_tracker.database import Database


def test_database_from_an_earlier_version_is_upgraded(tmp_path: Path) -> None:
    db_path = tmp_path / "old.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE companies (
                id INTEGER PRIMARY KEY, platform TEXT NOT NULL, board_id TEXT NOT NULL,
                discovered_at TEXT NOT NULL, discovered_query TEXT NOT NULL, blocked INTEGER NOT NULL DEFAULT 0,
                last_fetched_at TEXT, last_error TEXT, UNIQUE (platform, board_id)
            );
            CREATE TABLE jobs (
                id INTEGER PRIMARY KEY, platform TEXT NOT NULL, board_id TEXT NOT NULL, external_id TEXT NOT NULL,
                title TEXT NOT NULL, locations TEXT NOT NULL, remote INTEGER, salary_min INTEGER,
                salary_max INTEGER, salary_currency TEXT, description TEXT NOT NULL, posting_url TEXT NOT NULL,
                application_url TEXT NOT NULL, updated_at TEXT NOT NULL, content_hash TEXT NOT NULL,
                first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, closed INTEGER NOT NULL DEFAULT 0,
                rejected_rule TEXT, rejected_reason TEXT, UNIQUE (platform, external_id)
            );
            CREATE TABLE runs (
                id INTEGER PRIMARY KEY, status TEXT NOT NULL, stage TEXT NOT NULL DEFAULT 'discovering',
                started_at TEXT NOT NULL, finished_at TEXT, search_queries INTEGER NOT NULL DEFAULT 0,
                search_queries_capped INTEGER NOT NULL DEFAULT 0, companies_discovered INTEGER NOT NULL DEFAULT 0,
                companies_total INTEGER NOT NULL DEFAULT 0, companies_fetched INTEGER NOT NULL DEFAULT 0,
                new_jobs INTEGER NOT NULL DEFAULT 0, updated_jobs INTEGER NOT NULL DEFAULT 0,
                closed_jobs INTEGER NOT NULL DEFAULT 0, filtered_out TEXT NOT NULL DEFAULT '{}',
                errors TEXT NOT NULL DEFAULT '[]'
            );
            INSERT INTO companies (platform, board_id, discovered_at, discovered_query)
            VALUES ('greenhouse', 'acme', '2026-10-01T00:00:00+00:00', 'q');
            INSERT INTO jobs (platform, board_id, external_id, title, locations, description, posting_url,
                application_url, updated_at, content_hash, first_seen_at, last_seen_at)
            VALUES ('greenhouse', 'acme', '1', 'Backend Engineer', '[]', '', 'u', 'u', '2026-09-30T14:02:11-04:00',
                'h', '2026-10-01T00:00:00+00:00', '2026-10-01T00:00:00+00:00');
            INSERT INTO runs (status, started_at, finished_at)
            VALUES ('finished', '2026-10-01T00:00:00+00:00', '2026-10-01T00:01:00+00:00');
            """
        )
    db = Database(db_path)

    db.initialize()

    with db.transaction() as uow:
        [job] = uow.jobs.below_threshold(min_score=70)
        [run] = uow.runs.recent(limit=10)
    assert job.posting.updated_at == "2026-09-30T18:02:11+00:00"
    assert job.posting.work_mode is None
    assert job.score is None
    assert (run.scored_jobs, run.matched_jobs, run.ai_cost_usd) == (0, 0, 0)


def test_initializing_twice_is_harmless(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.initialize()
    with db.transaction() as uow:
        uow.settings.set("k", "v")

    db.initialize()

    with db.transaction() as uow:
        assert uow.settings.get("k") == "v"
