import json
import os
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException

from job_tracker.companies import Company
from job_tracker.db import Database
from job_tracker.runs import RunAlreadyActive, RunService
from job_tracker.sources import job_board_sources


def create_app(
    db_path: Path,
    http: httpx.Client,
    initial_companies: Sequence[Company] = (),
) -> FastAPI:
    db = Database(db_path)
    db.initialize(initial_companies)
    runs = RunService(db, job_board_sources(http))
    app = FastAPI(title="Job Tracker")

    @app.post("/api/runs", status_code=202)
    def start_run() -> dict[str, Any]:
        try:
            run_id = runs.start()
        except RunAlreadyActive:
            raise HTTPException(status_code=409, detail="A run is already in progress.") from None
        return get_run(run_id)

    @app.get("/api/runs")
    def list_runs() -> list[dict[str, Any]]:
        with db.connect() as conn:
            rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 20").fetchall()
            return [_run_json(row) for row in rows]

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: int) -> dict[str, Any]:
        with db.connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        return _run_json(row)

    @app.get("/api/jobs")
    def list_jobs() -> list[dict[str, Any]]:
        with db.connect() as conn:
            rows = conn.execute("SELECT * FROM jobs WHERE closed = 0 ORDER BY updated_at DESC").fetchall()
            return [_job_json(row) for row in rows]

    return app


def _run_json(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "status": row["status"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "companies_total": row["companies_total"],
        "companies_fetched": row["companies_fetched"],
        "new_jobs": row["new_jobs"],
        "updated_jobs": row["updated_jobs"],
        "closed_jobs": row["closed_jobs"],
        "errors": json.loads(row["errors"]),
    }


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
