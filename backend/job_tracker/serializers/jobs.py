from dataclasses import asdict
from typing import Any

from job_tracker.models.company import Company
from job_tracker.models.job import Job


def job_json(job: Job) -> dict[str, Any]:
    posting, salary = job.posting, job.posting.salary
    return {
        "id": job.id,
        "platform": posting.platform,
        "company": posting.board_id,
        "external_id": posting.external_id,
        "title": posting.title,
        "locations": posting.locations,
        "remote": posting.remote,
        "work_mode": posting.work_mode,
        "salary": None
        if salary is None
        else {"min": salary.minimum, "max": salary.maximum, "currency": salary.currency},
        "description": posting.description,
        "posting_url": posting.posting_url,
        "application_url": posting.application_url,
        "updated_at": posting.updated_at,
        "score": None if job.score is None else asdict(job.score),
    }


def filtered_job_json(job: Job) -> dict[str, Any]:
    assert job.rejection is not None
    return {**job_json(job), "rejection": asdict(job.rejection)}


def company_json(company: Company) -> dict[str, Any]:
    return asdict(company)
