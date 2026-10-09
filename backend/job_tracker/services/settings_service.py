from collections.abc import Collection

from job_tracker.database import Database
from job_tracker.models.ai import DEFAULT_SCORING_MODEL, DEFAULT_TAILORING_MODEL, AiSettings
from job_tracker.models.platform import ALL_PLATFORMS, PLATFORM_NAMES, Platform
from job_tracker.models.search_settings import SearchSettings
from job_tracker.services.discovery import supported_for_discovery
from job_tracker.services.errors import InvalidRequestError
from job_tracker.services.filtering import refilter_jobs

_SEARCH_API_KEY = "search_api_key"
_ANTHROPIC_API_KEY = "anthropic_api_key"
_SCORING_MODEL = "scoring_model"
_TAILORING_MODEL = "tailoring_model"


class SettingsService:
    """My search settings, API keys and AI models. Everything is kept in the local database only."""

    def __init__(self, db: Database, fetchable_platforms: Collection[Platform]) -> None:
        self._db = db
        self._fetchable = fetchable_platforms

    def platform_supported(self, platform: Platform) -> bool:
        """Whether jobs on this platform can be both discovered and fetched."""
        return platform in self._fetchable and supported_for_discovery(platform)

    def platforms(self) -> list[tuple[Platform, str, bool]]:
        """Every platform as (id, name, supported)."""
        return [(p, PLATFORM_NAMES[p], self.platform_supported(p)) for p in ALL_PLATFORMS]

    def search(self) -> SearchSettings:
        with self._db.transaction() as uow:
            return uow.settings.search_settings()

    def save_search(self, settings: SearchSettings) -> SearchSettings:
        """Save the settings and re-apply the filters to stored jobs; nothing is fetched or scored."""
        unsupported = [PLATFORM_NAMES[p] for p in settings.platforms if not self.platform_supported(p)]
        if unsupported:
            raise InvalidRequestError(f"{', '.join(unsupported)} isn't supported yet.")
        with self._db.transaction() as uow:
            uow.settings.save_search_settings(settings)
            refilter_jobs(uow)
        return settings

    def search_api_key(self) -> str | None:
        return self._get(_SEARCH_API_KEY)

    def set_search_api_key(self, key: str) -> None:
        self._set(_SEARCH_API_KEY, key.strip())

    def ai(self) -> AiSettings:
        return AiSettings(
            anthropic_api_key=self._get(_ANTHROPIC_API_KEY),
            scoring_model=self._get(_SCORING_MODEL) or DEFAULT_SCORING_MODEL,
            tailoring_model=self._get(_TAILORING_MODEL) or DEFAULT_TAILORING_MODEL,
        )

    def set_anthropic_api_key(self, key: str) -> AiSettings:
        self._set(_ANTHROPIC_API_KEY, key.strip())
        return self.ai()

    def set_models(self, scoring: str, tailoring: str) -> AiSettings:
        with self._db.transaction() as uow:
            uow.settings.set(_SCORING_MODEL, scoring)
            uow.settings.set(_TAILORING_MODEL, tailoring)
        return self.ai()

    def _get(self, key: str) -> str | None:
        """A setting, or None when it's unset or blank."""
        with self._db.transaction() as uow:
            return uow.settings.get(key) or None

    def _set(self, key: str, value: str) -> None:
        with self._db.transaction() as uow:
            uow.settings.set(key, value)
