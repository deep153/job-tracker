from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from job_tracker.app import create_app
from job_tracker.companies import Company
from tests.fakes import fake_job_boards

MakeClient = Callable[[list[Company]], TestClient]


@pytest.fixture
def make_client(tmp_path: Path) -> Iterator[MakeClient]:
    clients: list[TestClient] = []

    def make(starter_companies: list[Company]) -> TestClient:
        app = create_app(
            db_path=tmp_path / "test.db",
            http=fake_job_boards(),
            starter_companies=starter_companies,
        )
        client = TestClient(app)
        clients.append(client)
        return client

    yield make
    for client in clients:
        client.close()
