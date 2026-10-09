import os
from pathlib import Path

import httpx
from fastapi import FastAPI

from job_tracker.clients.claude import LLM
from job_tracker.clients.libreoffice import LibreOffice
from job_tracker.container import build_services
from job_tracker.routes import companies, jobs, resume, runs, search_settings, settings, status
from job_tracker.routes.errors import register_error_handlers


def create_app(db_path: Path, http: httpx.Client, office: LibreOffice | None = None, llm: LLM | None = None) -> FastAPI:
    app = FastAPI(title="Job Tracker")
    app.state.services = build_services(db_path, http, office, llm)
    register_error_handlers(app)
    for module in (status, resume, search_settings, settings, runs, companies, jobs):
        app.include_router(module.router)
    return app


def default_app() -> FastAPI:
    db_path = Path(os.environ.get("JOB_TRACKER_DB", Path.home() / ".job-tracker" / "job-tracker.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_app(db_path=db_path, http=httpx.Client(timeout=30))
