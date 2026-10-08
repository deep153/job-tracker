import threading
from pathlib import Path

import httpx

FIXTURES = Path(__file__).parent / "fixtures"

SEARCH_HOST = "api.search.brave.com"

_PLATFORM_BY_HOST = {
    "boards-api.greenhouse.io": "greenhouse",
}


def _board_id(platform: str, request: httpx.Request) -> str | None:
    parts = request.url.path.strip("/").split("/")
    if platform == "greenhouse" and len(parts) == 4 and parts[:2] == ["v1", "boards"] and parts[3] == "jobs":
        return parts[2]
    return None


def greenhouse_job_url(board_id: str, job_id: int = 4000000001) -> str:
    return f"https://job-boards.greenhouse.io/{board_id}/jobs/{job_id}"


class FakeJobBoards:
    """Serves recorded job-board fixtures and scripted web search results instead of the network.

    By default a board is served from `fixtures/<platform>/<board_id>.json`, and boards
    without a fixture answer 404 like the real APIs do.
    """

    def __init__(self) -> None:
        self._fixtures: dict[tuple[str, str], str] = {}
        self._failures: dict[tuple[str, str], int] = {}
        self._holds: dict[tuple[str, str], threading.Event] = {}
        self._search_results: list[str] = []
        self._search_failure: int | None = None
        self.search_queries: list[str] = []
        self.search_keys: list[str] = []
        self.fetched_boards: list[tuple[str, str]] = []

    def serve(self, platform: str, board_id: str, fixture: str) -> None:
        """Serve `fixtures/<platform>/<fixture>.json` for this board from now on."""
        self._fixtures[(platform, board_id)] = fixture

    def fail(self, platform: str, board_id: str, status: int = 500) -> None:
        self._failures[(platform, board_id)] = status

    def hold(self, platform: str, board_id: str) -> threading.Event:
        """Block requests for this board until the returned event is set."""
        event = threading.Event()
        self._holds[(platform, board_id)] = event
        return event

    def search_returns(self, urls: list[str]) -> None:
        """Every web search returns these result URLs, in order."""
        self._search_results = urls

    def fail_search(self, status: int) -> None:
        self._search_failure = status

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self._handle))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == SEARCH_HOST:
            return self._search(request)
        platform = _PLATFORM_BY_HOST.get(request.url.host)
        if platform is None:
            return httpx.Response(599, text=f"unexpected host {request.url.host}")
        board_id = _board_id(platform, request)
        if board_id is None:
            return httpx.Response(404)
        key = (platform, board_id)
        self.fetched_boards.append(key)
        if key in self._holds:
            self._holds[key].wait(timeout=10)
        if key in self._failures:
            return httpx.Response(self._failures[key], text="board unavailable")
        fixture = FIXTURES / platform / f"{self._fixtures.get(key, board_id)}.json"
        if not fixture.exists():
            return httpx.Response(404, json={"status": 404, "error": "Job board not found"})
        return httpx.Response(200, content=fixture.read_bytes(), headers={"content-type": "application/json"})

    def _search(self, request: httpx.Request) -> httpx.Response:
        if request.url.path != "/res/v1/web/search":
            return httpx.Response(404)
        self.search_queries.append(request.url.params["q"])
        self.search_keys.append(request.headers.get("X-Subscription-Token", ""))
        if self._search_failure is not None:
            return httpx.Response(self._search_failure, json={"error": "search failed"})
        results = [{"title": "Job", "url": url, "description": ""} for url in self._search_results]
        return httpx.Response(200, json={"type": "search", "web": {"type": "search", "results": results}})
