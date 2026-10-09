from typing import Any

from fastapi import APIRouter

from job_tracker.routes.dependencies import ServicesDep
from job_tracker.serializers.jobs import company_json
from job_tracker.validators.companies import CompanyUpdate

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("")
def list_companies(services: ServicesDep) -> list[dict[str, Any]]:
    return [company_json(company) for company in services.jobs.companies()]


@router.patch("/{company_id}")
def update_company(company_id: int, body: CompanyUpdate, services: ServicesDep) -> dict[str, Any]:
    return company_json(services.jobs.set_company_blocked(company_id, body.blocked))
