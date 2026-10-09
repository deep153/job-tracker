from typing import Any

from pydantic import BaseModel, Field, field_validator

from job_tracker.models.platform import Platform
from job_tracker.models.search_settings import DEFAULT_MIN_SCORE, SearchSettings, Seniority, WorkMode

MAX_SETTING_ITEMS = 20
MAX_SETTING_LENGTH = 100


class SearchSettingsIn(BaseModel):
    roles: list[str] = Field(max_length=MAX_SETTING_ITEMS)
    locations: list[str] = Field(max_length=MAX_SETTING_ITEMS)
    work_modes: list[WorkMode]
    platforms: list[Platform]
    excluded_keywords: list[str] = Field(default_factory=list, max_length=MAX_SETTING_ITEMS)
    seniority: Seniority | None = None
    years_experience: int | None = Field(default=None, ge=0, le=50)
    needs_sponsorship: bool = False
    min_salary: int | None = Field(default=None, ge=0, le=10_000_000)
    min_score: int = Field(default=DEFAULT_MIN_SCORE, ge=0, le=100)

    @field_validator("roles", "locations", "excluded_keywords")
    @classmethod
    def _clean_terms(cls, values: list[str]) -> list[str]:
        """Whitespace tidied, blanks and case-insensitive duplicates dropped."""
        cleaned: list[str] = []
        for value in values:
            term = " ".join(value.split())
            if len(term) > MAX_SETTING_LENGTH:
                raise ValueError(f"Keep each entry under {MAX_SETTING_LENGTH} characters.")
            if term and term.casefold() not in {c.casefold() for c in cleaned}:
                cleaned.append(term)
        return cleaned

    @field_validator("work_modes", "platforms")
    @classmethod
    def _dedupe(cls, values: list[Any]) -> list[Any]:
        return list(dict.fromkeys(values))

    def to_model(self) -> SearchSettings:
        return SearchSettings(**self.model_dump())
