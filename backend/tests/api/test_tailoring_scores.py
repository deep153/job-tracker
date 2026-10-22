from typing import Any

import pytest
from fastapi.testclient import TestClient

from job_tracker.clients.claude import LLMError
from tests.support.applications import apply, scored_job
from tests.support.fake_job_boards import FakeJobBoards
from tests.support.fake_llm import FakeLLM

TAILORED = "Backend engineer who builds payments APIs in Python and Go, with Kafka event pipelines at scale."


def tailoring(summary: str = TAILORED, gaps: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    return {"summary": [summary], "skills": [], "keywords": ["Payments"], "gaps": gaps or [], **extra}


def costs_by_kind(client: TestClient) -> dict[str, int]:
    return {k["kind"]: k["calls"] for k in client.get("/api/settings/costs").json()["by_kind"]}


def test_tailoring_targets_the_scorers_keywords_and_the_result_is_rescored(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    job_id = scored_job(client, boards)  # scored 80, matching Python and PostgreSQL and missing Kafka
    llm.tailor(tailoring(gaps=["Kafka", "Terraform"]))
    llm.score_resume(TAILORED, 88)

    application = apply(client, job_id)

    assert application["status"] == "in_review", application
    resume = application["resume"]
    assert resume["fit_score"] == {"before": 80, "after": 88}
    assert resume["gaps"] == ["Kafka"]  # only the job's keywords can be gaps
    coverage = resume["coverage"]
    assert [(k["keyword"], k["before"], k["after"]) for k in coverage["keywords"]] == [
        ("Python", True, True),
        ("PostgreSQL", True, True),
        ("Kafka", False, True),
    ]
    assert (coverage["before"], coverage["after"], coverage["total"]) == (2, 3, 3)

    assert costs_by_kind(client)["rescoring"] == 1
    assert application["cost_usd"] > 0
    assert client.get(f"/api/jobs/{job_id}").json()["score"]["score"] == 80  # the job's own score is untouched


def test_an_unscored_job_is_tailored_to_keywords_the_tailor_picks(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    llm.answer("Backend Engineer", LLMError("Claude's answer was cut off."))
    job_id = scored_job(client, boards)
    llm.tailor(tailoring(gaps=["kafka"], keywords=["Payments", "Kafka"]))
    llm.score_resume(TAILORED, 75)

    resume = apply(client, job_id)["resume"]

    assert resume["fit_score"] == {"before": None, "after": 75}
    assert [k["keyword"] for k in resume["coverage"]["keywords"]] == ["Payments", "Kafka"]
    assert resume["gaps"] == ["Kafka"]


def test_a_failed_rescore_leaves_the_after_score_empty(client: TestClient, boards: FakeJobBoards, llm: FakeLLM) -> None:
    job_id = scored_job(client, boards)
    llm.tailor(tailoring())
    llm.answer("Backend Engineer", LLMError("Claude's answer was cut off."))

    application = apply(client, job_id)

    assert application["status"] == "in_review", application
    assert application["resume"]["fit_score"] == {"before": 80, "after": None}


def test_the_rescore_cost_is_added_to_the_application(client: TestClient, boards: FakeJobBoards, llm: FakeLLM) -> None:
    job_id = scored_job(client, boards)
    llm.tailor(tailoring())

    application = apply(client, job_id)

    usage = {k["kind"]: k["cost_usd"] for k in client.get("/api/settings/costs").json()["by_kind"]}
    assert usage["rescoring"] > 0
    # Everything but the run's scoring was for this application.
    assert application["cost_usd"] == pytest.approx(sum(cost for kind, cost in usage.items() if kind != "scoring"))


def test_coverage_ignores_case_punctuation_plurals_and_parentheticals(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    llm.answer(
        "Backend Engineer",
        {
            "score": 70,
            "reasons": ["Good fit."],
            "matched_keywords": ["python"],
            "missing_keywords": ["Observability", "API", "CI/CD"],
        },
    )
    job_id = scored_job(client, boards)
    llm.tailor(tailoring("Builds payment APIs and ci-cd pipelines, with Observability (Grafana, Kibana) dashboards."))

    coverage = apply(client, job_id)["resume"]["coverage"]

    assert [(k["keyword"], k["before"], k["after"]) for k in coverage["keywords"]] == [
        ("python", True, True),
        ("Observability", False, True),
        ("API", False, True),
        ("CI/CD", False, True),
    ]
