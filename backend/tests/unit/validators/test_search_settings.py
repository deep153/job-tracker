from typing import Any

import pytest
from pydantic import ValidationError

from job_tracker.models.search_settings import SearchSettings
from job_tracker.validators.search_settings import MAX_SETTING_ITEMS, MAX_SETTING_LENGTH, SearchSettingsIn

VALID: dict[str, Any] = {
    "roles": ["Backend Engineer"],
    "locations": ["New York, NY"],
    "work_modes": ["remote"],
    "platforms": ["greenhouse"],
}


def test_terms_are_tidied_and_duplicates_dropped() -> None:
    body = SearchSettingsIn(
        **{
            **VALID,
            "roles": ["  Backend   Engineer ", "backend engineer", "", "SRE"],
            "work_modes": ["remote", "remote", "hybrid"],
        }
    )

    assert body.roles == ["Backend Engineer", "SRE"]
    assert body.work_modes == ["remote", "hybrid"]


def test_converts_to_the_model_with_defaults() -> None:
    assert SearchSettingsIn(**VALID).to_model() == SearchSettings(
        roles=["Backend Engineer"], locations=["New York, NY"], work_modes=["remote"], platforms=["greenhouse"]
    )


@pytest.mark.parametrize(
    "change",
    [
        {"roles": ["x" * (MAX_SETTING_LENGTH + 1)]},
        {"roles": [f"Role {n}" for n in range(MAX_SETTING_ITEMS + 1)]},
        {"platforms": ["workday"]},
        {"work_modes": ["anywhere"]},
        {"seniority": "wizard"},
        {"years_experience": -1},
        {"min_score": 101},
    ],
)
def test_bad_values_are_rejected(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SearchSettingsIn(**{**VALID, **change})
