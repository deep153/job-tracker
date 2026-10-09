import json
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from job_tracker.clients.claude import ClaudeLLM, LLMError
from job_tracker.services.pricing import estimate_cost
from tests.conftest import ANTHROPIC_KEY, READY_SETTINGS, SEARCH_KEY, discover_boards, run_to_completion
from tests.fakes import FakeJobBoards, FakeLLM, greenhouse_job
from tests.resumes import SKILL_LINES, SUMMARY, add_ready_resume, mapping_for, sample_resume, upload

BOARD = "globex"
NYC = "New York, NY"


def job(title: str, content: str = "<p>Build payment APIs in Python.</p>") -> dict[str, Any]:
    return greenhouse_job(BOARD, title, NYC, content)


def run_with(client: TestClient, boards: FakeJobBoards, jobs: list[dict[str, Any]], **settings: Any) -> dict[str, Any]:
    boards.serve_jobs(BOARD, jobs)
    discover_boards(client, boards, [BOARD], {**READY_SETTINGS, "roles": ["Engineer"], **settings})
    return run_to_completion(client)


def matches(client: TestClient) -> list[tuple[str, int]]:
    return [(j["title"], j["score"]["score"]) for j in client.get("/api/jobs").json()]


def below(client: TestClient) -> list[tuple[str, int | None]]:
    return [(j["title"], j["score"] and j["score"]["score"]) for j in client.get("/api/jobs/below-threshold").json()]


def test_dashboard_shows_only_jobs_at_or_above_the_threshold_sorted_by_score(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    llm.score("Backend Engineer", 92, ["You've built payment systems in Python.", "The role is in New York."])
    llm.score("Platform Engineer", 70)
    llm.score("Data Engineer", 69)
    llm.score("Mobile Engineer", 40)

    run = run_with(
        client,
        boards,
        [job("Data Engineer"), job("Platform Engineer"), job("Mobile Engineer"), job("Backend Engineer")],
    )

    assert matches(client) == [("Backend Engineer", 92), ("Platform Engineer", 70)]
    assert below(client) == [("Data Engineer", 69), ("Mobile Engineer", 40)]
    best = client.get("/api/jobs").json()[0]["score"]
    assert best["reasons"] == ["You've built payment systems in Python.", "The role is in New York."]
    assert best["matched_keywords"] == ["Python"]
    assert best["missing_keywords"] == ["Kafka"]
    assert best["model"] == "claude-haiku-5-5"
    assert best["resume_version"] == 1
    assert (run["stage"], run["scoring_total"], run["scored_jobs"], run["matched_jobs"]) == ("scoring", 4, 4, 2)
    assert run["errors"] == []


def test_listing_jobs_and_a_second_run_over_unchanged_jobs_make_no_new_llm_calls(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    run_with(client, boards, [job("Backend Engineer"), job("Platform Engineer")])
    assert llm.scored_titles() == ["Backend Engineer", "Platform Engineer"]
    llm.calls.clear()

    client.get("/api/jobs")
    client.get("/api/jobs/below-threshold")
    second = run_to_completion(client)

    assert llm.calls == []
    assert (second["scoring_total"], second["scored_jobs"], second["ai_cost_usd"]) == (0, 0, 0)
    assert len(matches(client)) == 2


def test_only_jobs_that_pass_the_hard_filters_are_scored(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    run_with(
        client,
        boards,
        [job("Backend Engineer"), job("Frontend Engineer"), job("Backend Engineering Manager")],
        roles=["Backend Engineer", "Backend Engineering"],
        excluded_keywords=["Manager"],
    )

    assert llm.scored_titles() == ["Backend Engineer"]


def test_a_changed_posting_is_scored_again(client: TestClient, boards: FakeJobBoards, llm: FakeLLM) -> None:
    posting = job("Backend Engineer")
    run_with(client, boards, [posting, job("Platform Engineer")])
    llm.calls.clear()

    llm.score("Backend Engineer", 55)
    boards.serve_jobs(BOARD, [{**posting, "content": "<p>Now mostly Kafka streaming.</p>"}, job("Platform Engineer")])
    run = run_to_completion(client)

    assert llm.scored_titles() == ["Backend Engineer"]
    assert run["scored_jobs"] == 1
    assert below(client) == [("Backend Engineer", 55)]


def test_a_new_resume_version_gets_its_own_scores(client: TestClient, boards: FakeJobBoards, llm: FakeLLM) -> None:
    run_with(client, boards, [job("Backend Engineer")])
    llm.calls.clear()

    add_ready_resume(client, summary="Data engineer who builds streaming pipelines with Kafka and Spark.")
    assert client.get("/api/jobs").json()[0]["score"]["resume_version"] == 1  # kept until rescored
    run_to_completion(client)

    assert "Kafka and Spark" in llm.calls[0].prompt
    assert client.get("/api/jobs").json()[0]["score"]["resume_version"] == 2


def test_threshold_is_editable_and_applies_without_new_llm_calls(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    assert client.get("/api/search-settings").json()["min_score"] == 70
    llm.score("Backend Engineer", 85)
    llm.score("Data Engineer", 60)
    run_with(client, boards, [job("Backend Engineer"), job("Data Engineer")])
    llm.calls.clear()

    saved = client.put("/api/search-settings", json={**READY_SETTINGS, "roles": ["Engineer"], "min_score": 55})

    assert saved.json()["min_score"] == 55
    assert matches(client) == [("Backend Engineer", 85), ("Data Engineer", 60)]
    assert llm.calls == []
    for bad in (-1, 101):
        response = client.put("/api/search-settings", json={**READY_SETTINGS, "min_score": bad})
        assert response.status_code == 422


def test_run_is_refused_without_an_anthropic_key_or_a_mapped_resume(client: TestClient, llm: FakeLLM) -> None:
    client.put("/api/search-settings", json=READY_SETTINGS)
    client.put("/api/settings/search-api-key", json={"key": SEARCH_KEY})

    refused = client.post("/api/runs")
    assert refused.status_code == 400
    assert refused.json()["detail"] == "Finish setting up first: add your Anthropic API key in Settings."

    client.put("/api/settings/anthropic-api-key", json={"key": ANTHROPIC_KEY})
    refused = client.post("/api/runs")
    assert refused.json()["detail"] == "Finish setting up first: upload your resume and mark its Summary and Skills."

    resume = upload(client, sample_resume()).json()
    assert client.get("/api/search-settings").json()["missing"] == ["Mark your resume's Summary and Skills."]
    assert client.post("/api/runs").status_code == 400

    client.put("/api/resume/mapping", json=mapping_for(resume))
    assert client.get("/api/search-settings").json()["ready"] is True
    assert client.get("/api/runs").json() == []
    assert llm.calls == []


def test_anthropic_key_is_stored_but_never_sent_back_in_full(client: TestClient) -> None:
    assert client.get("/api/settings").json()["anthropic_api_key"] == {"set": False, "last4": None}

    saved = client.put("/api/settings/anthropic-api-key", json={"key": f"  {ANTHROPIC_KEY} "})

    assert ANTHROPIC_KEY not in saved.text
    fetched = client.get("/api/settings")
    assert ANTHROPIC_KEY not in fetched.text
    assert fetched.json()["anthropic_api_key"] == {"set": True, "last4": ANTHROPIC_KEY[-4:]}
    assert ANTHROPIC_KEY not in client.get("/api/search-settings").text

    client.put("/api/settings/anthropic-api-key", json={"key": " "})
    assert client.get("/api/settings").json()["anthropic_api_key"]["set"] is False


def test_models_are_editable_and_the_scoring_model_is_used(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    defaults = client.get("/api/settings").json()
    assert (defaults["scoring_model"], defaults["tailoring_model"]) == ("claude-haiku-5-5", "claude-sonnet-5-5")
    assert "claude-opus-5-5" in defaults["suggested_models"]

    saved = client.put(
        "/api/settings/models", json={"scoring_model": " claude-sonnet-5-5 ", "tailoring_model": "claude-opus-5-5"}
    )
    assert (saved.json()["scoring_model"], saved.json()["tailoring_model"]) == ("claude-sonnet-5-5", "claude-opus-5-5")
    run_with(client, boards, [job("Backend Engineer")])

    assert [call.model for call in llm.calls] == ["claude-sonnet-5-5"]
    assert client.get("/api/jobs").json()[0]["score"]["model"] == "claude-sonnet-5-5"
    for bad in ("", "claude haiku", "x" * 101, "../etc"):
        response = client.put("/api/settings/models", json={"scoring_model": bad, "tailoring_model": "claude-opus-5-5"})
        assert response.status_code == 422, bad


def test_each_run_records_its_estimated_ai_cost_and_settings_sum_them_up(
    client: TestClient, boards: FakeJobBoards
) -> None:
    per_call = estimate_cost("claude-haiku-5-5", FakeLLM.INPUT_TOKENS, FakeLLM.OUTPUT_TOKENS)
    assert per_call == pytest.approx((1000 * 0.10 + 200 * 0.50) / 1_000_000)

    first = run_with(client, boards, [job("Backend Engineer"), job("Platform Engineer")])
    boards.serve_jobs(BOARD, [job("Backend Engineer"), job("Platform Engineer"), job("Data Engineer")])
    second = run_to_completion(client)

    assert first["ai_cost_usd"] == pytest.approx(2 * per_call)
    assert second["ai_cost_usd"] == pytest.approx(per_call)
    costs = client.get("/api/settings/costs").json()
    assert costs["total_usd"] == pytest.approx(3 * per_call)
    [scoring] = costs["by_kind"]
    assert (scoring["kind"], scoring["calls"], scoring["input_tokens"]) == ("scoring", 3, 3000)
    assert [(r["id"], r["scored_jobs"]) for r in costs["recent_runs"]] == [(second["id"], 1), (first["id"], 2)]


def test_prices_follow_the_model() -> None:
    assert estimate_cost("claude-sonnet-5-5", 1_000_000, 1_000_000) == pytest.approx(12)
    assert estimate_cost("claude-haiku-4-5-20251001", 1_000_000, 0) == pytest.approx(1)
    assert estimate_cost("claude-haiku-5-5", 200_000, 0) == pytest.approx(0.10)  # long prompts cost more
    assert estimate_cost("claude-opus-9", 1_000_000, 0) == pytest.approx(4)  # unknown: priced as its line


def test_a_fatal_llm_error_stops_scoring_and_the_next_run_catches_up(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    llm.fail(LLMError("Claude rejected your Anthropic API key. Check it in Settings.", fatal=True))

    run = run_with(client, boards, [job("Backend Engineer"), job("Platform Engineer"), job("Data Engineer")])

    assert run["status"] == "finished"
    assert run["scored_jobs"] == 0
    assert run["errors"] == [
        {
            "kind": "scoring",
            "platform": None,
            "board_id": None,
            "message": "Scoring stopped: Claude rejected your Anthropic API key. Check it in Settings.",
        }
    ]
    assert len(llm.calls) <= 4  # calls already in flight, not one per job
    assert [score for _, score in below(client)] == [None, None, None]

    llm.fail(None)
    assert run_to_completion(client)["scored_jobs"] == 3


def test_invalid_or_failed_answers_are_reported_and_retried_next_run(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    llm.answer("Backend Engineer", {"score": 150, "reasons": [], "matched_keywords": [], "missing_keywords": []})
    llm.answer("Data Engineer", LLMError("Claude's answer was cut off."))

    run = run_with(client, boards, [job("Backend Engineer"), job("Platform Engineer"), job("Data Engineer")])

    assert run["scored_jobs"] == 1
    [error] = run["errors"]
    assert error["kind"] == "scoring"
    assert error["message"].startswith("Couldn't score 2 jobs; they'll be tried again next run.")
    assert matches(client) == [("Platform Engineer", 80)]

    llm.score("Backend Engineer", 75)
    llm.score("Data Engineer", 90)
    llm.calls.clear()
    run_to_completion(client)
    assert llm.scored_titles() == ["Backend Engineer", "Data Engineer"]
    assert matches(client) == [("Data Engineer", 90), ("Platform Engineer", 80), ("Backend Engineer", 75)]


def test_answers_are_tidied(client: TestClient, boards: FakeJobBoards, llm: FakeLLM) -> None:
    llm.answer(
        "Backend Engineer",
        {
            "score": 88.0,
            "reasons": [f"Reason {n}." for n in range(8)],
            "matched_keywords": ["Python", " python ", "Go", ""],
            "missing_keywords": ["Kafka"],
        },
    )

    run_with(client, boards, [job("Backend Engineer")])

    [scored] = client.get("/api/jobs").json()
    assert scored["score"]["score"] == 88
    assert scored["score"]["reasons"] == [f"Reason {n}." for n in range(5)]
    assert scored["score"]["matched_keywords"] == ["Python", "Go"]


def test_the_prompt_has_my_resume_preferences_and_the_job(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    run_with(
        client,
        boards,
        [job("Backend Engineer", "<p>You'll build ledgers in Go.</p><p>$150,000 - $190,000 USD</p>")],
        seniority="senior",
        years_experience=6,
        needs_sponsorship=True,
    )

    [call] = llm.calls
    assert call.api_key == ANTHROPIC_KEY
    assert call.schema["required"] == ["score", "reasons", "matched_keywords", "missing_keywords"]
    for expected in [SUMMARY, *SKILL_LINES, "Skills: Python, Go, TypeScript", "Roles I want: Engineer"]:
        assert expected in call.prompt
    for expected in ["My level: senior", "Years of experience: 6", "I need visa sponsorship: yes"]:
        assert expected in call.prompt
    for expected in [
        "Title: Backend Engineer",
        f"Company: {BOARD}",
        "You'll build ledgers in Go.",
        "150,000 - 190,000",
    ]:
        assert expected in call.prompt


def claude(handler: Any) -> ClaudeLLM:
    return ClaudeLLM(http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))


def generate(llm: ClaudeLLM) -> Any:
    return llm.generate(
        api_key=ANTHROPIC_KEY,
        model="claude-haiku-5-5",
        system="Be brief.",
        prompt="Score this.",
        schema={"type": "object"},
        max_tokens=100,
    )


def test_claude_is_asked_for_structured_output_and_its_answer_parsed() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": "claude-haiku-5-5-20260901",
                "content": [{"type": "text", "text": '{"score": 77}'}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1234, "output_tokens": 56},
            },
        )

    response = generate(claude(handler))

    assert (response.data, response.model) == ({"score": 77}, "claude-haiku-5-5-20260901")
    assert (response.input_tokens, response.output_tokens) == (1234, 56)
    [request] = requests
    body = json.loads(request.content)
    assert request.headers["x-api-key"] == ANTHROPIC_KEY
    assert body["output_config"] == {"format": {"type": "json_schema", "schema": {"type": "object"}}}
    assert (body["model"], body["system"], body["max_tokens"]) == ("claude-haiku-5-5", "Be brief.", 100)


@pytest.mark.parametrize(
    ("status", "error", "message", "fatal"),
    [
        (401, "authentication_error", "Claude rejected your Anthropic API key. Check it in Settings.", True),
        (
            404,
            "not_found_error",
            "Claude has no model called “claude-haiku-5-5”. Check the model names in Settings.",
            True,
        ),
        (400, "invalid_request_error", "Your Anthropic account is out of credit.", True),
    ],
)
def test_claude_errors_are_explained(status: int, error: str, message: str, fatal: bool) -> None:
    detail = "Your credit balance is too low." if status == 400 else "nope"
    body = {"type": "error", "error": {"type": error, "message": detail}}

    with pytest.raises(LLMError) as raised:
        generate(claude(lambda _: httpx2.Response(status, json=body)))

    assert (raised.value.message, raised.value.fatal) == (message, fatal)
