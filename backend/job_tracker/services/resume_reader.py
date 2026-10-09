"""Reading a resume .docx: its paragraphs with their formatting, and the skills its Skills section lists."""

import io
import re
from collections.abc import Iterator
from typing import Any

import docx
from docx.document import Document
from docx.styles.style import ParagraphStyle
from docx.text.paragraph import Paragraph

from job_tracker.models.resume import ParagraphInfo
from job_tracker.services.errors import InvalidRequestError, TooLargeError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SKILL_LENGTH = 80

_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
_W_P = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"


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
        raise InvalidRequestError("Upload your resume as a Word document (.docx).")
    if len(data) > MAX_UPLOAD_BYTES:
        raise TooLargeError("That file is larger than 10 MB. Upload your resume as a regular .docx file.")
    try:
        document = docx.Document(io.BytesIO(data))
        paragraphs = [_paragraph_info(i, p) for i, p in enumerate(body_paragraphs(document))]
    except Exception:
        raise InvalidRequestError(
            "This file couldn't be opened as a Word document. It may be damaged or in another format. "
            "Save it as .docx from Word or Google Docs and upload it again.",
        ) from None
    if not any(p.text for p in paragraphs):
        raise InvalidRequestError("This document doesn't contain any text.")
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
