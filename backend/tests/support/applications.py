import io
import time
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from pypdf import PdfReader

from tests.support.api import READY_SETTINGS, configure_search, run_to_completion
from tests.support.fake_forms import form_url
from tests.support.fake_job_boards import (
    FakeJobBoards,
    ashby_job,
    ashby_job_url,
    greenhouse_job,
    greenhouse_job_url,
    lever_job,
    lever_job_url,
)
from tests.support.resumes import add_ready_resume

BOARD = "globex"

_JOBS: dict[str, Callable[..., dict[str, Any]]] = {
    "greenhouse": greenhouse_job,
    "lever": lever_job,
    "ashby": ashby_job,
}
_BOARD_URLS: dict[str, Callable[[str], str]] = {
    "greenhouse": greenhouse_job_url,
    "lever": lever_job_url,
    "ashby": ashby_job_url,
}


def scored_job(
    client: TestClient,
    boards: FakeJobBoards,
    bold_labels: bool = False,
    form: str = "greenhouse.html",
    variants: dict[str, bool] | None = None,
    platform: str = "greenhouse",
    resume: bytes | None = None,
    bullets: bool = False,
) -> int:
    """A ready resume (the sample one, or `resume` with its proposed `bullets` marked if asked) and one scored job on
    `platform` to apply to, whose application form is the local fake page `form` (with `variants`, see
    `fake_forms`); returns the job's id."""
    add_ready_resume(client, bold_labels=bold_labels, data=resume, bullets=bullets)
    url = form_url(form, **(variants or {}))
    job = _JOBS[platform](BOARD, "Backend Engineer", "New York, NY", "<p>Payments in Go.</p>", url=url)
    boards.serve_jobs(BOARD, [job], platform)
    configure_search(client, {**READY_SETTINGS, "roles": ["Engineer"], "platforms": [platform]})
    boards.search_returns([_BOARD_URLS[platform](BOARD)])
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
