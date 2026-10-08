import json
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from job_tracker.companies import ALL_PLATFORMS, PLATFORM_NAMES, Platform
from job_tracker.db import Database
from job_tracker.discovery import BraveSearch, supported_for_discovery
from job_tracker.filtering import refilter_jobs
from job_tracker.filters import RULES
from job_tracker.libreoffice import MISSING_MESSAGE, LibreOffice
from job_tracker.llm import LLM, SUGGESTED_MODELS, ClaudeLLM
from job_tracker.resume import MAX_UPLOAD_BYTES, ResumeError, ResumeStore
from job_tracker.runs import RunAlreadyActive, RunService, SetupIncomplete
from job_tracker.scoring import LATEST_SCORES
from job_tracker.search_settings import DEFAULT_MIN_SCORE, SearchSettings, Seniority, SettingsStore, WorkMode
from job_tracker.sources import job_board_sources

log = logging.getLogger(__name__)

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

MAX_SETTING_ITEMS = 20
MAX_SETTING_LENGTH = 100

_MODEL_NAME = re.compile(r"^[a-z0-9][a-z0-9.\-]{1,99}$", re.I)


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
    min_score: int = Field(default=DEFAULT_MIN_SCORE, ge=0, le=100)

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


class ModelsIn(BaseModel):
    scoring_model: str
    tailoring_model: str

    @field_validator("scoring_model", "tailoring_model")
    @classmethod
    def _model_name(cls, value: str) -> str:
        name = value.strip()
        if not _MODEL_NAME.match(name):
            raise ValueError("Enter a Claude model name, like claude-haiku-5-5.")
        return name


class CompanyUpdate(BaseModel):
    blocked: bool


class ResumeMappingIn(BaseModel):
    summary: list[int] = Field(max_length=500)
    skills: list[int] = Field(max_length=500)


class ResumeSkillsIn(BaseModel):
    skills: list[str] = Field(max_length=500)


def create_app(
    db_path: Path, http: httpx.Client, office: LibreOffice | None = None, llm: LLM | None = None
) -> FastAPI:
    db = Database(db_path)
    db.initialize()
    settings = SettingsStore(db)
    sources = job_board_sources(http)
    office = office or LibreOffice.detect()
    if not office.available:
        log.warning(MISSING_MESSAGE)
    resumes = ResumeStore(db, db_path.parent / "files", office)
    runs = RunService(db, settings, resumes, BraveSearch(http), sources, llm or ClaudeLLM())
    app = FastAPI(title="Job Tracker")

    @app.exception_handler(ResumeError)
    def resume_error(request: Request, error: ResumeError) -> JSONResponse:
        return JSONResponse(status_code=error.status, content={"detail": error.message})

    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        return {
            "libreoffice": {"available": office.available, "message": None if office.available else MISSING_MESSAGE}
        }

    @app.get("/api/resume")
    def get_resume() -> dict[str, Any] | None:
        return resumes.current()

    @app.post("/api/resume", status_code=201)
    async def upload_resume(file: UploadFile) -> dict[str, Any]:
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        return await run_in_threadpool(resumes.import_docx, file.filename or "", data)

    @app.put("/api/resume/mapping")
    def save_resume_mapping(body: ResumeMappingIn) -> dict[str, Any]:
        return resumes.save_mapping(body.summary, body.skills)

    @app.put("/api/resume/skills")
    def save_resume_skills(body: ResumeSkillsIn) -> dict[str, Any]:
        return resumes.save_skills(body.skills)

    @app.get("/api/resume/versions")
    def list_resume_versions() -> list[dict[str, Any]]:
        return resumes.versions()

    @app.get("/api/resume/versions/{version}/preview.pdf")
    def get_resume_preview(version: int) -> FileResponse:
        return FileResponse(resumes.file(version, "preview.pdf"), media_type="application/pdf")

    @app.get("/api/resume/versions/{version}/original.docx")
    def get_resume_original(version: int) -> FileResponse:
        resume = resumes.get(version)
        return FileResponse(resumes.file(version, "master.docx"), media_type=DOCX_TYPE, filename=resume["filename"])

    def platform_supported(platform: Platform) -> bool:
        return platform in sources and supported_for_discovery(platform)

    def search_settings_json() -> dict[str, Any]:
        current = settings.search()
        key = settings.search_api_key()
        missing = runs.missing()
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
            "min_score": current.min_score,
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

    def ai_settings_json() -> dict[str, Any]:
        key = settings.anthropic_api_key()
        return {
            "anthropic_api_key": {"set": key is not None, "last4": key[-4:] if key else None},
            "scoring_model": settings.scoring_model(),
            "tailoring_model": settings.tailoring_model(),
            "suggested_models": SUGGESTED_MODELS,
        }

    @app.get("/api/settings")
    def get_settings() -> dict[str, Any]:
        return ai_settings_json()

    @app.put("/api/settings/anthropic-api-key")
    def save_anthropic_api_key(body: SearchApiKeyIn) -> dict[str, Any]:
        settings.set_anthropic_api_key(body.key.strip())
        return ai_settings_json()

    @app.put("/api/settings/models")
    def save_models(body: ModelsIn) -> dict[str, Any]:
        settings.set_models(body.scoring_model, body.tailoring_model)
        return ai_settings_json()

    @app.get("/api/settings/costs")
    def get_costs() -> dict[str, Any]:
        with db.connect() as conn:
            by_kind = conn.execute(
                """
                SELECT kind, COUNT(*) AS calls, SUM(cost_usd) AS cost_usd, SUM(input_tokens) AS input_tokens,
                    SUM(output_tokens) AS output_tokens
                FROM ai_usage GROUP BY kind ORDER BY kind
                """
            ).fetchall()
            recent = conn.execute(
                "SELECT * FROM runs WHERE scoring_total > 0 OR ai_cost_usd > 0 ORDER BY id DESC LIMIT 10"
            ).fetchall()
        return {
            "total_usd": sum(row["cost_usd"] for row in by_kind),
            "by_kind": [
                {
                    "kind": row["kind"],
                    "calls": row["calls"],
                    "cost_usd": row["cost_usd"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                }
                for row in by_kind
            ],
            "recent_runs": [
                {
                    "id": row["id"],
                    "started_at": row["started_at"],
                    "scored_jobs": row["scored_jobs"],
                    "ai_cost_usd": row["ai_cost_usd"],
                }
                for row in recent
            ],
        }

    @app.post("/api/runs", status_code=202)
    def start_run() -> dict[str, Any]:
        try:
            run_id = runs.start()
        except SetupIncomplete as incomplete:
            first = incomplete.missing[0]
            detail = f"Finish setting up first: {first[0].lower()}{first[1:]}"
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

    def passing_jobs(where: str, order: str) -> list[dict[str, Any]]:
        """Open jobs that passed the filters, with their latest score, if any."""
        with db.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT jobs.*, latest.id AS score_id, latest.score, latest.reasons, latest.matched_keywords,
                    latest.missing_keywords, latest.model, latest.resume_version, latest.scored_at
                FROM jobs
                JOIN companies ON companies.platform = jobs.platform AND companies.board_id = jobs.board_id
                LEFT JOIN ({LATEST_SCORES}) AS latest ON latest.job_id = jobs.id
                WHERE jobs.closed = 0 AND companies.blocked = 0 AND jobs.rejected_rule IS NULL AND ({where})
                ORDER BY {order}
                """,
                (settings.search().min_score,),
            ).fetchall()
        return [_job_json(row) for row in rows]

    @app.get("/api/jobs")
    def list_jobs() -> list[dict[str, Any]]:
        return passing_jobs("latest.score >= ?", "latest.score DESC, jobs.updated_at DESC")

    @app.get("/api/jobs/below-threshold")
    def list_jobs_below_threshold() -> list[dict[str, Any]]:
        """Scored below my threshold, or not scored yet (those come first)."""
        return passing_jobs(
            "latest.score IS NULL OR latest.score < ?", "latest.score IS NOT NULL, latest.score DESC, jobs.updated_at DESC"
        )

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
        "scoring_total": row["scoring_total"],
        "scored_jobs": row["scored_jobs"],
        "matched_jobs": row["matched_jobs"],
        "ai_cost_usd": row["ai_cost_usd"],
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
        "score": _score_json(row),
    }


def _score_json(row: sqlite3.Row) -> dict[str, Any] | None:
    if "score_id" not in row.keys() or row["score_id"] is None:
        return None
    return {
        "score": row["score"],
        "reasons": json.loads(row["reasons"]),
        "matched_keywords": json.loads(row["matched_keywords"]),
        "missing_keywords": json.loads(row["missing_keywords"]),
        "model": row["model"],
        "resume_version": row["resume_version"],
        "scored_at": row["scored_at"],
    }


def default_app() -> FastAPI:
    db_path = Path(os.environ.get("JOB_TRACKER_DB", Path.home() / ".job-tracker" / "job-tracker.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_app(db_path=db_path, http=httpx.Client(timeout=30))
