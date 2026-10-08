import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

from job_tracker.companies import ALL_PLATFORMS, PLATFORM_NAMES, Platform
from job_tracker.db import Database
from job_tracker.discovery import BraveSearch, supported_for_discovery
from job_tracker.filtering import refilter_jobs
from job_tracker.filters import RULES
from job_tracker.runs import RunAlreadyActive, RunService, SearchSettingsIncomplete
from job_tracker.search_settings import SearchSettings, Seniority, SettingsStore, WorkMode
from job_tracker.sources import job_board_sources

MAX_SETTING_ITEMS = 20
MAX_SETTING_LENGTH = 100


class SearchSettingsIn(BaseModel):
    roles: list[str] = Field(max_length=MAX_SETTING_ITEMS)
    locations: list[str] = Field(max_length=MAX_SETTING_ITEMS)
    work_modes: list[WorkMode]
    platforms: list[Platform]
    excluded_keywords: list[str] = Field(default_factory=list, max_length=MAX_SETTING_ITEMS)
    seniority: Seniority | None = None
    years_experience: int | None = Field(default=None, ge=0, le=50)
    needs_sponsorship: bool = False
    min_salary: int | None = Field(default=None, ge=0, le=10_000_000)

    @field_validator("roles", "locations", "excluded_keywords")
    @classmethod
    def _clean_terms(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            term = " ".join(value.split())
            if len(term) > MAX_SETTING_LENGTH:
                raise ValueError(f"Keep each entry under {MAX_SETTING_LENGTH} characters.")
            if term and term.casefold() not in {c.casefold() for c in cleaned}:
                cleaned.append(term)
        return cleaned

    @field_validator("work_modes", "platforms")
    @classmethod
    def _dedupe(cls, values: list[Any]) -> list[Any]:
        return list(dict.fromkeys(values))


class SearchApiKeyIn(BaseModel):
    key: str = Field(max_length=500)


class CompanyUpdate(BaseModel):
    blocked: bool


def create_app(db_path: Path, http: httpx.Client) -> FastAPI:
    db = Database(db_path)
    db.initialize()
    settings = SettingsStore(db)
    sources = job_board_sources(http)
    runs = RunService(db, settings, BraveSearch(http), sources)
    app = FastAPI(title="Job Tracker")

    def platform_supported(platform: Platform) -> bool:
        return platform in sources and supported_for_discovery(platform)

    def search_settings_json() -> dict[str, Any]:
        current = settings.search()
        key = settings.search_api_key()
        missing = current.missing(has_search_key=key is not None)
        return {
            "roles": current.roles,
            "locations": current.locations,
            "work_modes": current.work_modes,
            "platforms": current.platforms,
            "excluded_keywords": current.excluded_keywords,
            "seniority": current.seniority,
            "years_experience": current.years_experience,
            "needs_sponsorship": current.needs_sponsorship,
            "min_salary": current.min_salary,
            "available_platforms": [
                {"id": p, "name": PLATFORM_NAMES[p], "supported": platform_supported(p)} for p in ALL_PLATFORMS
            ],
            "search_api_key": {"set": key is not None, "last4": key[-4:] if key else None},
            "missing": missing,
            "ready": not missing,
        }

    @app.get("/api/search-settings")
    def get_search_settings() -> dict[str, Any]:
        return search_settings_json()

    @app.put("/api/search-settings")
    def save_search_settings(body: SearchSettingsIn) -> dict[str, Any]:
        unsupported = [PLATFORM_NAMES[p] for p in body.platforms if not platform_supported(p)]
        if unsupported:
            raise HTTPException(status_code=422, detail=f"{', '.join(unsupported)} isn't supported yet.")
        settings.save_search(SearchSettings(**body.model_dump()))
        with db.connect() as conn:
            refilter_jobs(conn)
        return search_settings_json()

    @app.put("/api/settings/search-api-key", status_code=204)
    def save_search_api_key(body: SearchApiKeyIn) -> Response:
        settings.set_search_api_key(body.key.strip())
        return Response(status_code=204)

    @app.post("/api/runs", status_code=202)
    def start_run() -> dict[str, Any]:
        try:
            run_id = runs.start()
        except SearchSettingsIncomplete as incomplete:
            first = incomplete.missing[0]
            detail = f"Finish your search settings first: {first[0].lower()}{first[1:]}"
            raise HTTPException(status_code=400, detail=detail) from None
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

    @app.get("/api/companies")
    def list_companies() -> list[dict[str, Any]]:
        with db.connect() as conn:
            rows = conn.execute(
                """
                SELECT companies.*, COUNT(jobs.id) AS open_jobs
                FROM companies
                LEFT JOIN jobs ON jobs.platform = companies.platform
                    AND jobs.board_id = companies.board_id AND jobs.closed = 0
                GROUP BY companies.id
                ORDER BY companies.blocked, companies.board_id
                """
            ).fetchall()
            return [_company_json(row) for row in rows]

    @app.patch("/api/companies/{company_id}")
    def update_company(company_id: int, body: CompanyUpdate) -> dict[str, Any]:
        with db.connect() as conn:
            updated = conn.execute(
                "UPDATE companies SET blocked = ? WHERE id = ?", (body.blocked, company_id)
            ).rowcount
        if not updated:
            raise HTTPException(status_code=404, detail="Company not found.")
        return next(c for c in list_companies() if c["id"] == company_id)

    @app.get("/api/jobs")
    def list_jobs() -> list[dict[str, Any]]:
        with db.connect() as conn:
            rows = conn.execute(
                """
                SELECT jobs.* FROM jobs
                JOIN companies ON companies.platform = jobs.platform AND companies.board_id = jobs.board_id
                WHERE jobs.closed = 0 AND companies.blocked = 0 AND jobs.rejected_rule IS NULL
                ORDER BY jobs.updated_at DESC
                """
            ).fetchall()
            return [_job_json(row) for row in rows]

    @app.get("/api/jobs/filtered-out")
    def list_filtered_out_jobs() -> list[dict[str, Any]]:
        with db.connect() as conn:
            rows = conn.execute(
                """
                SELECT jobs.* FROM jobs
                JOIN companies ON companies.platform = jobs.platform AND companies.board_id = jobs.board_id
                WHERE jobs.closed = 0 AND companies.blocked = 0 AND jobs.rejected_rule IS NOT NULL
                ORDER BY jobs.updated_at DESC
                """
            ).fetchall()
            return [
                {**_job_json(row), "rejection": {"rule": row["rejected_rule"], "reason": row["rejected_reason"]}}
                for row in rows
            ]

    return app


def _run_json(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "status": row["status"],
        "stage": row["stage"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "search_queries": row["search_queries"],
        "search_queries_capped": bool(row["search_queries_capped"]),
        "companies_discovered": row["companies_discovered"],
        "companies_total": row["companies_total"],
        "companies_fetched": row["companies_fetched"],
        "new_jobs": row["new_jobs"],
        "updated_jobs": row["updated_jobs"],
        "closed_jobs": row["closed_jobs"],
        "filtered_out": {rule: 0 for rule in RULES} | json.loads(row["filtered_out"]),
        "errors": json.loads(row["errors"]),
    }


def _company_json(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "platform": row["platform"],
        "board_id": row["board_id"],
        "discovered_at": row["discovered_at"],
        "discovered_query": row["discovered_query"],
        "blocked": bool(row["blocked"]),
        "last_fetched_at": row["last_fetched_at"],
        "last_error": row["last_error"],
        "open_jobs": row["open_jobs"],
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
        "work_mode": row["work_mode"],
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
