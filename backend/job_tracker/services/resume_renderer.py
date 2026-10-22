"""The Resume Renderer: writes tailored Summary, Skills and bullet text into a copy of the master .docx.

Only the mapped paragraphs change, and their text is replaced inside the runs they already have, so each
paragraph keeps its fonts and styles (a bold "Languages:" label stays bold, the skills after it stay plain).
"""

import io

import docx
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from job_tracker.models.resume import Bullet, SkillLine
from job_tracker.services.resume_reader import body_paragraphs, separator

# Runs that hold text, including those inside links, tracked insertions and smart tags.
_TEXT_RUNS = "./w:r | ./w:hyperlink/w:r | ./w:ins/w:r | ./w:smartTag/w:r"
_W_BODY = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body"


def render(
    master: bytes,
    summary_paragraphs: list[int],
    summary: list[str],
    skills: dict[int, SkillLine],
    bullets: list[Bullet] | None = None,
) -> tuple[bytes, str]:
    """The tailored .docx, and its text.

    `summary` has one text per Summary paragraph; extra texts join the last paragraph, and Summary paragraphs
    left without text are removed. `skills` maps a Skills paragraph's index to the line it should now list.
    `bullets` are reworded experience bullets: each one's text after its label replaces the paragraph's.
    """
    document = docx.Document(io.BytesIO(master))
    paragraphs = list(body_paragraphs(document))
    count = len(summary_paragraphs)
    texts = summary[: count - 1] + [" ".join(summary[count - 1 :])] if len(summary) > count else summary
    for position, index in enumerate(summary_paragraphs):
        if position < len(texts):
            _replace(paragraphs[index], 0, texts[position])
        else:
            _remove(paragraphs[index])
    for index, line in skills.items():
        paragraph = paragraphs[index]
        raw = _raw_text(paragraph)
        keep = _label_end(raw) if line.label else 0
        _replace(paragraph, keep, separator(raw[keep:]).join(line.skills))
    for bullet in bullets or []:
        paragraph = paragraphs[bullet.index]
        _replace(paragraph, _label_end(_raw_text(paragraph)) if bullet.label else 0, bullet.text)
    out = io.BytesIO()
    document.save(out)
    text = "\n".join(p.text for p in body_paragraphs(document))
    return out.getvalue(), text


def _runs(paragraph: Paragraph) -> list[Run]:
    return [Run(r, paragraph) for r in paragraph._p.xpath(_TEXT_RUNS)]


def _raw_text(paragraph: Paragraph) -> str:
    return "".join(run.text for run in _runs(paragraph))


def _label_end(raw: str) -> int:
    """Where the text after a "Label:" (and the spaces after its colon) starts."""
    end = raw.find(":") + 1
    while end < len(raw) and raw[end] in " \t":
        end += 1
    return end


def _replace(paragraph: Paragraph, keep: int, text: str) -> None:
    """Keep the first `keep` characters and put `text` after them, in the run where the kept text ends (or the
    next one), so it takes that run's formatting. Later runs are emptied; runs holding pictures are left alone."""
    position, placed = 0, False
    for run in _runs(paragraph):
        if run._r.xpath("./w:drawing | ./w:pict"):
            continue
        current = run.text
        start, position = position, position + len(current)
        if placed:
            run.text = ""
        elif position > keep or (position == keep == 0):
            run.text = current[: keep - start] + text
            placed = True
    if not placed:
        paragraph.add_run(text)


def _remove(paragraph: Paragraph) -> None:
    """Drop a paragraph, or empty it where a paragraph is required (the last one in a table cell)."""
    element = paragraph._p
    parent = element.getparent()
    if parent is not None and (parent.tag == _W_BODY or len(parent.findall(element.tag)) > 1):
        parent.remove(element)
    else:
        _replace(paragraph, 0, "")
