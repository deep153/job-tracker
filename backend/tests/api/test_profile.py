from typing import Any

from fastapi.testclient import TestClient

from job_tracker.clients.claude import LLMError
from tests.support.api import READY_SETTINGS, configure_search
from tests.support.applications import apply, scored_job
from tests.support.fake_forms import add_to_forms
from tests.support.fake_job_boards import FakeJobBoards
from tests.support.fake_llm import FakeLLM
from tests.support.resumes import EMAIL, LINKEDIN_URL, PHONE, add_ready_resume, full_resume

AUTHORIZED = "Are you legally authorized to work in the United States?"
SPONSORSHIP = "Will you now or in the future require sponsorship for employment visa status?"
EDUCATION = ["School", "Degree", "Discipline", "End date month", "End date year"]


def costs_by_kind(client: TestClient) -> dict[str, int]:
    return {k["kind"]: k["calls"] for k in client.get("/api/settings/costs").json()["by_kind"]}


def proposal(client: TestClient) -> dict[str, Any]:
    response = client.post("/api/resume/profile")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def fields(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {field["question"]: field for field in body["fields"]}


def confirm(
    client: TestClient, body: dict[str, Any], replace: set[str] | None = None, answers: dict[str, str] | None = None
) -> Any:
    """Apply the proposal as extracted, with `answers` (by question) filled in or changed."""
    chosen = [
        {
            "question": field["question"],
            "category": field["category"],
            "answer": (answers or {}).get(field["question"], field["value"]),
            "replace": field["question"] in (replace or set()),
        }
        for field in body["fields"]
    ]
    return client.put("/api/resume/profile", json={"answers": chosen})


def bank(client: TestClient) -> dict[str, str]:
    return {entry["question"]: entry["answer"] for entry in client.get("/api/answer-bank").json()}


def test_the_proposal_reads_contact_details_and_links_including_hyperlink_targets(client: TestClient) -> None:
    add_ready_resume(client, data=full_resume())

    found = fields(proposal(client))

    assert {(f["category"], f["section"]) for q, f in found.items() if q in ("Email", "Phone")} == {
        ("personal", "resume")
    }
    assert all(field["current"] is None for field in found.values())
    assert (found["Email"]["value"], found["Phone"]["value"]) == (EMAIL, PHONE)
    assert (found["LinkedIn Profile"]["category"], found["LinkedIn Profile"]["value"]) == ("links", LINKEDIN_URL)
    assert found["GitHub"]["value"] == "https://github.com/jrivera"
    assert found["Website"]["value"] == ""
    assert {q: (found[q]["category"], found[q]["value"], found[q]["section"]) for q in [AUTHORIZED, SPONSORSHIP]} == {
        AUTHORIZED: ("work_authorization", "", "questions"),
        SPONSORSHIP: ("sponsorship", "No", "questions"),  # from my search settings
    }
    assert {"How did you hear about this job?", "Were you referred by a current employee?"} <= found.keys()
    assert bank(client) == {}  # nothing is saved until I confirm


def test_the_sponsorship_answer_follows_my_search_settings(client: TestClient) -> None:
    add_ready_resume(client, data=full_resume())
    configure_search(client, {**READY_SETTINGS, "needs_sponsorship": True})

    assert fields(proposal(client))[SPONSORSHIP]["value"] == "Yes"


def test_confirmed_answers_fill_the_next_application_form(client: TestClient, boards: FakeJobBoards) -> None:
    job_id = scored_job(client, boards, resume=full_resume())

    response = confirm(client, proposal(client), answers={AUTHORIZED: "Yes"})

    assert response.status_code == 200, response.text
    saved = bank(client)
    assert {saved["Email"], saved["Phone"], saved["LinkedIn Profile"], saved[AUTHORIZED]} == {
        EMAIL,
        PHONE,
        LINKEDIN_URL,
        "Yes",
    }
    assert "Website" not in saved  # left empty, so skipped
    answered = {q["label"]: (q["answer"], q["source"]) for q in apply(client, job_id)["questions"]}
    assert answered["Email"] == (EMAIL, "bank")
    assert answered["LinkedIn Profile"] == (LINKEDIN_URL, "bank")
    assert answered[AUTHORIZED] == ("Yes", "bank")


def test_an_existing_differing_answer_is_kept_unless_i_choose_to_replace_it(client: TestClient) -> None:
    add_ready_resume(client, data=full_resume())
    client.post("/api/answer-bank", json={"question": "Phone", "answer": "(555) 000-0000", "category": "personal"})

    body = proposal(client)
    assert (fields(body)["Phone"]["value"], fields(body)["Phone"]["current"]) == (PHONE, "(555) 000-0000")
    confirm(client, body)
    assert bank(client)["Phone"] == "(555) 000-0000"

    confirm(client, proposal(client), replace={"Phone"})
    assert bank(client)["Phone"] == PHONE


def test_confirming_twice_keeps_one_entry_per_question(client: TestClient) -> None:
    add_ready_resume(client, data=full_resume())
    confirm(client, proposal(client))
    first = client.get("/api/answer-bank").json()

    confirm(client, proposal(client), replace={"Email", "Phone"})

    assert client.get("/api/answer-bank").json() == first
    assert fields(proposal(client))["Email"]["current"] == EMAIL


def test_the_proposal_reads_my_name_location_and_education_with_one_ai_call(client: TestClient, llm: FakeLLM) -> None:
    configure_search(client)
    add_ready_resume(client, data=full_resume())

    body = proposal(client)

    found = {q: (f["category"], f["value"]) for q, f in fields(body).items()}
    assert {q: found[q] for q in ["First Name", "Last Name", "Location (City)", "Country"]} == {
        "First Name": ("personal", "Jordan"),  # proper-cased, though the resume shows "JORDAN RIVERA"
        "Last Name": ("personal", "Rivera"),
        "Location (City)": ("personal", "Brooklyn, NY"),
        "Country": ("personal", "United States"),
    }
    # The fake lists the bachelor's first; the master's is the higher degree.
    assert {q: found[q] for q in EDUCATION} == {
        "School": ("other", "Columbia University"),
        "Degree": ("other", "Master of Science"),  # written in full, though the fake says "MS"
        "Discipline": ("other", "Computer Science"),
        "End date month": ("other", "May"),
        "End date year": ("other", "2020"),
    }
    assert [(e["school"], e["degree"]) for e in body["education"]] == [
        ("University of Mumbai", "Bachelor of Technology"),
        ("Columbia University", "Master of Science"),
    ]
    assert body["selected_education"] == 1
    assert body["ai_note"] is None
    assert len(llm.profile_calls()) == 1
    assert "JORDAN RIVERA" in llm.profile_calls()[0].prompt
    assert costs_by_kind(client)["profile"] == 1


def test_my_name_and_school_fill_the_next_application_form(client: TestClient, boards: FakeJobBoards) -> None:
    job_id = scored_job(client, boards, resume=full_resume())
    add_to_forms('<label for="school">School</label><input type="text" id="school" name="school">')

    confirm(client, proposal(client))

    answered = {q["label"]: (q["answer"], q["source"]) for q in apply(client, job_id)["questions"]}
    assert answered["First Name"] == ("Jordan", "bank")
    assert answered["Last Name"] == ("Rivera", "bank")
    assert answered["School"] == ("Columbia University", "bank")


def test_without_an_api_key_the_code_found_fields_are_still_proposed(client: TestClient, llm: FakeLLM) -> None:
    add_ready_resume(client, data=full_resume())

    body = proposal(client)

    assert fields(body)["Email"]["value"] == EMAIL
    assert fields(body)["First Name"]["value"] == ""
    assert body["education"] == [] and body["selected_education"] is None
    assert "Anthropic API key" in body["ai_note"]
    assert llm.profile_calls() == []


def test_a_failed_ai_call_still_proposes_the_code_found_fields(client: TestClient, llm: FakeLLM) -> None:
    configure_search(client)
    add_ready_resume(client, data=full_resume())
    llm.fail(LLMError("Claude is overloaded."))

    body = proposal(client)

    assert fields(body)["Phone"]["value"] == PHONE
    assert "Claude is overloaded." in body["ai_note"]


def test_a_profile_needs_a_resume(client: TestClient) -> None:
    response = client.post("/api/resume/profile")
    assert response.status_code == 409
    assert response.json()["detail"] == "Upload your resume first."
