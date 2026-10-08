import re
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import parse_qs, urlparse

import httpx

from job_tracker.companies import Platform
from job_tracker.search_settings import SearchSettings

MAX_SEARCH_QUERIES_PER_RUN = 20

_SITE_FILTERS: dict[Platform, str] = {
    "greenhouse": "(site:job-boards.greenhouse.io OR site:boards.greenhouse.io)",
    "lever": "site:jobs.lever.co",
    "ashby": "site:jobs.ashbyhq.com",
}

# Hosts whose first path segment is the company board ID. EU Lever boards (jobs.eu.lever.co) are left
# out: they're served by a separate API.
_BOARD_HOSTS: dict[Platform, re.Pattern[str]] = {
    "greenhouse": re.compile(r"^(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io$"),
    "lever": re.compile(r"^jobs\.lever\.co$"),
    "ashby": re.compile(r"^jobs\.ashbyhq\.com$"),
}
_BOARD_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class SearchError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class WebSearch(Protocol):
    def search(self, query: str, api_key: str) -> list[str]:
        """Return result URLs for a query."""
        ...


class BraveSearch:
    """Brave Search web API (https://api.search.brave.com)."""

    URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def search(self, query: str, api_key: str) -> list[str]:
        try:
            response = self._http.get(
                self.URL,
                params={"q": query, "count": 20},
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            )
        except httpx.TransportError:
            raise SearchError("Couldn't reach the search API.") from None
        status = response.status_code
        if status in (401, 403):
            raise SearchError(f"The search API rejected your key (HTTP {status}). Check the key in Search settings.")
        if status == 429:
            raise SearchError("The search API rate limit was reached (HTTP 429). Try again later.")
        if status >= 400:
            raise SearchError(f"The search API returned HTTP {status}.")
        results = response.json().get("web", {}).get("results", [])
        return [result["url"] for result in results if "url" in result]


def supported_for_discovery(platform: Platform) -> bool:
    return platform in _SITE_FILTERS


def build_queries(settings: SearchSettings) -> list[tuple[Platform, str]]:
    places = [*settings.locations, *(["remote"] if "remote" in settings.work_modes else [])]
    # Platforms take turns, so the per-run cap doesn't use up every search on the first platform.
    return [
        (platform, f'{_SITE_FILTERS[platform]} "{role}" "{place}"')
        for role in settings.roles
        for place in places
        for platform in settings.platforms
        if platform in _SITE_FILTERS
    ]


def extract_board_id(platform: Platform, url: str) -> str | None:
    """The company board ID a job-board URL belongs to, or None if it isn't a board URL.

    Board IDs are lower-cased: Greenhouse and Ashby ignore case, and Lever's API only knows the lower-case form.
    """
    parsed = urlparse(url)
    if not _BOARD_HOSTS[platform].match(parsed.hostname or ""):
        return None
    segments = [segment for segment in parsed.path.split("/") if segment]
    if not segments:
        return None
    board = segments[0]
    if platform == "greenhouse" and board == "embed":
        board = parse_qs(parsed.query).get("for", [""])[0]
    return board.lower() if _BOARD_ID.match(board) else None


@dataclass
class DiscoveredBoard:
    platform: Platform
    board_id: str
    query: str


@dataclass
class DiscoveryResult:
    boards: list[DiscoveredBoard] = field(default_factory=list)
    queries_made: int = 0
    capped: bool = False
    error: str | None = None


def discover(search: WebSearch, api_key: str, settings: SearchSettings) -> DiscoveryResult:
    queries = build_queries(settings)
    result = DiscoveryResult(capped=len(queries) > MAX_SEARCH_QUERIES_PER_RUN)
    seen: set[tuple[Platform, str]] = set()
    for platform, query in queries[:MAX_SEARCH_QUERIES_PER_RUN]:
        result.queries_made += 1
        try:
            urls = search.search(query, api_key)
        except SearchError as error:
            # Every later query would fail the same way (bad key, rate limit), so stop here.
            result.error = error.message
            break
        for url in urls:
            board_id = extract_board_id(platform, url)
            if board_id and (platform, board_id) not in seen:
                seen.add((platform, board_id))
                result.boards.append(DiscoveredBoard(platform, board_id, query))
    return result
