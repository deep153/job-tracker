from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from job_tracker.app import create_app
from tests.support import fake_forms
from tests.support.fake_job_boards import FakeJobBoards
from tests.support.fake_llm import FakeLLM


@pytest.fixture
def boards() -> FakeJobBoards:
    return FakeJobBoards()


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture(autouse=True)
def forms() -> None:
    fake_forms.reset()


@pytest.fixture
def client(tmp_path: Path, boards: FakeJobBoards, llm: FakeLLM) -> Iterator[TestClient]:
    app = create_app(db_path=tmp_path / "test.db", http=boards.client(), llm=llm, visible_browser=False)
    with TestClient(app) as test_client:
        yield test_client
