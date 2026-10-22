from dataclasses import dataclass


@dataclass(frozen=True)
class ParagraphInfo:
    """One paragraph of the resume .docx, with the formatting the mapping screen shows."""

    index: int
    text: str
    style: str | None
    bold: bool
    italic: bool
    font: str | None
    size: float | None  # points
    alignment: str | None
    is_list: bool


@dataclass(frozen=True)
class ResumeVersion:
    """One uploaded version of the master resume. Each upload is a new version; earlier ones are kept."""

    version: int
    filename: str
    directory: str
    uploaded_at: str
    paragraphs: list[ParagraphInfo]
    page_count: int
    summary_paragraphs: list[int] | None = None
    skills_paragraphs: list[int] | None = None
    skills: list[str] | None = None
    bullet_paragraphs: list[int] | None = None  # experience bullets; None for versions mapped before they existed

    @property
    def mapped(self) -> bool:
        return self.summary_paragraphs is not None

    @property
    def proposed_bullets(self) -> list[int] | None:
        """The default experience-bullet marking: every list item after the last Summary or Skills paragraph."""
        if not self.mapped:
            return None
        last = max([*(self.summary_paragraphs or []), *(self.skills_paragraphs or [])])
        return [p.index for p in self.paragraphs if p.index > last and p.is_list and p.text]

    @property
    def ready(self) -> bool:
        """Its Summary and Skills are marked, so it can be scored against and tailored."""
        return self.mapped and bool(self.skills)


@dataclass(frozen=True)
class SkillLine:
    """One line of the Skills section: an optional label ("Languages") and the skills it lists, in order."""

    label: str | None
    skills: list[str]


@dataclass(frozen=True)
class MasterResume:
    """The current resume version as the AI sees it."""

    version: int
    text: str
    skills: list[str]
