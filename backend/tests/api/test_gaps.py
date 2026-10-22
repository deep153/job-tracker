from typing import Any

from fastapi.testclient import TestClient

from tests.support.applications import apply, pdf_text, scored_job
from tests.support.fake_job_boards import FakeJobBoards
from tests.support.fake_llm import FakeLLM

TAILORED = "Backend engineer who builds payments APIs in Python and Go."
LONG = " ".join(["Backend engineer who ships reliable, well-tested payment systems for large card networks."] * 40)


def tailoring(gaps: list[str], skills: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"summary": [TAILORED], "skills": skills or [], "bullets": [], "keywords": [], "gaps": gaps}


def add_gap(client: TestClient, application_id: int, keyword: str, line: int) -> Any:
    return client.post(f"/api/applications/{application_id}/gaps", json={"keyword": keyword, "line": line})


def test_adding_a_gap_puts_it_on_the_chosen_skills_line_and_in_my_master_list(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = scored_job(client, boards)  # the scorer's keywords: Python, PostgreSQL and Kafka
    llm.tailor(tailoring(["Kafka"]))
    application = apply(client, job_id)
    assert application["resume"]["gaps"] == ["Kafka"]
    llm.score_resume("Kafka", 86)

    response = add_gap(client, application["id"], "kafka", 1)

    assert response.status_code == 200, response.text
    resume = response.json()["resume"]
    assert resume["gaps"] == []
    assert resume["skills"]["tailored"][1] == {
        "label": "Infrastructure",
        "skills": ["PostgreSQL", "Docker", "Kubernetes", "AWS (Lambda, S3)", "Kafka"],
    }
    assert [(k["keyword"], k["after"]) for k in resume["coverage"]["keywords"]][-1] == ("Kafka", True)
    assert resume["fit_score"]["after"] == 86
    assert "Infrastructure: PostgreSQL; Docker; Kubernetes; AWS (Lambda, S3); Kafka" in pdf_text(
        client.get(resume["pdf_url"]).content
    )
    assert client.get("/api/resume").json()["skills"][-1] == "Kafka"
    assert len(llm.tailoring_calls()) == 1


def test_a_later_application_can_use_a_skill_added_from_a_gap(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = scored_job(client, boards)
    llm.tailor(tailoring(["Kafka"]))
    first = apply(client, job_id)
    add_gap(client, first["id"], "Kafka", 1)
    assert client.delete(f"/api/applications/{first['id']}").status_code == 204

    llm.tailor(tailoring([], skills=[{"line": 2, "skills": ["Kafka", "PostgreSQL", "Docker"]}]))
    second = apply(client, job_id)

    assert second["resume"]["skills"]["tailored"][1]["skills"] == ["Kafka", "PostgreSQL", "Docker"]
    assert "Infrastructure: Kafka; PostgreSQL; Docker" in pdf_text(client.get(second["resume"]["pdf_url"]).content)


def test_a_gap_that_would_lengthen_the_resume_is_refused_and_nothing_changes(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = scored_job(client, boards)
    llm.tailor(tailoring(["Kafka"]))
    application = apply(client, job_id)
    resume = application["resume"]
    too_long = client.put(
        f"/api/applications/{application['id']}/resume",
        json={"summary": [LONG], "skills": [line["skills"] for line in resume["skills"]["tailored"]]},
    ).json()
    assert too_long["resume"]["fits"] is False
    master_skills = client.get("/api/resume").json()["skills"]

    response = add_gap(client, application["id"], "Kafka", 0)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Adding “Kafka” would make your resume run to 2 pages, longer than your 1-page master, so it wasn't "
        "added. Shorten the resume first, or try another Skills line."
    )
    assert client.get(f"/api/applications/{application['id']}").json() == too_long
    assert client.get("/api/resume").json()["skills"] == master_skills


def test_only_a_gap_of_this_resume_can_be_added_to_a_real_skills_line(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = scored_job(client, boards)
    llm.tailor(tailoring(["Kafka"]))
    application = apply(client, job_id)

    for keyword, line, message in [
        ("Terraform", 0, "“Terraform” isn't one of this resume's gaps."),
        ("Kafka", 5, "Your resume has no Skills line 6."),
    ]:
        response = add_gap(client, application["id"], keyword, line)
        assert response.status_code == 422
        assert response.json()["detail"] == message
