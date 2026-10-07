from pathlib import Path

import httpx

FIXTURES = Path(__file__).parent / "fixtures"


def _greenhouse(request: httpx.Request) -> httpx.Response:
    # /v1/boards/{board_id}/jobs
    parts = request.url.path.strip("/").split("/")
    if len(parts) != 4 or parts[:2] != ["v1", "boards"] or parts[3] != "jobs":
        return httpx.Response(404)
    fixture = FIXTURES / "greenhouse" / f"{parts[2]}.json"
    if not fixture.exists():
        return httpx.Response(404, json={"status": 404, "error": "Job board not found"})
    return httpx.Response(200, content=fixture.read_bytes(), headers={"content-type": "application/json"})


_HOSTS = {
    "boards-api.greenhouse.io": _greenhouse,
}


def fake_job_boards() -> httpx.Client:
    """An HTTP client that serves recorded job-board fixtures instead of the network."""

    def handler(request: httpx.Request) -> httpx.Response:
        route = _HOSTS.get(request.url.host)
        if route is None:
            return httpx.Response(599, text=f"unexpected host {request.url.host}")
        return route(request)

    return httpx.Client(transport=httpx.MockTransport(handler))
