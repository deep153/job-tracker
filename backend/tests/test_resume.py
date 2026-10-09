import io
import zipfile
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from pypdf import PdfReader

from job_tracker.app import create_app
from job_tracker.clients.libreoffice import LibreOffice
from tests.resumes import SKILL_LINES, SUMMARY, index_of, mapping_for, sample_resume, upload


def pdf_text(pdf: bytes) -> str:
    return " ".join(" ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages).split())


def test_imported_resume_is_mapped_and_previewed_as_a_matching_pdf(client: TestClient) -> None:
    uploaded = upload(client, sample_resume())
    assert uploaded.status_code == 201, uploaded.text
    resume = uploaded.json()
    assert resume["version"] == 1
    assert resume["filename"] == "Jordan Rivera.docx"
    assert resume["page_count"] == 1
    assert resume["mapping"] is None
    assert resume["skills"] is None
    assert resume["ready"] is False

    paragraphs = {p["text"]: p for p in resume["paragraphs"]}
    assert [p["text"] for p in resume["paragraphs"] if p["text"]][:5] == [
        "Jordan Rivera",
        "Brooklyn, NY · jordan@example.com · github.com/jrivera",
        "Summary",
        SUMMARY,
        "Skills",
    ]
    assert paragraphs["Jordan Rivera"]["style"] == "Title"
    assert paragraphs["Summary"]["style"] == "Heading 1"
    assert paragraphs["Summary"]["bold"] is True
    assert paragraphs["Brooklyn, NY · jordan@example.com · github.com/jrivera"]["alignment"] == "center"
    assert paragraphs["Senior Software Engineer, Initech 1"]["bold"] is True  # inside a table
    assert paragraphs["Senior Software Engineer, Initech 1"]["size"] == 11
    assert paragraphs["2021 – Present"]["bold"] is False
    bullet = paragraphs["Built ledger service number 1 handling card payments."]
    assert bullet["style"] == "List Bullet"
    assert bullet["is_list"] is True
    assert paragraphs[SUMMARY]["is_list"] is False

    mapped = client.put("/api/resume/mapping", json=mapping_for(resume))
    assert mapped.status_code == 200, mapped.text
    assert mapped.json()["mapping"] == mapping_for(resume)
    assert mapped.json()["skills"] == [
        "Python",
        "Go",
        "TypeScript",
        "SQL",
        "PostgreSQL",
        "Docker",
        "Kubernetes",
        "AWS (Lambda, S3)",
    ]
    assert mapped.json()["ready"] is True
    assert client.get("/api/resume").json() == mapped.json()

    preview = client.get(resume["preview_url"])
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "application/pdf"
    assert len(PdfReader(io.BytesIO(preview.content)).pages) == resume["page_count"]
    text = pdf_text(preview.content)
    for paragraph in resume["paragraphs"]:
        assert paragraph["text"] in text


def test_page_count_of_a_longer_resume_is_recorded(client: TestClient) -> None:
    resume = upload(client, sample_resume(pages=2)).json()

    assert resume["page_count"] == 2
    preview = client.get(resume["preview_url"]).content
    assert len(PdfReader(io.BytesIO(preview)).pages) == 2
    assert "Built ledger service number 6 handling card payments." in pdf_text(preview)


def test_master_skills_list_can_be_edited(client: TestClient) -> None:
    resume = upload(client, sample_resume()).json()
    client.put("/api/resume/mapping", json=mapping_for(resume))

    edited = client.put(
        "/api/resume/skills", json={"skills": [" Rust ", "Python", "python", "Go", "", "Distributed  systems"]}
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["skills"] == ["Rust", "Python", "Go", "Distributed systems"]
    assert client.get("/api/resume").json()["skills"] == ["Rust", "Python", "Go", "Distributed systems"]

    # Saving the same mapping again keeps the edits; changing the Skills section starts over from it.
    assert client.put("/api/resume/mapping", json=mapping_for(resume)).json()["skills"][0] == "Rust"
    languages_only = {**mapping_for(resume), "skills": [index_of(resume, SKILL_LINES[0])]}
    assert client.put("/api/resume/mapping", json=languages_only).json()["skills"] == [
        "Python",
        "Go",
        "TypeScript",
        "SQL",
    ]

    emptied = client.put("/api/resume/skills", json={"skills": [" ", ""]})
    assert emptied.status_code == 422
    assert emptied.json()["detail"] == "Keep at least one skill in your master skills list."


def test_files_that_are_not_a_valid_docx_are_rejected(client: TestClient) -> None:
    pdf = upload(client, b"%PDF-1.7 not a resume", filename="resume.pdf")
    assert pdf.status_code == 422
    assert pdf.json()["detail"] == "Upload your resume as a Word document (.docx)."

    corrupt_message = (
        "This file couldn't be opened as a Word document. It may be damaged or in another format. "
        "Save it as .docx from Word or Google Docs and upload it again."
    )
    garbage = upload(client, b"\x00\x01 definitely not a zip file", filename="resume.docx")
    assert garbage.status_code == 422
    assert garbage.json()["detail"] == corrupt_message

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("notes.txt", "a zip file, but not a Word document")
    not_word = upload(client, archive.getvalue(), filename="resume.docx")
    assert not_word.status_code == 422
    assert not_word.json()["detail"] == corrupt_message

    truncated = upload(client, sample_resume()[:2000], filename="resume.docx")
    assert truncated.status_code == 422
    assert truncated.json()["detail"] == corrupt_message

    assert client.get("/api/resume").json() is None
    assert client.get("/api/resume/versions").json() == []


def test_incomplete_or_invalid_mappings_are_rejected(client: TestClient) -> None:
    before_upload = client.put("/api/resume/mapping", json={"summary": [1], "skills": [2]})
    assert before_upload.status_code == 404
    assert before_upload.json()["detail"] == "Upload your resume first."

    resume = upload(client, sample_resume()).json()
    good = mapping_for(resume)
    skills_first = client.put("/api/resume/skills", json={"skills": ["Python"]})
    assert skills_first.status_code == 409
    assert skills_first.json()["detail"] == "Mark your Summary and Skills paragraphs first."

    blank = next(p["index"] for p in resume["paragraphs"] if not p["text"])
    heading_only = [index_of(resume, "Skills")]
    cases = [
        ({**good, "summary": []}, "Mark at least one paragraph as your Summary."),
        ({**good, "skills": []}, "Mark at least one paragraph as your Skills section."),
        (
            {**good, "skills": [*good["skills"], *good["summary"]]},
            "A paragraph can be part of the Summary or the Skills section, not both.",
        ),
        ({**good, "summary": [999]}, "Paragraph 999 isn't in this resume."),
        (
            {**good, "summary": [*good["summary"], blank]},
            "Blank paragraphs can't be part of the Summary or Skills section.",
        ),
        ({**good, "skills": heading_only}, "The paragraphs marked as Skills don't list any skills."),
    ]
    for mapping, message in cases:
        response = client.put("/api/resume/mapping", json=mapping)
        assert response.status_code == 422, mapping
        assert response.json()["detail"] == message

    assert client.get("/api/resume").json()["mapping"] is None


def test_replacing_the_master_creates_a_new_version_and_keeps_earlier_ones(client: TestClient) -> None:
    first_file = sample_resume()
    first = upload(client, first_file).json()
    client.put("/api/resume/mapping", json=mapping_for(first))

    newer_summary = "Backend engineer with seven years of experience building payment systems."
    second = upload(client, sample_resume(summary=newer_summary), filename="Jordan Rivera 2026.docx").json()

    assert second["version"] == 2
    assert second["mapping"] is None  # each version is mapped on its own
    assert client.get("/api/resume").json()["version"] == 2
    versions = client.get("/api/resume/versions").json()
    assert [(v["version"], v["filename"], v["ready"]) for v in versions] == [
        (2, "Jordan Rivera 2026.docx", False),
        (1, "Jordan Rivera.docx", True),
    ]

    original = client.get(first["original_url"])
    assert original.status_code == 200
    assert original.content == first_file
    assert SUMMARY in pdf_text(client.get(first["preview_url"]).content)
    assert newer_summary in pdf_text(client.get(second["preview_url"]).content)
    assert client.get("/api/resume/versions/99/preview.pdf").status_code == 404


def test_missing_libreoffice_is_reported_and_blocks_import(tmp_path: Path) -> None:
    app = create_app(tmp_path / "test.db", httpx.Client(), office=LibreOffice(None))
    with TestClient(app) as client:
        status = client.get("/api/status").json()
        assert status["libreoffice"]["available"] is False
        assert status["libreoffice"]["message"].startswith("LibreOffice isn't installed")

        refused = upload(client, sample_resume())
        assert refused.status_code == 409
        assert refused.json()["detail"] == status["libreoffice"]["message"]
        assert client.get("/api/resume").json() is None


def test_libreoffice_found_at_startup_is_reported(client: TestClient) -> None:
    assert client.get("/api/status").json() == {"libreoffice": {"available": True, "message": None}}
