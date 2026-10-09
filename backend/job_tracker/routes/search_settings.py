from typing import Any

from fastapi import APIRouter

from job_tracker.container import Services
from job_tracker.routes.dependencies import ServicesDep
from job_tracker.serializers.settings import search_settings_json
from job_tracker.validators.search_settings import SearchSettingsIn

router = APIRouter(prefix="/api/search-settings", tags=["settings"])


def _search_settings(services: Services) -> dict[str, Any]:
    settings = services.settings
    return search_settings_json(
        settings.search(), settings.platforms(), settings.search_api_key(), services.runs.missing()
    )


@router.get("")
def get_search_settings(services: ServicesDep) -> dict[str, Any]:
    return _search_settings(services)


@router.put("")
def save_search_settings(body: SearchSettingsIn, services: ServicesDep) -> dict[str, Any]:
    services.settings.save_search(body.to_model())
    return _search_settings(services)
