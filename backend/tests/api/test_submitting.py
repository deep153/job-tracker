import time
from typing import Any

from fastapi.testclient import TestClient

from tests.api.test_answers import BANK, WHY, add_entries
from tests.support import fake_forms
from tests.support.applications import apply, scored_job
from tests.support.fake_job_boards import FakeJobBoards


def reviewed(client: TestClient, boards: FakeJobBoards, **variants: bool) -> dict[str, Any]:
    """An application in review with every required question answered."""
    add_entries(client, BANK)
    application = apply(client, scored_job(client, boards, form="greenhouse.html", variants=variants))
    response = client.put(
        f"/api/applications/{application['id']}/answers",
        json={"answers": {WHY: "I want to build payment systems at Globex's scale.", "gender": "Female"}},
    )
    assert response.json()["can_approve"], response.text
    return dict(response.json())


def submit(client: TestClient, application_id: int) -> dict[str, Any]:
    """Approve the application and wait for the submission to finish."""
    response = client.post(f"/api/applications/{application_id}/approve")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "submitting"
    deadline = time.monotonic() + 60
    while True:
        application: dict[str, Any] = client.get(f"/api/applications/{application_id}").json()
        if application["status"] != "submitting":
            return application
        assert time.monotonic() < deadline, "submitting never finished"
        time.sleep(0.05)


def test_approving_submits_the_reviewed_answers_and_the_tailored_pdf(client: TestClient, boards: FakeJobBoards) -> None:
    application = reviewed(client, boards)

    submitted = submit(client, application["id"])

    assert (submitted["status"], submitted["error"]) == ("submitted", None)
    assert submitted["submitted_at"] is not None
    [sent] = fake_forms.submissions()
    assert {name: value for name, value in sent.fields.items() if value} == {
        "first_name": "Jordan",
        "last_name": "Rivera",
        "email": "jordan@example.com",
        "country": "United States +1",
        "question_4001": "https://linkedin.com/in/jrivera",
        "question_4002": "1",
        "question_4003": "No",
        WHY: "I want to build payment systems at Globex's scale.",
        "gender": "Female",
        "fingerprint": "abc123",
    }
    pdf = client.get(f"/api/applications/{application['id']}/resume.pdf").content
    assert list(sent.files) == ["resume"]
    filename, content = sent.files["resume"]
    assert (filename.endswith(".pdf"), content) == (True, pdf)


def test_a_job_can_only_be_submitted_to_once(client: TestClient, boards: FakeJobBoards) -> None:
    application = reviewed(client, boards)
    submit(client, application["id"])

    again = client.post(f"/api/applications/{application['id']}/approve")
    reapply = client.post(f"/api/jobs/{application['job']['id']}/apply")

    assert (again.status_code, again.json()["detail"]) == (409, "This application has already been sent.")
    assert (reapply.status_code, reapply.json()["detail"]) == (409, "You've already applied to this job.")
    assert len(fake_forms.submissions()) == 1
