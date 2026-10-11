import io
import time
from typing import Any

import docx
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from job_tracker.clients.claude import LLMError
from job_tracker.services.resume_reader import read_paragraphs
from tests.support.api import READY_SETTINGS, discover_boards, run_to_completion
from tests.support.fake_job_boards import FakeJobBoards, greenhouse_job
from tests.support.fake_llm import FakeLLM
from tests.support.resumes import SUMMARY, add_ready_resume

BOARD = "globex"
TAILORED = "Backend engineer who builds payments APIs in Python and Go, with Kafka event pipelines at scale."
LONG = " ".join(["Backend engineer who ships reliable, well-tested payment systems for large card networks."] * 40)


def tailoring(summary: str = TAILORED, skills: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"summary": [summary], "skills": skills or [], "keywords": ["Python", "Go", "Kafka", "Payments"]}


def scored_job(client: TestClient, boards: FakeJobBoards, bold_labels: bool = False) -> int:
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


def test_applying_tailors_the_resume_and_opens_the_review(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = scored_job(client, boards, bold_labels=True)
    master = client.get("/api/resume").json()
    client.put("/api/resume/skills", json={"skills": [*master["skills"], "Kafka"]})
    llm.tailor(
        tailoring(
            skills=[
                {"line": 1, "skills": ["Go", "Rust", "python", "SQL", "TypeScript"]},
                {"line": 2, "skills": ["kafka", "Kubernetes", "PostgreSQL", "Docker", "Terraform", "AWS (Lambda, S3)"]},
            ]
        )
    )

    started = client.post(f"/api/jobs/{job_id}/apply")
    assert started.status_code == 202
    assert started.json()["status"] == "drafting"
    application = apply(client, job_id)

    assert application["status"] == "in_review", application
    resume = application["resume"]
    assert resume["summary"] == {"master": [SUMMARY], "tailored": [TAILORED]}
    assert resume["skills"]["master"] == [
        {"label": "Languages", "skills": ["Python", "Go", "TypeScript", "SQL"]},
        {"label": "Infrastructure", "skills": ["PostgreSQL", "Docker", "Kubernetes", "AWS (Lambda, S3)"]},
    ]
    assert resume["skills"]["tailored"] == [
        {"label": "Languages", "skills": ["Go", "Python", "SQL", "TypeScript"]},
        {"label": "Infrastructure", "skills": ["Kafka", "Kubernetes", "PostgreSQL", "Docker", "AWS (Lambda, S3)"]},
    ]
    assert (resume["page_count"], resume["master_page_count"]) == (1, 1)
    coverage = resume["coverage"]
    assert [(k["keyword"], k["before"], k["after"]) for k in coverage["keywords"]] == [
        ("Python", True, True),
        ("Go", True, True),
        ("Kafka", False, True),
        ("Payments", True, True),
    ]
    assert (coverage["before"], coverage["after"], coverage["total"]) == (3, 4, 4)

    pdf = client.get(f"/api/applications/{application['id']}/resume.pdf")
    assert pdf.headers["content-type"] == "application/pdf"
    text = pdf_text(pdf.content)
    assert page_count(pdf.content) == 1
    for expected in [TAILORED, "Languages: Go, Python, SQL, TypeScript", "Built ledger service number 1"]:
        assert expected in text
    for absent in ["Rust", "Terraform", SUMMARY]:
        assert absent not in text

    [call] = llm.tailoring_calls()
    assert call.model == "claude-sonnet-5-5"
    assert "never invent" in call.system.lower()
    assert application["cost_usd"] > 0
    [_, tailoring_costs] = client.get("/api/settings/costs").json()["by_kind"]
    assert (tailoring_costs["kind"], tailoring_costs["calls"]) == ("tailoring", 1)
    assert client.get(f"/api/jobs/{job_id}").json()["application"] == {"id": application["id"], "status": "in_review"}


def test_only_the_summary_and_skills_change_and_keep_their_formatting(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = scored_job(client, boards, bold_labels=True)
    llm.tailor(tailoring(skills=[{"line": 2, "skills": ["Docker", "PostgreSQL"]}]))
    application = apply(client, job_id)
    master_docx = client.get(f"/api/resume/versions/{application['resume']['master_version']}/original.docx")

    tailored_docx = client.get(f"/api/applications/{application['id']}/resume.docx")

    master = read_paragraphs("master.docx", master_docx.content)
    tailored = read_paragraphs("tailored.docx", tailored_docx.content)
    mapping = client.get("/api/resume").json()["mapping"]
    mapped = set(mapping["summary"] + mapping["skills"])
    assert len(tailored) == len(master)
    for before, after in zip(master, tailored, strict=True):
        if before.index in mapped:
            assert (after.style, after.font, after.size, after.alignment) == (
                before.style,
                before.font,
                before.size,
                before.alignment,
            )
        else:
            assert after == before
    assert [p.text for p in tailored if p.index in mapped] == [
        TAILORED,
        "Languages: Python, Go, TypeScript, SQL",
        "Infrastructure: Docker; PostgreSQL",
    ]
    infrastructure = next(p for p in docx.Document(io.BytesIO(tailored_docx.content)).paragraphs if "Docker" in p.text)
    assert [(run.text, run.bold) for run in infrastructure.runs if run.text] == [
        ("Infrastructure: ", True),
        ("Docker; PostgreSQL", None),
    ]


def test_a_summary_too_long_to_fit_is_shortened_and_retried(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = scored_job(client, boards)
    llm.tailor(tailoring(summary=LONG), tailoring())

    application = apply(client, job_id)

    assert application["status"] == "in_review", application
    assert len(llm.tailoring_calls()) == 2
    assert application["resume"]["page_count"] == 1
    pdf = client.get(f"/api/applications/{application['id']}/resume.pdf").content
    assert page_count(pdf) == 1
    assert TAILORED in pdf_text(pdf)
    [_, tailoring_costs] = client.get("/api/settings/costs").json()["by_kind"]
    assert tailoring_costs["calls"] == 2


def test_a_resume_that_still_does_not_fit_fails_with_a_clear_reason(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = scored_job(client, boards)
    llm.tailor(tailoring(summary=LONG), tailoring(summary=LONG))

    application = apply(client, job_id)

    assert application["status"] == "failed"
    assert application["error"] == (
        "The tailored resume ran to 2 pages, longer than your 1-page master, even after shortening it. "
        "Try again, or shorten your master resume."
    )
    assert application["resume"] is None
    assert client.get(f"/api/applications/{application['id']}/resume.pdf").status_code == 404


def test_cancelling_in_review_discards_the_application(client: TestClient, boards: FakeJobBoards) -> None:
    job_id = scored_job(client, boards)
    application = apply(client, job_id)

    cancelled = client.delete(f"/api/applications/{application['id']}")

    assert cancelled.status_code == 204
    assert client.get(f"/api/applications/{application['id']}").status_code == 404
    assert client.get(f"/api/applications/{application['id']}/resume.pdf").status_code == 404
    assert client.get(f"/api/jobs/{job_id}").json()["application"] is None
    again = apply(client, job_id)
    assert (again["status"], again["id"] != application["id"]) == ("in_review", True)


def test_applying_again_returns_the_open_application(client: TestClient, boards: FakeJobBoards, llm: FakeLLM) -> None:
    job_id = scored_job(client, boards)
    first = apply(client, job_id)

    second = client.post(f"/api/jobs/{job_id}/apply")

    assert (second.status_code, second.json()["id"]) == (200, first["id"])
    assert len(llm.tailoring_calls()) == 1
    assert client.post("/api/jobs/9999/apply").status_code == 404


def test_a_failed_tailoring_is_reported_and_can_be_retried(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = scored_job(client, boards)
    llm.tailor(LLMError("Claude's answer was cut off."))

    failed = apply(client, job_id)

    assert (failed["status"], failed["error"]) == ("failed", "Claude's answer was cut off.")
    retried = apply(client, job_id)
    assert retried["status"] == "in_review"
    assert client.get(f"/api/applications/{failed['id']}").status_code == 404


@pytest.mark.parametrize(
    "answer",
    [
        {"summary": [], "skills": [], "keywords": []},
        {"summary": ["   "], "skills": [], "keywords": []},
        {"summary": "One string", "skills": [], "keywords": []},
        {"summary": ["Fine."], "skills": [{"line": "one", "skills": []}], "keywords": []},
    ],
)
def test_tailoring_answers_that_dont_make_sense_fail_the_application(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM, answer: dict[str, Any]
) -> None:
    job_id = scored_job(client, boards)
    llm.tailor(answer)

    application = apply(client, job_id)

    assert application["status"] == "failed"
    assert application["error"] == "Claude's tailoring answer didn't have the expected fields."


def test_applying_is_refused_until_tailoring_is_set_up(client: TestClient, boards: FakeJobBoards) -> None:
    job_id = scored_job(client, boards)
    client.put("/api/settings/anthropic-api-key", json={"key": " "})

    refused = client.post(f"/api/jobs/{job_id}/apply")

    assert refused.status_code == 400
    assert refused.json()["detail"] == "Finish setting up first: add your Anthropic API key in Settings."
