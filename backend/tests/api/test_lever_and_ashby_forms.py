from typing import Any

from fastapi.testclient import TestClient

from tests.api.test_answers import BANK, add_entries, questions
from tests.api.test_submitting import submit
from tests.support import fake_forms
from tests.support.applications import apply, scored_job
from tests.support.fake_job_boards import FakeJobBoards

FULL_NAME = ("Full name", "Jordan Rivera", "personal")
WHY_TEXT = "I want to build payment systems at Globex's scale."

LEVER_WHY = "cards[1c719ca9][field1]"
ASHBY_WHY = "5b1e2f0a-0000-4000-8000-000000000003"
ASHBY_PRIVACY = "I have read the privacy notice."


def reviewed(
    client: TestClient, boards: FakeJobBoards, platform: str, answers: dict[str, str], **variants: bool
) -> Any:
    """An application to a `platform` job in review, with `answers` typed in for what the bank didn't answer."""
    add_entries(client, [*BANK, FULL_NAME])
    application = apply(
        client, scored_job(client, boards, form=f"{platform}.html", variants=variants, platform=platform)
    )
    assert application["status"] == "in_review", application
    response = client.put(f"/api/applications/{application['id']}/answers", json={"answers": answers})
    assert response.json()["can_approve"], response.text
    return response.json()


def sent_fields() -> dict[str, str]:
    [sent] = fake_forms.submissions()
    return {name: value for name, value in sent.fields.items() if value}


def test_applying_to_a_lever_job_reads_its_form_and_approving_submits_it(
    client: TestClient, boards: FakeJobBoards
) -> None:
    add_entries(client, [*BANK, FULL_NAME])
    application = apply(client, scored_job(client, boards, form="lever.html", platform="lever"))

    assert application["status"] == "in_review", application
    assert questions(application) == [
        ("resume", "Resume/CV", "file", True, "Tailored resume (PDF)", "resume", False),
        ("name", "Full name", "text", True, "Jordan Rivera", "bank", False),
        ("email", "Email", "text", True, "jordan@example.com", "bank", False),
        ("phone", "Phone", "text", False, None, "none", False),
        ("urls[LinkedIn]", "LinkedIn URL", "text", False, "https://linkedin.com/in/jrivera", "bank", False),
        (
            "cards[1c719ca9][field0]",
            "Are you legally authorized to work in the United States?",
            "radio",
            True,
            "Yes",
            "bank",
            False,
        ),
        (LEVER_WHY, "Why do you want to work at Globex?", "textarea", True, None, "none", True),
        ("eeo[gender]", "Gender", "select", False, "Decline to self-identify", "bank", False),
        ("comments", "Additional information", "textarea", False, None, "none", False),
    ]
    client.put(f"/api/applications/{application['id']}/answers", json={"answers": {LEVER_WHY: WHY_TEXT}})

    submitted = submit(client, application["id"])

    assert (submitted["status"], submitted["error"]) == ("submitted", None)
    assert sent_fields() == {
        "name": "Jordan Rivera",
        "email": "jordan@example.com",
        "urls[LinkedIn]": "https://linkedin.com/in/jrivera",
        "cards[1c719ca9][baseTemplate]": "{}",
        "cards[1c719ca9][field0]": "Yes",
        LEVER_WHY: WHY_TEXT,
        "eeo[gender]": "Decline to self-identify",
        "accountId": "b8300af6",
    }
    [sent] = fake_forms.submissions()
    pdf = client.get(f"/api/applications/{application['id']}/resume.pdf").content
    assert (list(sent.files), sent.files["resume"][1]) == (["resume"], pdf)


def test_applying_to_an_ashby_job_reads_its_form_and_approving_submits_it(
    client: TestClient, boards: FakeJobBoards
) -> None:
    add_entries(client, [*BANK, FULL_NAME])
    application = apply(client, scored_job(client, boards, form="ashby.html", platform="ashby"))

    assert application["status"] == "in_review", application
    assert questions(application) == [
        ("_systemfield_name", "Name", "text", True, "Jordan Rivera", "bank", False),
        ("_systemfield_email", "Email", "text", True, "jordan@example.com", "bank", False),
        ("_systemfield_resume", "Resume", "file", True, "Tailored resume (PDF)", "resume", False),
        (
            "5b1e2f0a-0000-4000-8000-000000000001",
            "LinkedIn Profile",
            "text",
            False,
            "https://linkedin.com/in/jrivera",
            "bank",
            False,
        ),
        (
            "5b1e2f0a-0000-4000-8000-000000000002",
            "Are you authorized to work in the US?",
            "radio",
            True,
            "Yes",
            "bank",
            False,
        ),
        (ASHBY_WHY, "Why do you want to work at Globex?", "textarea", True, None, "none", True),
        (ASHBY_PRIVACY, "Privacy Notice Acknowledgement", "checkbox", True, None, "none", True),
        ("eeoc_gender", "Gender", "radio", False, "Decline to self-identify", "bank", False),
    ]
    by_key = {q["key"]: q for q in application["questions"]}
    assert by_key["5b1e2f0a-0000-4000-8000-000000000002"]["options"] == ["Yes", "No"]
    client.put(
        f"/api/applications/{application['id']}/answers",
        json={"answers": {ASHBY_WHY: WHY_TEXT, ASHBY_PRIVACY: "Yes"}},
    )

    submitted = submit(client, application["id"])

    assert (submitted["status"], submitted["error"]) == ("submitted", None)
    assert sent_fields() == {
        "_systemfield_name": "Jordan Rivera",
        "_systemfield_email": "jordan@example.com",
        "5b1e2f0a-0000-4000-8000-000000000001": "https://linkedin.com/in/jrivera",
        "5b1e2f0a-0000-4000-8000-000000000002": "Yes",
        ASHBY_WHY: WHY_TEXT,
        ASHBY_PRIVACY: "on",
        "eeoc_gender": "Decline to self-identify",
    }
    [sent] = fake_forms.submissions()
    pdf = client.get(f"/api/applications/{application['id']}/resume.pdf").content
    assert (list(sent.files), sent.files["_systemfield_resume"][1]) == (["_systemfield_resume"], pdf)


def test_a_lever_form_with_a_captcha_is_handed_over_to_me(client: TestClient, boards: FakeJobBoards) -> None:
    application = reviewed(client, boards, "lever", {LEVER_WHY: WHY_TEXT}, captcha=True)

    handed_over = submit(client, application["id"])

    assert handed_over["status"] == "needs_manual"
    assert handed_over["error"].startswith("The form has a CAPTCHA to solve.")
    assert fake_forms.submissions() == []


ASHBY_ANSWERS = {ASHBY_WHY: WHY_TEXT, ASHBY_PRIVACY: "Yes"}


def test_an_ashby_form_with_a_captcha_is_handed_over_to_me(client: TestClient, boards: FakeJobBoards) -> None:
    application = reviewed(client, boards, "ashby", ASHBY_ANSWERS, captcha=True)

    handed_over = submit(client, application["id"])

    assert handed_over["status"] == "needs_manual"
    assert handed_over["error"].startswith("The form has a CAPTCHA to solve.")
    assert fake_forms.submissions() == []


def test_a_required_ashby_question_added_after_review_is_handed_over_to_me(
    client: TestClient, boards: FakeJobBoards
) -> None:
    application = reviewed(client, boards, "ashby", ASHBY_ANSWERS)
    fake_forms.add_to_forms(
        '<div class="ashby-application-form-field-entry" data-field-path="5b1e2f0a-0000-4000-8000-000000000009">'
        '<label class="_heading_f7cvd_52 _required_f7cvd_91 ashby-application-form-question-title" '
        'for="5b1e2f0a-0000-4000-8000-000000000009">Are you willing to relocate?</label>'
        '<input name="5b1e2f0a-0000-4000-8000-000000000009" id="5b1e2f0a-0000-4000-8000-000000000009" type="text" />'
        "</div>"
    )

    handed_over = submit(client, application["id"])

    assert handed_over["status"] == "needs_manual"
    assert handed_over["error"].startswith(
        "The form asks required questions that weren't there in review: “Are you willing to relocate?”."
    )
    assert fake_forms.submissions() == []
