from typing import Any

from job_tracker.models.ai import SUGGESTED_MODELS, AiSettings, CostSummary
from job_tracker.models.platform import Platform
from job_tracker.models.search_settings import SearchSettings


def secret_json(key: str | None) -> dict[str, Any]:
    """Whether a key is set, and its last four characters; never the key itself."""
    return {"set": key is not None, "last4": key[-4:] if key else None}


def search_settings_json(
    settings: SearchSettings,
    platforms: list[tuple[Platform, str, bool]],
    search_api_key: str | None,
    missing: list[str],
) -> dict[str, Any]:
    return {
        "roles": settings.roles,
        "locations": settings.locations,
        "work_modes": settings.work_modes,
        "platforms": settings.platforms,
        "excluded_keywords": settings.excluded_keywords,
        "seniority": settings.seniority,
        "years_experience": settings.years_experience,
        "needs_sponsorship": settings.needs_sponsorship,
        "min_salary": settings.min_salary,
        "min_score": settings.min_score,
        "available_platforms": [{"id": p, "name": name, "supported": ok} for p, name, ok in platforms],
        "search_api_key": secret_json(search_api_key),
        "missing": missing,
        "ready": not missing,
    }


def ai_settings_json(settings: AiSettings) -> dict[str, Any]:
    return {
        "anthropic_api_key": secret_json(settings.anthropic_api_key),
        "scoring_model": settings.scoring_model,
        "tailoring_model": settings.tailoring_model,
        "suggested_models": SUGGESTED_MODELS,
    }


def costs_json(summary: CostSummary) -> dict[str, Any]:
    return {
        "total_usd": summary.total_usd,
        "by_kind": [
            {
                "kind": usage.kind,
                "calls": usage.calls,
                "cost_usd": usage.cost_usd,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            }
            for usage in summary.by_kind
        ],
        "recent_runs": [
            {
                "id": run.run_id,
                "started_at": run.started_at,
                "scored_jobs": run.scored_jobs,
                "ai_cost_usd": run.ai_cost_usd,
            }
            for run in summary.recent_runs
        ],
    }
