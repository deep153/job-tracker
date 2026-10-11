from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from job_tracker.clients.claude import LLMError
from tests.support.api import READY_SETTINGS, discover_boards, run_to_completion
from tests.support.fake_job_boards import FakeJobBoards, greenhouse_job
from tests.support.fake_llm import FakeLLM
from tests.support.resumes import add_ready_resume

BOARD = "globex"
NYC = "New York, NY"
SETTINGS = {**READY_SETTINGS, "roles": ["Engineer"], "locations": [NYC, "Chicago, IL"]}


def job(title: str, location: str = NYC, board: str = BOARD, days_ago: int = 1) -> dict[str, Any]:
    updated_at = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat(timespec="seconds")
    return greenhouse_job(board, title, location, "<p>Build payment APIs in Python.</p>", updated_at)


def run_with(client: TestClient, boards: FakeJobBoards, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    boards.serve_jobs(BOARD, jobs)
    discover_boards(client, boards, [BOARD], SETTINGS)
    return run_to_completion(client)


def titles(client: TestClient, path: str = "/api/jobs", **params: Any) -> list[str]:
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    return [j["title"] for j in response.json()]


def job_id(client: TestClient, title: str) -> int:
    listed = client.get("/api/jobs").json() + client.get("/api/jobs/below-threshold").json()
    return next(int(j["id"]) for j in listed if j["title"] == title)


def test_a_dismissed_job_does_not_reappear_after_another_run(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    backend, platform = job("Backend Engineer"), job("Platform Engineer")
    run_with(client, boards, [backend, platform])

    dismissed = client.post(f"/api/jobs/{job_id(client, 'Backend Engineer')}/dismiss")

    assert dismissed.status_code == 204
    assert titles(client) == ["Platform Engineer"]
    llm.calls.clear()
    boards.serve_jobs(BOARD, [{**backend, "content": "<p>Now with Kafka.</p>"}, platform])
    run_to_completion(client)
    assert titles(client) == ["Platform Engineer"]
    assert titles(client, "/api/jobs/below-threshold") == []
    assert llm.calls == []  # a dismissed job isn't scored again, even when it changes
    assert client.post("/api/jobs/9999/dismiss").status_code == 404


def test_a_matched_job_stays_listed_across_runs_until_it_closes(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    backend = job("Backend Engineer")
    run_with(client, boards, [backend])

    boards.serve_jobs(BOARD, [backend, job("Platform Engineer")])
    run_to_completion(client)
    assert sorted(titles(client)) == ["Backend Engineer", "Platform Engineer"]

    boards.serve_jobs(BOARD, [job("Data Engineer")])
    run_to_completion(client)
    assert titles(client) == ["Data Engineer"]


def test_rescoring_after_replacing_the_resume_scores_against_the_new_version(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    run_with(client, boards, [job("Backend Engineer"), job("Platform Engineer")])
    add_ready_resume(client, summary="Data engineer who builds streaming pipelines with Kafka and Spark.")
    llm.calls.clear()
    llm.score("Backend Engineer", 64, ["Your resume now leans toward data engineering."])
    backend = job_id(client, "Backend Engineer")

    rescored = client.post(f"/api/jobs/{backend}/rescore")

    assert rescored.status_code == 200, rescored.text
    assert (rescored.json()["score"]["score"], rescored.json()["score"]["resume_version"]) == (64, 2)
    [call] = llm.calls
    assert "Kafka and Spark" in call.prompt
    detail = client.get(f"/api/jobs/{backend}").json()
    assert detail["score"]["reasons"] == ["Your resume now leans toward data engineering."]
    assert titles(client) == ["Platform Engineer"]
    assert titles(client, "/api/jobs/below-threshold") == ["Backend Engineer"]
    [scoring] = client.get("/api/settings/costs").json()["by_kind"]
    assert scoring["calls"] == 3
    llm.calls.clear()
    run_to_completion(client)
    assert llm.scored_titles() == ["Platform Engineer"]  # the rescored job is up to date


def test_rescoring_explains_what_went_wrong(client: TestClient, boards: FakeJobBoards, llm: FakeLLM) -> None:
    run_with(client, boards, [job("Backend Engineer")])
    backend = job_id(client, "Backend Engineer")
    llm.fail(LLMError("Claude rejected your Anthropic API key. Check it in Settings.", fatal=True))

    failed = client.post(f"/api/jobs/{backend}/rescore")

    assert failed.status_code == 400
    assert failed.json()["detail"] == "Claude rejected your Anthropic API key. Check it in Settings."
    assert client.get(f"/api/jobs/{backend}").json()["score"]["score"] == 80  # the old score is kept
    client.put("/api/settings/anthropic-api-key", json={"key": " "})
    refused = client.post(f"/api/jobs/{backend}/rescore")
    assert refused.json()["detail"] == "Finish setting up first: add your Anthropic API key in Settings."
    assert client.post("/api/jobs/9999/rescore").status_code == 404


def test_job_detail_has_the_full_description_score_and_posting_link(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    llm.score("Backend Engineer", 91, ["You've built payment APIs."])
    run_with(client, boards, [job("Backend Engineer")])

    detail = client.get(f"/api/jobs/{job_id(client, 'Backend Engineer')}")

    assert detail.status_code == 200
    body = detail.json()
    assert body["description"] == "Build payment APIs in Python."
    assert (body["score"]["score"], body["score"]["reasons"]) == (91, ["You've built payment APIs."])
    assert (body["score"]["matched_keywords"], body["score"]["missing_keywords"]) == (["Python"], ["Kafka"])
    assert body["posting_url"].startswith(f"https://job-boards.greenhouse.io/{BOARD}/jobs/")
    assert body["dismissed"] is False
    assert client.get("/api/jobs/9999").status_code == 404


def test_jobs_can_be_filtered_by_company_location_and_posted_date_and_sorted(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    llm.score("Backend Engineer", 95)
    llm.score("Platform Engineer", 85)
    llm.score("Data Engineer", 75)
    llm.score("Mobile Engineer", 40)
    boards.serve_jobs(BOARD, [job("Backend Engineer", days_ago=20), job("Platform Engineer", "Chicago, IL")])
    boards.serve_jobs("initech", [job("Data Engineer", board="initech", days_ago=3), job("Mobile Engineer")])
    discover_boards(client, boards, [BOARD, "initech"], SETTINGS)
    run_to_completion(client)

    assert titles(client) == ["Backend Engineer", "Platform Engineer", "Data Engineer"]
    assert titles(client, sort="posted") == ["Platform Engineer", "Data Engineer", "Backend Engineer"]
    assert titles(client, company="initech") == ["Data Engineer"]
    assert titles(client, location="chicago") == ["Platform Engineer"]
    assert titles(client, posted_within_days=7) == ["Platform Engineer", "Data Engineer"]
    assert titles(client, company=BOARD, location="york") == ["Backend Engineer"]
    assert titles(client, "/api/jobs/below-threshold", company=BOARD) == []
    assert titles(client, "/api/jobs/below-threshold", company="initech") == ["Mobile Engineer"]
    assert client.get("/api/jobs", params={"sort": "salary"}).status_code == 422
    assert client.get("/api/jobs", params={"posted_within_days": 0}).status_code == 422
