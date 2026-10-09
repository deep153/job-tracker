from typing import Any

from fastapi import APIRouter

from job_tracker.routes.dependencies import ServicesDep
from job_tracker.serializers.jobs import filtered_job_json, job_json

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
def list_jobs(services: ServicesDep) -> list[dict[str, Any]]:
    """Jobs scored at or above my threshold, best first."""
    return [job_json(job) for job in services.jobs.matches()]


@router.get("/below-threshold")
def list_jobs_below_threshold(services: ServicesDep) -> list[dict[str, Any]]:
    """Scored below my threshold, or not scored yet (those come first)."""
    return [job_json(job) for job in services.jobs.below_threshold()]


@router.get("/filtered-out")
def list_filtered_out_jobs(services: ServicesDep) -> list[dict[str, Any]]:
    return [filtered_job_json(job) for job in services.jobs.filtered_out()]
