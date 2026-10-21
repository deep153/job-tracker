from typing import Any

from fastapi import APIRouter

from job_tracker.routes.dependencies import ServicesDep
from job_tracker.serializers.runs import run_json

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", status_code=202)
def start_run(services: ServicesDep) -> dict[str, Any]:
    return run_json(services.runs.start())


@router.post("/score", status_code=202)
def start_scoring_run(services: ServicesDep) -> dict[str, Any]:
    """Score the jobs that have no score for my current resume, without searching or fetching."""
    return run_json(services.runs.start_scoring())


@router.get("")
def list_runs(services: ServicesDep) -> list[dict[str, Any]]:
    return [run_json(run) for run in services.runs.recent()]


@router.get("/unscored")
def unscored_jobs(services: ServicesDep) -> dict[str, int]:
    return {"count": services.runs.unscored_count()}


@router.get("/{run_id}")
def get_run(run_id: int, services: ServicesDep) -> dict[str, Any]:
    return run_json(services.runs.get(run_id))
