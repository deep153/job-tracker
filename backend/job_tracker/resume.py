"""Resume master: the imported .docx, which of its paragraphs are the Summary and Skills, and the master skills list."""

import io
import json
import re
import shutil
import sqlite3
import uuid
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import docx
from docx.document import Document
from docx.styles.style import ParagraphStyle
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

from job_tracker.db import Database
from job_tracker.libreoffice import MISSING_MESSAGE, ConversionError, LibreOffice

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SKILLS = 200
MAX_SKILL_LENGTH = 80

_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
_W_P = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"


class ResumeError(Exception):
    """A request about the resume that can't be done, with a message for the user."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class ParagraphInfo:
    index: int
    text: str
    style: str | None
    bold: bool
    italic: bool
    font: str | None
    size: float | None  # points
    alignment: str | None
    is_list: bool


def body_paragraphs(document: Document) -> Iterator[Paragraph]:
    """Every paragraph in the document body in reading order, including those inside tables and text boxes.

    A paragraph's position in this sequence is how the Summary and Skills mapping refers to it.
    """
    for element in document.element.body.iter(_W_P):
        # Word stores text boxes twice (modern and fallback copies); only the modern copy counts.
        if any(ancestor.tag == _FALLBACK for ancestor in element.iterancestors()):
            continue
        yield Paragraph(element, document.part)


def read_paragraphs(filename: str, data: bytes) -> list[ParagraphInfo]:
    if not filename.lower().endswith(".docx"):
        raise ResumeError(422, "Upload your resume as a Word document (.docx).")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ResumeError(413, "That file is larger than 10 MB. Upload your resume as a regular .docx file.")
    try:
        document = docx.Document(io.BytesIO(data))
        paragraphs = [_paragraph_info(i, p) for i, p in enumerate(body_paragraphs(document))]
    except Exception:
        raise ResumeError(
            422,
            "This file couldn't be opened as a Word document. It may be damaged or in another format. "
            "Save it as .docx from Word or Google Docs and upload it again.",
        ) from None
    if not any(p.text for p in paragraphs):
        raise ResumeError(422, "This document doesn't contain any text.")
    return paragraphs


def _paragraph_info(index: int, paragraph: Paragraph) -> ParagraphInfo:
    style = paragraph.style if isinstance(paragraph.style, ParagraphStyle) else None
    runs = [run for run in paragraph.runs if run.text.strip()]
    first = runs[0] if runs else None
    p_pr = paragraph._p.pPr
    style_p_pr = style.element.pPr if style is not None else None
    alignment = paragraph.alignment if paragraph.alignment is not None else _style_value(style, "alignment")
    return ParagraphInfo(
        index=index,
        text=" ".join(paragraph.text.split()),
        style=style.name if style is not None else None,
        bold=bool(runs) and all(_run_flag(run.bold, style, "bold") for run in runs),
        italic=bool(runs) and all(_run_flag(run.italic, style, "italic") for run in runs),
        font=(first.font.name if first is not None and first.font.name else None) or _style_value(style, "name"),
        size=(first.font.size.pt if first is not None and first.font.size else None) or _style_size(style),
        alignment=alignment.name.lower() if alignment is not None else None,
        is_list=(p_pr is not None and p_pr.numPr is not None)
        or (style_p_pr is not None and style_p_pr.numPr is not None),
    )


def _styles(style: ParagraphStyle | None) -> Iterator[ParagraphStyle]:
    """A style and the styles it's based on, nearest first."""
    while style is not None:
        yield style
        base = style.base_style
        style = base if isinstance(base, ParagraphStyle) else None


def _run_flag(value: bool | None, style: ParagraphStyle | None, name: str) -> bool:
    if value is not None:
        return value
    return next((bool(v) for s in _styles(style) if (v := getattr(s.font, name)) is not None), False)


def _style_value(style: ParagraphStyle | None, name: str) -> Any:
    for s in _styles(style):
        value = getattr(s.paragraph_format, name) if name == "alignment" else getattr(s.font, name)
        if value is not None:
            return value
    return None


def _style_size(style: ParagraphStyle | None) -> float | None:
    size = _style_value(style, "size")
    return size.pt if size is not None else None


# "Skills", "Technical Skills:", "Skills & Tools": a heading, not a skill.
_SKILLS_HEADING = re.compile(r"^(?:(?:technical|core|key|professional)\s+)?skills?(?:\s*(?:&|and)\s*\w+)?\s*:?$", re.I)
# "Languages: Python, Go": the label isn't a skill.
_LABEL = re.compile(r"^([^:,;]{1,40}):\s*(.+)$")
_SEPARATORS = set(",;|•·▪●◦\t")


def skills_from_text(texts: list[str]) -> list[str]:
    """The skills listed in the Skills section's paragraphs, in order, without duplicates."""
    skills: list[str] = []
    for text in texts:
        text = text.strip()
        if not text or _SKILLS_HEADING.match(text):
            continue
        if label := _LABEL.match(text):
            text = label[2]
        for item in _split_top_level(text):
            add_skill(skills, item)
    return skills


def add_skill(skills: list[str], item: str) -> None:
    skill = " ".join(item.split()).strip(" .*-–—")
    if skill and len(skill) <= MAX_SKILL_LENGTH and skill.casefold() not in {s.casefold() for s in skills}:
        skills.append(skill)


def _split_top_level(text: str) -> list[str]:
    """Split on list separators, except inside brackets: "Cloud (AWS, GCP)" is one skill."""
    items, current, depth = [], "", 0
    for char in text:
        depth += (char in "([{") - (char in ")]}")
        if char in _SEPARATORS and depth <= 0:
            items.append(current)
            current = ""
        else:
            current += char
    items.append(current)
    return items


@dataclass(frozen=True)
class MasterResume:
    """The current resume version as the AI sees it."""

    version: int
    text: str
    skills: list[str]


class ResumeStore:
    """Versions of the master resume: each upload is a new version, and earlier versions are kept."""

    def __init__(self, db: Database, files_dir: Path, office: LibreOffice) -> None:
        self._db = db
        self._dir = files_dir / "resumes"
        self._office = office

    def import_docx(self, filename: str, data: bytes) -> dict[str, Any]:
        paragraphs = read_paragraphs(filename, data)
        if not self._office.available:
            raise ResumeError(409, MISSING_MESSAGE)
        directory = uuid.uuid4().hex
        target = self._dir / directory
        target.mkdir(parents=True)
        try:
            (target / "master.docx").write_bytes(data)
            (self._office.convert_to_pdf(target / "master.docx", target)).rename(target / "preview.pdf")
            page_count = len(PdfReader(target / "preview.pdf").pages)
        except ConversionError as error:
            shutil.rmtree(target, ignore_errors=True)
            raise ResumeError(422, error.message) from None
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise
        with self._db.connect() as conn:
            version = conn.execute(
                """
                INSERT INTO resume_master (filename, directory, uploaded_at, paragraphs, page_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    Path(filename).name,
                    directory,
                    datetime.now(UTC).isoformat(),
                    json.dumps([asdict(p) for p in paragraphs]),
                    page_count,
                ),
            ).lastrowid
        assert version is not None
        return self.get(version)

    def current(self) -> dict[str, Any] | None:
        with self._db.connect() as conn:
            row = conn.execute("SELECT * FROM resume_master ORDER BY id DESC LIMIT 1").fetchone()
        return None if row is None else _resume_json(row)

    def get(self, version: int) -> dict[str, Any]:
        return _resume_json(self._row(version))

    def master(self) -> MasterResume | None:
        """The current version, or None until it's uploaded and its Summary and Skills are marked."""
        resume = self.current()
        if resume is None or not resume["ready"]:
            return None
        text = "\n".join(p["text"] for p in resume["paragraphs"] if p["text"])
        return MasterResume(resume["version"], text, resume["skills"])

    def versions(self) -> list[dict[str, Any]]:
        with self._db.connect() as conn:
            rows = conn.execute("SELECT * FROM resume_master ORDER BY id DESC").fetchall()
        keys = ("version", "filename", "uploaded_at", "page_count", "ready", "preview_url", "original_url")
        return [{key: resume[key] for key in keys} for resume in map(_resume_json, rows)]

    def file(self, version: int, name: str) -> Path:
        directory: str = self._row(version)["directory"]
        return self._dir / directory / name

    def save_mapping(self, summary: list[int], skills: list[int]) -> dict[str, Any]:
        row = self._current_row()
        paragraphs = json.loads(row["paragraphs"])
        summary, skills = sorted(set(summary)), sorted(set(skills))
        if not summary:
            raise ResumeError(422, "Mark at least one paragraph as your Summary.")
        if not skills:
            raise ResumeError(422, "Mark at least one paragraph as your Skills section.")
        if set(summary) & set(skills):
            raise ResumeError(422, "A paragraph can be part of the Summary or the Skills section, not both.")
        for index in summary + skills:
            if not 0 <= index < len(paragraphs):
                raise ResumeError(422, f"Paragraph {index} isn't in this resume.")
            if not paragraphs[index]["text"]:
                raise ResumeError(422, "Blank paragraphs can't be part of the Summary or Skills section.")
        listed = skills_from_text([paragraphs[i]["text"] for i in skills])
        if not listed:
            raise ResumeError(422, "The paragraphs marked as Skills don't list any skills.")
        # Keep my edits to the skills list unless the Skills section itself changed.
        keep = row["skills"] is not None and json.loads(row["skills_paragraphs"]) == skills
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE resume_master SET summary_paragraphs = ?, skills_paragraphs = ?, skills = ? WHERE id = ?",
                (json.dumps(summary), json.dumps(skills), row["skills"] if keep else json.dumps(listed), row["id"]),
            )
        return self.get(row["id"])

    def save_skills(self, skills: list[str]) -> dict[str, Any]:
        row = self._current_row()
        if row["skills_paragraphs"] is None:
            raise ResumeError(409, "Mark your Summary and Skills paragraphs first.")
        cleaned: list[str] = []
        for skill in skills:
            if len(" ".join(skill.split())) > MAX_SKILL_LENGTH:
                raise ResumeError(422, f"Keep each skill under {MAX_SKILL_LENGTH} characters.")
            add_skill(cleaned, skill)
        if not cleaned:
            raise ResumeError(422, "Keep at least one skill in your master skills list.")
        if len(cleaned) > MAX_SKILLS:
            raise ResumeError(422, f"Keep your master skills list to {MAX_SKILLS} skills or fewer.")
        with self._db.connect() as conn:
            conn.execute("UPDATE resume_master SET skills = ? WHERE id = ?", (json.dumps(cleaned), row["id"]))
        return self.get(row["id"])

    def _current_row(self) -> sqlite3.Row:
        with self._db.connect() as conn:
            row: sqlite3.Row | None = conn.execute("SELECT * FROM resume_master ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            raise ResumeError(404, "Upload your resume first.")
        return row

    def _row(self, version: int) -> sqlite3.Row:
        with self._db.connect() as conn:
            row: sqlite3.Row | None = conn.execute("SELECT * FROM resume_master WHERE id = ?", (version,)).fetchone()
        if row is None:
            raise ResumeError(404, "Resume version not found.")
        return row


def _resume_json(row: sqlite3.Row) -> dict[str, Any]:
    mapped = row["summary_paragraphs"] is not None
    skills = json.loads(row["skills"]) if row["skills"] is not None else None
    version = row["id"]
    return {
        "version": version,
        "filename": row["filename"],
        "uploaded_at": row["uploaded_at"],
        "page_count": row["page_count"],
        "paragraphs": json.loads(row["paragraphs"]),
        "mapping": (
            {"summary": json.loads(row["summary_paragraphs"]), "skills": json.loads(row["skills_paragraphs"])}
            if mapped
            else None
        ),
        "skills": skills,
        "ready": mapped and bool(skills),
        "preview_url": f"/api/resume/versions/{version}/preview.pdf",
        "original_url": f"/api/resume/versions/{version}/original.docx",
    }
