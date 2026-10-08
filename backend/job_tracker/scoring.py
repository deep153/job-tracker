"""The Fit Scorer: how well a job matches my master resume and preferences, as a score from 0 to 100."""

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from job_tracker.llm import LLM, LLMError, estimate_cost
from job_tracker.resume import MasterResume
from job_tracker.search_settings import SearchSettings

MAX_REASONS = 5
MAX_KEYWORDS = 15
MAX_DESCRIPTION_CHARS = 20_000
MAX_OUTPUT_TOKENS = 1_000

_SENIORITY_NAMES = {
    "intern": "intern",
    "junior": "junior",
    "mid": "mid-level",
    "senior": "senior",
    "staff": "staff",
    "principal": "principal",
}

SYSTEM_PROMPT = """You screen job postings for one job seeker. Given their resume, their preferences and a job \
posting, judge how strong a fit the job is for them.

Score from 0 to 100:
- 85-100: an excellent fit; they meet nearly every requirement and the role matches what they want.
- 70-84: a good fit worth applying to; minor gaps.
- 50-69: a partial fit; noticeable gaps in skills, experience or seniority.
- 0-49: a poor fit.

Judge from evidence in the resume only; don't assume skills it doesn't show. Reasons are short sentences \
(at most 5), most important first, written to the job seeker ("You have...", "The role needs..."). \
Matched keywords are skills, tools and qualifications the posting asks for that the resume shows; missing \
keywords are ones the posting asks for that the resume lacks. Use the posting's wording for keywords and \
keep each to a few words."""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "description": "Fit from 0 (poor) to 100 (excellent)."},
        "reasons": {"type": "array", "items": {"type": "string"}, "description": "At most 5 short reasons."},
        "matched_keywords": {"type": "array", "items": {"type": "string"}},
        "missing_keywords": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score", "reasons", "matched_keywords", "missing_keywords"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class FitScore:
    score: int
    reasons: list[str]
    matched_keywords: list[str]
    missing_keywords: list[str]
    model: str
    input_tokens: int
    output_tokens: int


def build_prompt(resume: MasterResume, settings: SearchSettings, job: sqlite3.Row) -> str:
    return "\n\n".join(
        [
            f"<resume>\n{resume.text}\n\nSkills: {', '.join(resume.skills)}\n</resume>",
            f"<preferences>\n{_preferences(settings)}\n</preferences>",
            f"<job>\n{_job_text(job)}\n</job>",
            "How well does this job fit me?",
        ]
    )


def _preferences(settings: SearchSettings) -> str:
    lines = [f"Roles I want: {', '.join(settings.roles)}"]
    if settings.locations:
        lines.append(f"Locations: {'; '.join(settings.locations)}")
    names = {"remote": "remote", "hybrid": "hybrid", "onsite": "on-site"}
    lines.append(f"Work arrangements I'm open to: {', '.join(names[m] for m in settings.work_modes) or 'any'}")
    if settings.seniority:
        lines.append(f"My level: {_SENIORITY_NAMES[settings.seniority]}")
    if settings.years_experience is not None:
        lines.append(f"Years of experience: {settings.years_experience}")
    lines.append(f"I need visa sponsorship: {'yes' if settings.needs_sponsorship else 'no'}")
    if settings.min_salary:
        lines.append(f"Minimum salary: ${settings.min_salary:,} a year")
    return "\n".join(lines)


def _job_text(job: sqlite3.Row) -> str:
    lines = [f"Title: {job['title']}", f"Company: {job['board_id']}"]
    locations = json.loads(job["locations"])
    if locations:
        lines.append(f"Location: {'; '.join(locations)}")
    if job["work_mode"]:
        lines.append(f"Work arrangement: {job['work_mode']}")
    if job["salary_min"] is not None or job["salary_max"] is not None:
        pay = " - ".join(f"{v:,}" for v in (job["salary_min"], job["salary_max"]) if v is not None)
        lines.append(f"Salary: {pay} {job['salary_currency'] or ''}".rstrip())
    description = job["description"]
    if len(description) > MAX_DESCRIPTION_CHARS:
        description = description[:MAX_DESCRIPTION_CHARS] + " [...]"
    lines.append(f"\n{description}")
    return "\n".join(lines)


def score_job(
    llm: LLM, api_key: str, model: str, resume: MasterResume, settings: SearchSettings, job: sqlite3.Row
) -> FitScore:
    """Ask the model for a fit score. Raises LLMError if the call fails or the answer doesn't make sense."""
    response = llm.generate(
        api_key=api_key,
        model=model,
        system=SYSTEM_PROMPT,
        prompt=build_prompt(resume, settings, job),
        schema=SCHEMA,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    data = response.data
    score = data.get("score")
    if isinstance(score, float) and score.is_integer():
        score = int(score)
    if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
        raise LLMError(f"Claude gave a score outside 0-100 ({score!r}).")
    for key in ("reasons", "matched_keywords", "missing_keywords"):
        if not isinstance(data.get(key), list) or not all(isinstance(item, str) for item in data[key]):
            raise LLMError("Claude's answer didn't have the expected fields.")
    return FitScore(
        score=score,
        reasons=_tidy(data["reasons"], MAX_REASONS),
        matched_keywords=_tidy(data["matched_keywords"], MAX_KEYWORDS),
        missing_keywords=_tidy(data["missing_keywords"], MAX_KEYWORDS),
        model=response.model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
    )


def _tidy(items: list[str], limit: int) -> list[str]:
    tidy: list[str] = []
    for item in items:
        text = " ".join(item.split())
        if text and text.casefold() not in {t.casefold() for t in tidy}:
            tidy.append(text)
    return tidy[:limit]


def save_score(
    conn: sqlite3.Connection, job_id: int, content_hash: str, resume_version: int, fit: FitScore, scored_at: str
) -> None:
    """Replaces any earlier score for this job and resume version, so the newest score has the highest id."""
    conn.execute(
        """
        INSERT OR REPLACE INTO scores (job_id, resume_version, content_hash, score, reasons, matched_keywords,
            missing_keywords, model, scored_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            resume_version,
            content_hash,
            fit.score,
            json.dumps(fit.reasons),
            json.dumps(fit.matched_keywords),
            json.dumps(fit.missing_keywords),
            fit.model,
            scored_at,
        ),
    )


def record_usage(
    conn: sqlite3.Connection,
    kind: str,
    run_id: int | None,
    job_id: int | None,
    model: str,
    input_tokens: int,
    output_tokens: int,
    created_at: str,
) -> float:
    cost = estimate_cost(model, input_tokens, output_tokens)
    conn.execute(
        """
        INSERT INTO ai_usage (kind, run_id, job_id, model, input_tokens, output_tokens, cost_usd, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (kind, run_id, job_id, model, input_tokens, output_tokens, cost, created_at),
    )
    return cost


# The newest score for each job, whichever resume version it was scored against.
LATEST_SCORES = """
    SELECT scores.* FROM scores
    JOIN (SELECT job_id, MAX(id) AS id FROM scores GROUP BY job_id) AS latest ON latest.id = scores.id
"""
