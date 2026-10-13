from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.support.applications import apply, scored_job
from tests.support.fake_forms import form_url
from tests.support.fake_job_boards import FakeJobBoards

WHY = "question_4004"
BANK = [
    ("First Name", "Jordan", "personal"),
    ("Last Name", "Rivera", "personal"),
    ("Email", "jordan@example.com", "personal"),
    ("Country", "United States", "personal"),
    ("LinkedIn", "https://linkedin.com/in/jrivera", "links"),
    ("Are you authorized to work in the US?", "Yes", "work_authorization"),
    ("Will you require visa sponsorship?", "No", "sponsorship"),
    ("Gender", "Decline to self-identify", "eeo"),
]


def add_entries(client: TestClient, entries: list[tuple[str, str, str]]) -> None:
    for question, answer, category in entries:
        response = client.post("/api/answer-bank", json={"question": question, "answer": answer, "category": category})
        assert response.status_code == 201, response.text


def questions(application: dict[str, Any]) -> list[tuple[Any, ...]]:
    return [
        (q["key"], q["label"], q["kind"], q["required"], q["answer"], q["source"], q["needs_input"])
        for q in application["questions"]
    ]


def test_answer_bank_entries_can_be_listed_added_updated_and_deleted(client: TestClient) -> None:
    assert client.get("/api/answer-bank").json() == []

    created = client.post(
        "/api/answer-bank",
        json={"question": " Are you authorized to work in the US? ", "answer": "Yes", "category": "work_authorization"},
    )
    assert created.status_code == 201
    entry = created.json()
    assert (entry["question"], entry["answer"], entry["category"], entry["last_used_at"]) == (
        "Are you authorized to work in the US?",
        "Yes",
        "work_authorization",
        None,
    )

    updated = client.put(
        f"/api/answer-bank/{entry['id']}",
        json={"question": "Are you authorized to work in the US?", "answer": "No", "category": "work_authorization"},
    )
    assert updated.json()["answer"] == "No"
    assert [e["answer"] for e in client.get("/api/answer-bank").json()] == ["No"]

    assert client.delete(f"/api/answer-bank/{entry['id']}").status_code == 204
    assert client.get("/api/answer-bank").json() == []
    assert client.delete(f"/api/answer-bank/{entry['id']}").status_code == 404


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"question": " ", "answer": "Yes", "category": "other"}, "Write the question."),
        ({"question": "Start date", "answer": "", "category": "start_date"}, "Write the answer."),
        ({"question": "Gender", "answer": "Female", "category": "eeo"}, "You already have an answer for “Gender”."),
    ],
)
def test_invalid_answer_bank_entries_are_rejected(client: TestClient, body: dict[str, str], message: str) -> None:
    add_entries(client, [("Gender", "Decline to self-identify", "eeo")])

    response = client.post("/api/answer-bank", json=body)

    assert response.status_code == 422
    assert response.json()["detail"] == message
    assert client.post("/api/answer-bank", json={**body, "category": "astrology"}).status_code == 422


def test_applying_reads_the_greenhouse_form_and_answers_from_the_bank(
    client: TestClient, boards: FakeJobBoards
) -> None:
    add_entries(client, BANK)

    application = apply(client, scored_job(client, boards))

    assert application["status"] == "in_review", application
    assert questions(application) == [
        ("first_name", "First Name", "text", True, "Jordan", "bank", False),
        ("last_name", "Last Name", "text", True, "Rivera", "bank", False),
        ("email", "Email", "text", True, "jordan@example.com", "bank", False),
        ("country", "Country", "select", True, "United States +1", "bank", False),
        ("phone", "Phone", "text", False, None, "none", False),
        ("resume", "Resume/CV", "file", True, "Tailored resume (PDF)", "resume", False),
        ("cover_letter", "Cover Letter", "file", False, None, "none", False),
        ("question_4001", "LinkedIn Profile", "text", False, "https://linkedin.com/in/jrivera", "bank", False),
        (
            "question_4002",
            "Are you legally authorized to work in the United States?",
            "select",
            True,
            "Yes",
            "bank",
            False,
        ),
        (
            "question_4003",
            "Will you now or in the future require sponsorship for employment visa status (e.g. H-1B)?",
            "select",
            True,
            "No",
            "bank",
            False,
        ),
        (WHY, "Why do you want to work at Globex?", "textarea", True, None, "none", True),
        ("gender", "Gender", "select", False, "Decline To Self Identify", "bank", False),
        ("veteran_status", "Veteran Status", "radio", False, None, "none", False),
    ]
    by_key = {q["key"]: q for q in application["questions"]}
    assert by_key["gender"]["options"] == ["Male", "Female", "Decline To Self Identify"]
    assert by_key["veteran_status"]["options"] == [
        "I am not a protected veteran",
        "I identify as one or more of the classifications of protected veteran",
        "I don't wish to answer",
    ]
    assert (application["form_error"], application["can_approve"]) == (None, False)
    used = {e["question"]: e["last_used_at"] for e in client.get("/api/answer-bank").json()}
    assert all(used.values())


def test_bank_entries_only_answer_the_questions_they_match(client: TestClient, boards: FakeJobBoards) -> None:
    add_entries(client, [("Last Name", "Rivera", "personal"), ("Personal website", "https://jr.dev", "links")])

    application = apply(client, scored_job(client, boards))

    by_key = {q["key"]: (q["answer"], q["source"]) for q in application["questions"]}
    assert by_key["first_name"] == (None, "none")
    assert by_key["last_name"] == ("Rivera", "bank")
    assert by_key["question_4001"] == (None, "none")


def test_approve_is_refused_while_a_required_question_needs_input(client: TestClient, boards: FakeJobBoards) -> None:
    add_entries(client, BANK)
    application = apply(client, scored_job(client, boards))

    refused = client.post(f"/api/applications/{application['id']}/approve")

    assert refused.status_code == 409
    assert refused.json()["detail"] == "Answer the required questions first: “Why do you want to work at Globex?”."
    answered = client.put(
        f"/api/applications/{application['id']}/answers",
        json={"answers": {WHY: "I want to build payment systems at Globex's scale.", "phone": "555-0100"}},
    ).json()
    by_key = {q["key"]: (q["answer"], q["source"], q["needs_input"]) for q in answered["questions"]}
    assert by_key[WHY] == ("I want to build payment systems at Globex's scale.", "you", False)
    assert by_key["phone"] == ("555-0100", "you", False)
    assert answered["can_approve"] is True
    approved = client.post(f"/api/applications/{application['id']}/approve")
    assert approved.status_code == 200, approved.text


@pytest.mark.parametrize(
    ("answers", "message"),
    [
        ({"gender": "Prefer not to say"}, "Pick one of the options for “Gender”."),
        ({"question_9999": "Hi"}, "This form has no question “question_9999”."),
        ({"resume": "me.pdf"}, "“Resume/CV” is filled with your tailored resume."),
    ],
)
def test_invalid_answer_edits_are_rejected(
    client: TestClient, boards: FakeJobBoards, answers: dict[str, str], message: str
) -> None:
    application = apply(client, scored_job(client, boards))

    response = client.put(f"/api/applications/{application['id']}/answers", json={"answers": answers})

    assert response.status_code == 422
    assert response.json()["detail"] == message


def test_answers_can_pick_options_case_insensitively_and_be_cleared(client: TestClient, boards: FakeJobBoards) -> None:
    add_entries(client, BANK)
    application = apply(client, scored_job(client, boards))

    edited = client.put(
        f"/api/applications/{application['id']}/answers", json={"answers": {"gender": "female", "first_name": " "}}
    ).json()

    by_key = {q["key"]: (q["answer"], q["source"], q["needs_input"]) for q in edited["questions"]}
    assert by_key["gender"] == ("Female", "you", False)
    assert by_key["first_name"] == (None, "none", True)


def test_a_page_without_an_application_form_fails_the_application(client: TestClient, boards: FakeJobBoards) -> None:
    application = apply(client, scored_job(client, boards, form="no-form.html"))

    assert application["status"] == "failed"
    assert application["error"] == (
        f"Couldn't find an application form at {form_url('no-form.html')}. The job may have closed."
    )
