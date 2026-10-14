from fastapi.testclient import TestClient

from tests.api.test_answers import WHY
from tests.api.test_submitting import reviewed, submit
from tests.support import fake_forms
from tests.support.fake_job_boards import FakeJobBoards
from tests.support.fake_llm import DEFAULT_COVER_LETTER


def dashboard_ids(client: TestClient) -> list[int]:
    jobs = client.get("/api/jobs").json() + client.get("/api/jobs/below-threshold").json()
    return [job["id"] for job in jobs]


def test_a_submitted_application_is_listed_with_what_was_sent_and_leaves_the_dashboard(
    client: TestClient, boards: FakeJobBoards
) -> None:
    application = reviewed(client, boards)
    job_id = application["job"]["id"]
    assert dashboard_ids(client) == [job_id]

    submitted = submit(client, application["id"])

    [listed] = client.get("/api/applications").json()
    assert (listed["id"], listed["status"], listed["date"]) == (
        application["id"],
        "submitted",
        submitted["submitted_at"],
    )
    assert (listed["job"]["company"], listed["job"]["title"], listed["job"]["score"]["score"]) == (
        "globex",
        "Backend Engineer",
        80,
    )
    assert dashboard_ids(client) == []
    detail = client.get(f"/api/applications/{application['id']}").json()
    [sent] = fake_forms.submissions()
    assert client.get(detail["resume"]["pdf_url"]).content == sent.files["resume"][1]
    assert client.get(detail["cover_letter"]["pdf_url"]).content == sent.files["cover_letter"][1]
    assert detail["cover_letter"]["text"] == DEFAULT_COVER_LETTER
    sources = {q["key"]: (q["answer"], q["source"]) for q in detail["questions"]}
    assert sources["first_name"] == ("Jordan", "bank")
    assert sources[WHY] == ("I want to build payment systems at Globex's scale.", "you")


def test_i_can_update_the_status_by_hand_only_after_submitting(client: TestClient, boards: FakeJobBoards) -> None:
    application = reviewed(client, boards)
    url = f"/api/applications/{application['id']}/status"

    too_early = client.put(url, json={"status": "interviewing"})
    submit(client, application["id"])
    interviewing = client.put(url, json={"status": "interviewing"})

    assert (too_early.status_code, too_early.json()["detail"]) == (
        409,
        "You can update the status once the application has been submitted.",
    )
    assert (interviewing.status_code, interviewing.json()["status"]) == (200, "interviewing")
    assert [a["status"] for a in client.get("/api/applications").json()] == ["interviewing"]
    for status in ("offer", "rejected", "withdrawn"):
        assert client.put(url, json={"status": status}).json()["status"] == status
    assert client.put(url, json={"status": "drafting"}).status_code == 422
    assert client.post(f"/api/applications/{application['id']}/approve").status_code == 409
    assert dashboard_ids(client) == []


def test_an_application_i_finished_by_hand_can_be_marked_submitted(client: TestClient, boards: FakeJobBoards) -> None:
    application = reviewed(client, boards, captcha=True)
    handed_over = submit(client, application["id"])
    assert handed_over["status"] == "needs_manual"
    assert dashboard_ids(client) == [application["job"]["id"]]

    marked = client.put(f"/api/applications/{application['id']}/status", json={"status": "submitted"})

    assert (marked.json()["status"], marked.json()["error"]) == ("submitted", None)
    assert marked.json()["submitted_at"] is not None
    assert dashboard_ids(client) == []
