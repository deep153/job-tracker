import io
from typing import Any

import docx
from fastapi.testclient import TestClient

from job_tracker.services.resume_reader import read_paragraphs
from tests.support.applications import apply, page_count, pdf_text, scored_job
from tests.support.fake_job_boards import FakeJobBoards
from tests.support.fake_llm import FakeLLM
from tests.support.resumes import BULLETS, full_resume

TAILORED = "Backend engineer who builds payments APIs in Python and Go."
LONG = " ".join(["Backend engineer who ships reliable, well-tested payment systems for large card networks."] * 40)
PAYMENTS = "Cut checkout latency by 60% for 2M+ users by moving the ledger service to Go."
REWORDED = "Cut payment API latency by 60% for 2M+ users by moving the ledger service to Go."
API = "Built an internal Python API used by 14 teams to reconcile card settlements daily."


def tailoring(*bullets: tuple[int, str], summary: str = TAILORED) -> dict[str, Any]:
    return {
        "summary": [summary],
        "skills": [],
        "keywords": [],
        "gaps": [],
        "bullets": [{"bullet": number, "text": text} for number, text in bullets],
    }


def bullets_job(client: TestClient, boards: FakeJobBoards) -> int:
    """A job scored against the full resume with its proposed bullets marked; the scorer's keywords for it are
    Python, PostgreSQL and Kafka."""
    return scored_job(client, boards, resume=full_resume(), bullets=True)


def by_label(application: dict[str, Any]) -> dict[str | None, dict[str, Any]]:
    return {bullet["label"]: bullet for bullet in application["resume"]["bullets"]}


def test_reworded_bullets_keep_their_bold_label_and_nothing_else_changes(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = bullets_job(client, boards)
    llm.tailor(tailoring((1, REWORDED), (4, API)))

    application = apply(client, job_id)

    assert application["status"] == "in_review", application
    bullets = application["resume"]["bullets"]
    assert [(b["label"], b["master"], b["tailored"], b["reverted"]) for b in bullets] == [
        ("Payments", PAYMENTS, REWORDED, None),
        ("Reliability", BULLETS[1].split(": ", 1)[1], BULLETS[1].split(": ", 1)[1], None),
        ("Migration", BULLETS[2].split(": ", 1)[1], BULLETS[2].split(": ", 1)[1], None),
        (None, BULLETS[3], API, None),
    ]

    master_docx = client.get(f"/api/resume/versions/{application['resume']['master_version']}/original.docx").content
    tailored_docx = client.get(f"/api/applications/{application['id']}/resume.docx").content
    mapping = client.get("/api/resume").json()["mapping"]
    changed = {bullets[0]["index"], bullets[3]["index"]}
    master, tailored = read_paragraphs("m.docx", master_docx), read_paragraphs("t.docx", tailored_docx)
    for before, after in zip(master, tailored, strict=True):
        if before.index not in {*mapping["summary"], *mapping["skills"], *changed}:
            assert after == before
    assert tailored[bullets[0]["index"]].text == f"Payments: {REWORDED}"
    assert tailored[bullets[3]["index"]].text == API
    payments = next(p for p in docx.Document(io.BytesIO(tailored_docx)).paragraphs if p.text.startswith("Payments"))
    assert [(run.text, run.bold) for run in payments.runs if run.text] == [("Payments: ", True), (REWORDED, None)]

    pdf = client.get(f"/api/applications/{application['id']}/resume.pdf").content
    assert f"Payments: {REWORDED}" in pdf_text(pdf)
    assert page_count(pdf) == application["resume"]["master_page_count"] == application["resume"]["page_count"]


def test_a_reworded_bullet_that_changes_a_number_is_reverted(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = bullets_job(client, boards)
    changed = REWORDED.replace("60%", "70%")
    llm.tailor(tailoring((1, changed)))

    application = apply(client, job_id)

    payments = by_label(application)["Payments"]
    assert payments["tailored"] == PAYMENTS
    assert payments["reverted"] == {"text": changed, "reason": "It changes 60% to 70%."}
    text = pdf_text(client.get(f"/api/applications/{application['id']}/resume.pdf").content)
    assert f"Payments: {PAYMENTS}" in text
    assert "70%" not in text


def test_a_reworded_bullet_that_adds_an_unlisted_skill_is_reverted(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = bullets_job(client, boards)
    with_kafka = "Cut checkout latency by 60% for 2M+ users by moving the ledger to Go and Kafka."
    keeps_grafana = "Led on-call for 9+ services and cut incidents by 35% with Grafana and Python alerts."
    llm.tailor(tailoring((1, with_kafka), (2, keeps_grafana)))

    application = apply(client, job_id)

    payments, reliability = by_label(application)["Payments"], by_label(application)["Reliability"]
    assert payments["tailored"] == PAYMENTS
    assert payments["reverted"] == {
        "text": with_kafka,
        "reason": "It adds “Kafka”, which isn't in this bullet or your master skills list.",
    }
    assert (reliability["tailored"], reliability["reverted"]) == (keeps_grafana, None)


def test_a_reworded_bullet_that_grew_too_much_is_reverted(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = bullets_job(client, boards)
    longer = f"{PAYMENTS[:-1]}, which made checkout feel instant on mobile."
    llm.tailor(tailoring((1, longer)))

    payments = by_label(apply(client, job_id))["Payments"]

    assert payments["tailored"] == PAYMENTS
    assert payments["reverted"]["text"] == longer
    assert payments["reverted"]["reason"] == "It's 57% longer than the original; a rewrite can grow by 15% at most."


def test_shortening_and_retrying_covers_the_bullets_too(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = bullets_job(client, boards)
    llm.tailor(tailoring((1, REWORDED), summary=LONG), tailoring((4, API)))

    application = apply(client, job_id)

    assert application["status"] == "in_review", application
    assert len(llm.tailoring_calls()) == 2
    assert [b["tailored"] for b in application["resume"]["bullets"]][::3] == [PAYMENTS, API]
    pdf = client.get(f"/api/applications/{application['id']}/resume.pdf").content
    assert page_count(pdf) == 1
    assert API in pdf_text(pdf)
