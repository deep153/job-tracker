from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response

from job_tracker.models.job import JobQuery, JobSort
from job_tracker.routes.dependencies import ServicesDep
from job_tracker.serializers.jobs import filtered_job_json, job_json
from job_tracker.services.job_service import job_query

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _query(
    company: str | None = None,
    location: str | None = None,
    posted_within_days: Annotated[int | None, Query(ge=1)] = None,
    sort: JobSort = "score",
) -> JobQuery:
    return job_query(company, location, posted_within_days, sort)


QueryDep = Annotated[JobQuery, Depends(_query)]


@router.get("")
def list_jobs(services: ServicesDep, query: QueryDep) -> list[dict[str, Any]]:
    """Jobs scored at or above my threshold, best first unless sorted by posted date."""
    return [job_json(job) for job in services.jobs.matches(query)]


@router.get("/below-threshold")
def list_jobs_below_threshold(services: ServicesDep, query: QueryDep) -> list[dict[str, Any]]:
    """Scored below my threshold, or not scored yet (those come first when sorted by score)."""
    return [job_json(job) for job in services.jobs.below_threshold(query)]


@router.get("/filtered-out")
def list_filtered_out_jobs(services: ServicesDep) -> list[dict[str, Any]]:
    return [filtered_job_json(job) for job in services.jobs.filtered_out()]


@router.get("/{job_id}")
def get_job(job_id: int, services: ServicesDep) -> dict[str, Any]:
    job = services.jobs.get(job_id)
    return filtered_job_json(job) if job.rejection else job_json(job)


@router.post("/{job_id}/dismiss", status_code=204)
def dismiss_job(job_id: int, services: ServicesDep) -> Response:
    services.jobs.dismiss(job_id)
    return Response(status_code=204)


@router.post("/{job_id}/rescore")
def rescore_job(job_id: int, services: ServicesDep) -> dict[str, Any]:
    """Calls Claude once, against the current master resume."""
    job = services.jobs.rescore(job_id)
    return filtered_job_json(job) if job.rejection else job_json(job)
