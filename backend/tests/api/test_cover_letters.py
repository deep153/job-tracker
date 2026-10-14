from fastapi.testclient import TestClient

from tests.api.test_answers import BANK, add_entries, questions
from tests.api.test_lever_and_ashby_forms import FULL_NAME, LEVER_WHY, WHY_TEXT
from tests.api.test_submitting import reviewed, submit
from tests.support import fake_forms
from tests.support.applications import apply, pdf_text, scored_job
from tests.support.fake_job_boards import FakeJobBoards
from tests.support.fake_llm import DEFAULT_COVER_LETTER, FakeLLM
from tests.support.resumes import SUMMARY

EDITED = (
    "Dear Globex team,\n\nI build payment systems in Python and Go, and Globex's ledger work is what I want to do "
    "next.\n\nBest,\nJordan Rivera"
)


def test_a_form_without_a_cover_letter_field_gets_no_cover_letter(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    application = apply(client, scored_job(client, boards, form="lever.html", platform="lever"))

    assert application["status"] == "in_review", application
    assert application["cover_letter"] is None
    assert llm.cover_letter_calls() == []


def test_a_cover_letter_upload_gets_a_tailored_letter_and_my_edited_version_is_sent(
    client: TestClient, boards: FakeJobBoards, llm: FakeLLM
) -> None:
    application = reviewed(client, boards)

    assert application["cover_letter"]["text"] == DEFAULT_COVER_LETTER
    [row] = [q for q in questions(application) if q[0] == "cover_letter"]
    assert row == ("cover_letter", "Cover Letter", "file", False, "Tailored cover letter (PDF)", "cover_letter", False)
    [call] = llm.cover_letter_calls()
    assert (call.model, SUMMARY in call.prompt, "Payments in Go." in call.prompt) == ("claude-sonnet-5-5", True, True)
    assert "Never invent" in call.system
    letter_pdf = client.get(application["cover_letter"]["pdf_url"])
    assert DEFAULT_COVER_LETTER.split("\n")[2] in pdf_text(letter_pdf.content)

    edited = client.put(f"/api/applications/{application['id']}/cover-letter", json={"text": EDITED})
    assert edited.status_code == 200, edited.text
    assert edited.json()["cover_letter"]["text"] == EDITED
    submitted = submit(client, application["id"])

    assert submitted["status"] == "submitted", submitted
    assert submitted["cover_letter"]["text"] == EDITED
    [sent] = fake_forms.submissions()
    filename, content = sent.files["cover_letter"]
    assert filename.endswith(".pdf")
    assert "Globex's ledger work is what I want to do next." in pdf_text(content)


def test_a_cover_letter_text_box_is_filled_with_my_edited_letter(client: TestClient, boards: FakeJobBoards) -> None:
    add_entries(client, [*BANK, FULL_NAME])
    fake_forms.add_to_forms(
        '<li class="application-question"><label><div class="application-label">Cover letter</div>'
        '<div class="application-field"><textarea name="cards[1c719ca9][field9]"></textarea></div></label></li>'
    )
    application = apply(client, scored_job(client, boards, form="lever.html", platform="lever"))
    [row] = [q for q in questions(application) if q[0] == "cards[1c719ca9][field9]"]
    assert row[1:] == ("Cover letter", "textarea", False, "Tailored cover letter", "cover_letter", False)
    client.put(f"/api/applications/{application['id']}/answers", json={"answers": {LEVER_WHY: WHY_TEXT}})
    client.put(f"/api/applications/{application['id']}/cover-letter", json={"text": EDITED})

    submitted = submit(client, application["id"])

    assert submitted["status"] == "submitted", submitted
    [sent] = fake_forms.submissions()
    assert sent.fields["cards[1c719ca9][field9]"].replace("\r\n", "\n") == EDITED
