import io

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Pt

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

SUMMARY = "Backend engineer with six years of experience building payment systems in Python and Go."
SKILL_LINES = ["Languages: Python, Go, TypeScript, SQL", "Infrastructure: PostgreSQL; Docker; Kubernetes; AWS (Lambda, S3)"]


def sample_resume(summary: str = SUMMARY, pages: int = 1) -> bytes:
    """A resume laid out the way real ones are: a title, headings, labelled skill lines, a table row for a
    job's title and dates, and bullet points. Extra pages repeat the experience section after a page break."""
    document = docx.Document()
    document.add_heading("Jordan Rivera", level=0)
    contact = document.add_paragraph("Brooklyn, NY · jordan@example.com · github.com/jrivera")
    contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_heading("Summary", level=1)
    document.add_paragraph(summary)
    document.add_heading("Skills", level=1)
    for line in SKILL_LINES:
        document.add_paragraph(line)
    document.add_paragraph()
    for page in range(pages):
        if page > 0:
            document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        document.add_heading("Experience" if page == 0 else "Earlier experience", level=1)
        row = document.add_table(rows=1, cols=2).rows[0]
        title = row.cells[0].paragraphs[0].add_run(f"Senior Software Engineer, Initech {page + 1}")
        title.bold = True
        title.font.size = Pt(11)
        row.cells[1].paragraphs[0].text = "2021 – Present"
        for n in range(3):
            document.add_paragraph(f"Built ledger service number {page * 3 + n + 1} handling card payments.", "List Bullet")
    document.add_heading("Education", level=1)
    document.add_paragraph("B.S. Computer Science, State University, 2018")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
