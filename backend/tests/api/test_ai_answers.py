from typing import Any

from fastapi.testclient import TestClient

from tests.api.test_answers import BANK, WHY, add_entries
from tests.support import fake_forms
from tests.support.applications import apply, scored_job
from tests.support.fake_job_boards import FakeJobBoards
from tests.support.fake_llm import FakeLLM
from tests.support.resumes import SUMMARY

WHY_LABEL = "Why do you want to work at Globex?"
DRAFT = "Globex's payments platform is the kind of system I've built for six years in Python and Go."


def by_key(application: dict[str, Any]) -> dict[str, tuple[Any, Any, Any]]:
    return {q["key"]: (q["answer"], q["source"], q["needs_input"]) for q in application["questions"]}


def test_an_open_ended_question_gets_an_ai_draft_from_my_resume_and_the_job(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    add_entries(client, BANK)
    llm.draft(WHY_LABEL, DRAFT)

    application = apply(client, scored_job(client, boards))

    assert by_key(application)[WHY] == (DRAFT, "ai", False)
    [call] = llm.answering_calls()
    assert call.questions == [WHY_LABEL]
    assert call.model == "claude-sonnet-5-5"
    assert SUMMARY in call.prompt and "Payments in Go." in call.prompt
    assert "Never invent" in call.system
    costs = {kind["kind"]: kind["calls"] for kind in client.get("/api/settings/costs").json()["by_kind"]}
    assert costs["answers"] == 1


def test_an_answer_saved_from_review_answers_the_next_application(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    add_entries(client, BANK)
    job_id = scored_job(client, boards)
    application = apply(client, job_id)
    client.put(
        f"/api/applications/{application['id']}/answers",
        json={"answers": {WHY: "I want to build payment systems at Globex's scale.", "gender": "Female"}},
    )

    saved = client.post(f"/api/applications/{application['id']}/answers/save-to-bank", json={"key": WHY})
    client.post(f"/api/applications/{application['id']}/answers/save-to-bank", json={"key": "gender"})

    assert saved.status_code == 200, saved.text
    assert by_key(saved.json())[WHY] == ("I want to build payment systems at Globex's scale.", "bank", False)
    bank = {(e["question"], e["answer"], e["category"]) for e in client.get("/api/answer-bank").json()}
    assert (WHY_LABEL, "I want to build payment systems at Globex's scale.", "other") in bank
    assert ("Gender", "Female", "eeo") in bank
    assert len(bank) == len(BANK) + 1
    assert client.delete(f"/api/applications/{application['id']}").status_code == 204
    llm.calls.clear()

    again = apply(client, job_id)

    assert by_key(again)[WHY] == ("I want to build payment systems at Globex's scale.", "bank", False)
    assert by_key(again)["gender"] == ("Female", "bank", False)
    assert llm.answering_calls() == []


def test_a_question_the_ai_cannot_answer_still_needs_input(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    add_entries(client, BANK)

    application = apply(client, scored_job(client, boards))

    assert by_key(application)[WHY] == (None, "none", True)
    assert [call.questions for call in llm.answering_calls()] == [[WHY_LABEL]]


def test_eeo_questions_are_never_sent_to_the_ai_and_need_my_saved_choice(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    add_entries(client, [entry for entry in BANK if entry[2] != "eeo"])
    fake_forms.add_to_forms(
        '<label for="question_4005">How would you describe your gender identity?</label>'
        '<input id="question_4005" name="question_4005" type="text" />'
    )
    llm.draft("How would you describe your gender identity?", "Made up by the AI")

    application = apply(client, scored_job(client, boards))

    answers = by_key(application)
    assert answers["gender"] == (None, "none", True)
    assert answers["veteran_status"] == (None, "none", True)
    assert answers["question_4005"] == (None, "none", True)
    assert [call.questions for call in llm.answering_calls()] == [[WHY_LABEL]]
    assert application["approval_problem"] == (
        "Answer these questions first: “Why do you want to work at Globex?”, “Gender”, “Veteran Status”, "
        "“How would you describe your gender identity?”."
    )
