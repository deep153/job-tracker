import io
import time
from typing import Any

from fastapi.testclient import TestClient
from pypdf import PdfReader

from tests.support.api import READY_SETTINGS, discover_boards, run_to_completion
from tests.support.fake_job_boards import FakeJobBoards, greenhouse_job
from tests.support.resumes import add_ready_resume

BOARD = "globex"


def scored_job(client: TestClient, boards: FakeJobBoards, bold_labels: bool = False) -> int:
    """A ready resume and one scored job to apply to; returns the job's id."""
    add_ready_resume(client, bold_labels=bold_labels)
    boards.serve_jobs(BOARD, [greenhouse_job(BOARD, "Backend Engineer", "New York, NY", "<p>Payments in Go.</p>")])
    discover_boards(client, boards, [BOARD], {**READY_SETTINGS, "roles": ["Engineer"]})
    run_to_completion(client)
    [job] = client.get("/api/jobs").json()
    return int(job["id"])


def apply(client: TestClient, job_id: int) -> dict[str, Any]:
    """Apply to the job and wait for tailoring to finish."""
    response = client.post(f"/api/jobs/{job_id}/apply")
    assert response.status_code in (200, 202), response.text
    deadline = time.monotonic() + 60
    while True:
        application: dict[str, Any] = client.get(f"/api/applications/{response.json()['id']}").json()
        if application["status"] != "drafting":
            return application
        assert time.monotonic() < deadline, "tailoring never finished"
        time.sleep(0.05)


def pdf_text(pdf: bytes) -> str:
    return " ".join(" ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages).split())


def page_count(pdf: bytes) -> int:
    return len(PdfReader(io.BytesIO(pdf)).pages)
