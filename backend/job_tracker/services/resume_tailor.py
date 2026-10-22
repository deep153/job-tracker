"""The Resume Tailor: a new Summary, reordered Skills and reworded experience bullets for one job, using only
skills from my master list, and the job's keywords it couldn't cover."""

from dataclasses import dataclass, field
from typing import Any, TypeGuard

from job_tracker.clients.claude import LLM, LLMError
from job_tracker.models.job import Job
from job_tracker.models.resume import Bullet, SkillLine
from job_tracker.services.fit_scorer import job_text

MAX_KEYWORDS = 20
MAX_OUTPUT_TOKENS = 2_000

SYSTEM_PROMPT = """You tailor one job seeker's resume to a job posting by editing only three parts of it: the \
Summary, the order of the Skills, and the wording of the experience bullets.

Rules:
- Never invent experience, employers, job titles, dates, metrics, education or skills. Use only facts the \
resume states.
- Rewrite the Summary so it speaks to the posting's main requirements, using the posting's wording where the \
resume backs it up. Keep it about as long as the current Summary, and give one text per Summary paragraph.
- For each Skills line, list its skills with the most relevant to the posting first. Use only skills from \
the allowed skills list, spelled as they are there. You may add an allowed skill the posting asks for to the \
line it fits best, or leave out a skill that doesn't matter for this job.
- You may reword an experience bullet's text toward the posting's wording, where the bullet already backs it \
up. Give only the text after the bullet's label (the label stays as it is), keep every number exactly as \
written (percentages, counts, "9+"), name no skill or tool the bullet doesn't already show unless it's on the \
allowed skills list, and stay within about 10% of the original length. Leaving a bullet unchanged is fine; \
list only the bullets you changed.
- Keywords are the posting's most important skills, tools and qualifications (at most 20), in its wording, \
a few words each, most important first. When target keywords are given, aim the Summary and Skills at those \
instead.
- Gaps are the keywords (the target keywords when given, otherwise yours) that the resume can't honestly show, \
even after your edits. Spell them as they are in the keywords."""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The new Summary, one text per Summary paragraph.",
        },
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "line": {"type": "integer", "description": "The Skills line's number."},
                    "skills": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["line", "skills"],
                "additionalProperties": False,
            },
        },
        "bullets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "bullet": {"type": "integer", "description": "The experience bullet's number."},
                    "text": {"type": "string", "description": "Its new text after the label."},
                },
                "required": ["bullet", "text"],
                "additionalProperties": False,
            },
            "description": "Only the experience bullets you reworded.",
        },
        "keywords": {"type": "array", "items": {"type": "string"}},
        "gaps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Keywords the resume can't honestly show.",
        },
    },
    "required": ["summary", "skills", "bullets", "keywords", "gaps"],
    "additionalProperties": False,
}

_INVALID = "Claude's tailoring answer didn't have the expected fields."


@dataclass(frozen=True)
class TailorRequest:
    resume_text: str
    summary: list[str]
    skills: list[SkillLine]
    allowed_skills: list[str]
    job: Job
    target_keywords: list[str] = field(default_factory=list)  # the Fit Scorer's; empty lets the tailor pick
    bullets: list[Bullet] = field(default_factory=list)


@dataclass(frozen=True)
class Shorten:
    """The last edit made the resume longer than the master; the next one has to be shorter."""

    pages: int
    master_pages: int
    summary: list[str]
    bullets: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TailorResult:
    summary: list[str]
    skills: list[SkillLine]  # one per line of the request, in the same order
    bullets: dict[int, str]  # reworded text after the label, by position in the request's bullets; not yet checked
    keywords: list[str]  # the target keywords, or the tailor's own when there were none
    gaps: list[str]  # of the keywords, in their spelling
    model: str
    input_tokens: int
    output_tokens: int


def build_prompt(request: TailorRequest, shorten: Shorten | None) -> str:
    summary = "\n".join(f"Paragraph {n}: {text}" for n, text in enumerate(request.summary, 1))
    words = sum(len(text.split()) for text in request.summary)
    lines = "\n".join(
        f"Line {n}: {f'{line.label}: ' if line.label else ''}{', '.join(line.skills)}"
        for n, line in enumerate(request.skills, 1)
    )
    parts = [
        f"<resume>\n{request.resume_text}\n</resume>",
        f'<summary paragraphs="{len(request.summary)}" words="{words}">\n{summary}\n</summary>',
        f"<skills_lines>\n{lines}\n</skills_lines>",
        f"<allowed_skills>\n{', '.join(request.allowed_skills)}\n</allowed_skills>",
        f"<job>\n{job_text(request.job)}\n</job>",
    ]
    if request.bullets:
        bullets = "\n".join(
            f"Bullet {n}{f' (label “{b.label}”)' if b.label else ''}: {b.text}"
            for n, b in enumerate(request.bullets, 1)
        )
        parts.append(f"<experience_bullets>\n{bullets}\n</experience_bullets>")
    if request.target_keywords:
        parts.append(f"<target_keywords>\n{', '.join(request.target_keywords)}\n</target_keywords>")
    if shorten is None:
        parts.append(f"Tailor my Summary, Skills{' and bullets' if request.bullets else ''} to this job.")
    else:
        previous = sum(len(text.split()) for text in shorten.summary)
        ask = (
            f"Your last Summary ({previous} words) made my resume run to {shorten.pages} pages instead of "
            f"{shorten.master_pages}. Tailor it again with a shorter Summary: at most {words} words, fewer if you "
            "can, and no more skills on a line than it has now."
        )
        if shorten.bullets:
            reworded = "\n".join(f"Bullet {n + 1}: {text}" for n, text in sorted(shorten.bullets.items()))
            ask += (
                f" Your reworded bullets were:\n{reworded}\nKeep any you reword no longer than the original "
                "bullet, shorter if you can."
            )
        parts.append(ask)
    return "\n\n".join(parts)


class ResumeTailor:
    """Asks the LLM for the edit, then enforces in code that skills come only from my master list."""

    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    def tailor(self, api_key: str, model: str, request: TailorRequest, shorten: Shorten | None = None) -> TailorResult:
        """Raises LLMError if the call fails or the answer doesn't make sense."""
        response = self._llm.generate(
            api_key=api_key,
            model=model,
            system=SYSTEM_PROMPT,
            prompt=build_prompt(request, shorten),
            schema=SCHEMA,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        data = response.data
        summary, skills, keywords = data.get("summary"), data.get("skills"), data.get("keywords")
        gaps, bullets = data.get("gaps", []), data.get("bullets", [])
        if not _strings(summary) or not _strings(keywords) or not _strings(gaps) or not isinstance(skills, list):
            raise LLMError(_INVALID)
        if not isinstance(bullets, list):
            raise LLMError(_INVALID)
        reworded: dict[int, str] = {}
        for item in bullets:
            number = item.get("bullet") if isinstance(item, dict) else None
            if not isinstance(number, int) or isinstance(number, bool) or not isinstance(item.get("text"), str):
                raise LLMError(_INVALID)
            text = " ".join(item["text"].split())
            if 0 < number <= len(request.bullets) and text:
                reworded[number - 1] = text
        summary = [" ".join(text.split()) for text in summary if text.strip()]
        if not summary:
            raise LLMError(_INVALID)
        chosen: dict[int, list[str]] = {}
        for line in skills:
            number = line.get("line") if isinstance(line, dict) else None
            if not isinstance(number, int) or isinstance(number, bool) or not _strings(line.get("skills")):
                raise LLMError(_INVALID)
            chosen[number - 1] = line["skills"]
        targets = request.target_keywords or _tidy(keywords)[:MAX_KEYWORDS]
        spelling = {_key(keyword): keyword for keyword in targets}
        return TailorResult(
            summary=summary,
            skills=allowed_lines(request.skills, chosen, request.allowed_skills),
            bullets=reworded,
            keywords=targets,
            gaps=[spelling[_key(gap)] for gap in _tidy(gaps) if _key(gap) in spelling],
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )


def allowed_lines(lines: list[SkillLine], chosen: dict[int, list[str]], allowed: list[str]) -> list[SkillLine]:
    """The Skills lines with the chosen skills, keeping only skills on the master list (in its spelling), each
    once. A line that wasn't chosen, or whose choice has no allowed skill, keeps the skills it had."""
    spelling = {_key(skill): skill for skill in allowed}
    used: set[str] = set()
    picked: dict[int, list[str]] = {}
    for index, skills in sorted(chosen.items()):
        if not 0 <= index < len(lines):
            continue
        kept = []
        for skill in skills:
            key = _key(skill)
            if key in spelling and key not in used:
                used.add(key)
                kept.append(spelling[key])
        if kept:
            picked[index] = kept
    result = []
    for index, line in enumerate(lines):
        unpicked = [s for s in line.skills if _key(s) not in used] or line.skills
        result.append(SkillLine(line.label, picked.get(index, unpicked)))
    return result


def _key(skill: str) -> str:
    return " ".join(skill.split()).casefold()


def _strings(value: object) -> TypeGuard[list[str]]:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _tidy(items: list[str]) -> list[str]:
    tidy: list[str] = []
    for item in items:
        text = " ".join(item.split())
        if text and text.casefold() not in {t.casefold() for t in tidy}:
            tidy.append(text)
    return tidy
