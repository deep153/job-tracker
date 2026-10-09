from typing import Any

from fastapi import APIRouter, Response

from job_tracker.routes.dependencies import ServicesDep
from job_tracker.serializers.settings import ai_settings_json, costs_json
from job_tracker.validators.settings import ApiKeyIn, ModelsIn

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings(services: ServicesDep) -> dict[str, Any]:
    return ai_settings_json(services.settings.ai())


@router.put("/search-api-key", status_code=204)
def save_search_api_key(body: ApiKeyIn, services: ServicesDep) -> Response:
    services.settings.set_search_api_key(body.key)
    return Response(status_code=204)


@router.put("/anthropic-api-key")
def save_anthropic_api_key(body: ApiKeyIn, services: ServicesDep) -> dict[str, Any]:
    return ai_settings_json(services.settings.set_anthropic_api_key(body.key))


@router.put("/models")
def save_models(body: ModelsIn, services: ServicesDep) -> dict[str, Any]:
    return ai_settings_json(services.settings.set_models(body.scoring_model, body.tailoring_model))


@router.get("/costs")
def get_costs(services: ServicesDep) -> dict[str, Any]:
    return costs_json(services.costs.summary())
