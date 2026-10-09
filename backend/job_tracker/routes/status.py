from typing import Any

from fastapi import APIRouter

from job_tracker.clients.libreoffice import MISSING_MESSAGE
from job_tracker.routes.dependencies import ServicesDep

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("")
def get_status(services: ServicesDep) -> dict[str, Any]:
    available = services.office.available
    return {"libreoffice": {"available": available, "message": None if available else MISSING_MESSAGE}}
