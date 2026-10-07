import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from job_tracker.app import create_app
from job_tracker.companies import Company
from tests.fakes import FakeJobBoards

MakeClient = Callable[[list[Company]], TestClient]


@pytest.fixture
def boards() -> FakeJobBoards:
    return FakeJobBoards()


@pytest.fixture
def make_client(tmp_path: Path, boards: FakeJobBoards) -> Iterator[MakeClient]:
    clients: list[TestClient] = []

    def make(companies: list[Company]) -> TestClient:
        app = create_app(
            db_path=tmp_path / "test.db",
            http=boards.client(),
            initial_companies=companies,
        )
        client = TestClient(app)
        clients.append(client)
        return client

    yield make
    for client in clients:
        client.close()


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
