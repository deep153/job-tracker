import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from job_tracker.app import create_app
from tests.fakes import FakeJobBoards, greenhouse_job_url

SEARCH_KEY = "brave-test-key-1234"

READY_SETTINGS: dict[str, Any] = {
    "roles": ["Backend Engineer"],
    "locations": ["New York, NY"],
    "work_modes": ["remote", "hybrid", "onsite"],
    "platforms": ["greenhouse"],
}


@pytest.fixture
def boards() -> FakeJobBoards:
    return FakeJobBoards()


@pytest.fixture
def client(tmp_path: Path, boards: FakeJobBoards) -> Iterator[TestClient]:
    app = create_app(db_path=tmp_path / "test.db", http=boards.client())
    with TestClient(app) as test_client:
        yield test_client


def configure_search(client: TestClient, settings: dict[str, Any] | None = None) -> None:
    response = client.put("/api/search-settings", json=settings or READY_SETTINGS)
    assert response.status_code == 200, response.text
    response = client.put("/api/settings/search-api-key", json={"key": SEARCH_KEY})
    assert response.status_code == 204, response.text


def discover_boards(client: TestClient, boards: FakeJobBoards, board_ids: list[str]) -> None:
    """Configure a ready search whose results point at these Greenhouse boards."""
    configure_search(client)
    boards.search_returns([greenhouse_job_url(board_id) for board_id in board_ids])


def wait_for_run(client: TestClient, run_id: int, until: Callable[[dict[str, Any]], bool] | None = None) -> dict[str, Any]:
    """Poll a run until `until` holds (default: the run is no longer running)."""
    check = until or (lambda run: run["status"] != "running")
    deadline = time.monotonic() + 5
    while True:
        run: dict[str, Any] = client.get(f"/api/runs/{run_id}").json()
        if check(run):
            return run
        if time.monotonic() > deadline:
            raise AssertionError(f"run never reached the expected state: {run}")
        time.sleep(0.02)


def run_to_completion(client: TestClient) -> dict[str, Any]:
    response = client.post("/api/runs")
    assert response.status_code == 202, response.text
    return wait_for_run(client, response.json()["id"])
