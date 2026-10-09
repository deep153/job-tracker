from typing import Protocol

import httpx


class SearchError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class WebSearch(Protocol):
    def search(self, query: str, api_key: str) -> list[str]:
        """Return result URLs for a query. Raises SearchError if the search can't be made."""
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
