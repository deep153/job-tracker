from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from job_tracker.app import create_app
from job_tracker.clients.claude import LLMError
from tests.support.applications import apply, page_count, pdf_text, scored_job
from tests.support.fake_job_boards import FakeJobBoards
from tests.support.fake_llm import DEFAULT_TAILORED_SUMMARY, FakeLLM

EDITED = "Payments engineer focused on Kafka streaming services in Python."
LONG = " ".join(["Backend engineer who ships reliable, well-tested payment systems for large card networks."] * 40)
SKILLS = [["SQL", "python"], ["Docker", "PostgreSQL", "Kubernetes"]]


def edit(client: TestClient, application_id: int, summary: list[str], skills: list[list[str]]) -> Any:
    return client.put(f"/api/applications/{application_id}/resume", json={"summary": summary, "skills": skills})


def test_editing_the_summary_and_skills_regenerates_the_pdf(client: TestClient, boards: FakeJobBoards) -> None:
    application = apply(client, scored_job(client, boards))

    response = edit(client, application["id"], [EDITED], SKILLS)

    assert response.status_code == 200, response.text
    resume = response.json()["resume"]
    assert resume["summary"]["tailored"] == [EDITED]
    assert resume["skills"]["tailored"] == [
        {"label": "Languages", "skills": ["SQL", "Python"]},
        {"label": "Infrastructure", "skills": ["Docker", "PostgreSQL", "Kubernetes"]},
    ]
    assert (resume["page_count"], resume["master_page_count"], resume["fits"]) == (1, 1, True)
    coverage = resume["coverage"]
    assert [(k["keyword"], k["before"], k["after"]) for k in coverage["keywords"]] == [
        ("Python", True, True),
        ("Kafka", False, True),
    ]
    pdf = client.get(resume["pdf_url"]).content
    assert page_count(pdf) == 1
    text = pdf_text(pdf)
    assert EDITED in text
    assert "Languages: SQL, Python" in text
    assert "Infrastructure: Docker; PostgreSQL; Kubernetes" in text
    assert DEFAULT_TAILORED_SUMMARY not in text


@pytest.mark.parametrize(
    ("summary", "skills", "message"),
    [
        (
            [EDITED],
            [["SQL", "Rust"], ["Docker"]],
            "“Rust” isn't in your master skills list. Add it on the Resume page first, or remove it.",
        ),
        ([EDITED], [["SQL"]], "Your resume has 2 skills lines; send the skills for each of them."),
        ([EDITED], [["SQL"], []], "Keep at least one skill on each skills line."),
        (["  "], SKILLS, "Write a Summary before regenerating."),
    ],
)
def test_edits_that_break_the_rules_are_rejected(
    client: TestClient, boards: FakeJobBoards, summary: list[str], skills: list[list[str]], message: str
) -> None:
    application = apply(client, scored_job(client, boards))

    response = edit(client, application["id"], summary, skills)

    assert response.status_code == 422
    assert response.json()["detail"] == message
    assert client.get(f"/api/applications/{application['id']}").json() == application


def test_edits_that_make_the_resume_longer_are_flagged(client: TestClient, boards: FakeJobBoards) -> None:
    application = apply(client, scored_job(client, boards))

    too_long = edit(client, application["id"], [LONG], SKILLS).json()["resume"]

    assert (too_long["page_count"], too_long["master_page_count"], too_long["fits"]) == (2, 1, False)
    assert page_count(client.get(too_long["pdf_url"]).content) == 2
    fixed = edit(client, application["id"], [EDITED], SKILLS).json()["resume"]
    assert (fixed["page_count"], fixed["fits"]) == (1, True)


def test_a_saved_draft_returns_the_same_review_bundle_when_reopened(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM, tmp_path: Path
) -> None:
    job_id = scored_job(client, boards)
    application = apply(client, job_id)
    saved = edit(client, application["id"], [EDITED], SKILLS).json()
    pdf = client.get(saved["resume"]["pdf_url"]).content

    with TestClient(create_app(db_path=tmp_path / "test.db", http=boards.client(), llm=llm)) as reopened:
        assert reopened.get(f"/api/applications/{application['id']}").json() == saved
        assert reopened.get(saved["resume"]["pdf_url"]).content == pdf
        assert reopened.get(f"/api/jobs/{job_id}").json()["application"] == {
            "id": application["id"],
            "status": "in_review",
        }


def test_only_an_application_in_review_can_be_edited(client: TestClient, boards: FakeJobBoards, llm: FakeLLM) -> None:
    llm.tailor(LLMError("Claude's answer was cut off."))
    failed = apply(client, scored_job(client, boards))

    response = edit(client, failed["id"], [EDITED], SKILLS)

    assert response.status_code == 409
    assert response.json()["detail"] == "Only an application in review can be edited."
    assert edit(client, 9999, [EDITED], SKILLS).status_code == 404
