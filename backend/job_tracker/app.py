import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI

from job_tracker.companies import STARTER_COMPANIES, Company
from job_tracker.db import Database
from job_tracker.runs import execute_run
from job_tracker.sources import job_board_sources


def create_app(
    db_path: Path,
    http: httpx.Client,
    starter_companies: list[Company] = STARTER_COMPANIES,
) -> FastAPI:
    db = Database(db_path)
    db.initialize(starter_companies)
    sources = job_board_sources(http)
    app = FastAPI(title="Job Tracker")

    @app.post("/api/runs", status_code=201)
    def start_run() -> dict[str, Any]:
        with db.connect() as conn:
            run_id = execute_run(conn, sources)
            return _run_json(conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone())

    @app.get("/api/jobs")
    def list_jobs() -> list[dict[str, Any]]:
        with db.connect() as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY updated_at DESC").fetchall()
            return [_job_json(row) for row in rows]

    return app


def _run_json(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "started_at": row["started_at"], "finished_at": row["finished_at"]}


def _job_json(row: sqlite3.Row) -> dict[str, Any]:
    salary = None
    if row["salary_min"] is not None or row["salary_max"] is not None:
        salary = {"min": row["salary_min"], "max": row["salary_max"], "currency": row["salary_currency"]}
    return {
        "id": row["id"],
        "platform": row["platform"],
        "company": row["board_id"],
        "external_id": row["external_id"],
        "title": row["title"],
        "locations": json.loads(row["locations"]),
        "remote": None if row["remote"] is None else bool(row["remote"]),
        "salary": salary,
        "description": row["description"],
        "posting_url": row["posting_url"],
        "application_url": row["application_url"],
        "updated_at": row["updated_at"],
    }


def default_app() -> FastAPI:
    db_path = Path(os.environ.get("JOB_TRACKER_DB", Path.home() / ".job-tracker" / "job-tracker.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_app(db_path=db_path, http=httpx.Client(timeout=30))
