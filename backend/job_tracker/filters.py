"""Hard filters: deterministic rules that drop postings I'd never take, before anything else happens to them."""

import re
from dataclasses import dataclass
from typing import Literal

from job_tracker.postings import Posting, SalaryRange
from job_tracker.search_settings import SearchSettings

Rule = Literal["role", "excluded_keyword", "location", "seniority", "experience", "sponsorship", "salary"]

RULES: tuple[Rule, ...] = ("role", "excluded_keyword", "location", "seniority", "experience", "sponsorship", "salary")


@dataclass(frozen=True)
class Rejection:
    rule: Rule
    reason: str


def check(posting: Posting, settings: SearchSettings) -> Rejection | None:
    """The first rule this posting breaks, or None if it passes them all."""
    if settings.roles and not any(_has_phrase_words(posting.title, role) for role in settings.roles):
        return Rejection("role", "Title doesn't match any of your roles.")
    for keyword in settings.excluded_keywords:
        if _has_phrase_words(posting.title, keyword):
            return Rejection("excluded_keyword", f"Title contains “{keyword}”.")
    if reason := _location_problem(posting, settings):
        return Rejection("location", reason)
    if reason := _seniority_problem(posting.title, settings.seniority):
        return Rejection("seniority", reason)
    if settings.years_experience is not None and (reason := _years_problem(posting.description, settings.years_experience)):
        return Rejection("experience", reason)
    if settings.needs_sponsorship and refuses_sponsorship(posting.description):
        return Rejection("sponsorship", "Says it doesn't sponsor visas.")
    if settings.min_salary is not None and (reason := _salary_problem(posting.salary, settings.min_salary)):
        return Rejection("salary", reason)
    return None


def _salary_problem(salary: SalaryRange | None, minimum: int) -> str | None:
    # My minimum is in US dollars; pay in other currencies isn't compared.
    if salary is None or salary.currency not in (None, "USD"):
        return None
    top = salary.maximum if salary.maximum is not None else salary.minimum
    if top is None or top >= minimum:
        return None
    return f"Pays up to ${top:,}, below your ${minimum:,} minimum."


_SPONSORSHIP = r"(?:(?:visa|immigration|employment|employer|work)\s+)?sponsor"
_NO_SPONSORSHIP = re.compile(
    "|".join(
        [
            rf"\bno\s+{_SPONSORSHIP}",
            r"\b(?:not|unable to|cannot|can't|can not|won't|will not|do not|does not|don't|doesn't)\s+"
            rf"(?:be\s+)?(?:able\s+to\s+)?(?:offer|provide|support|consider)?\s*{_SPONSORSHIP}",
            rf"\bnot\s+eligible\s+for\s+{_SPONSORSHIP}",
            rf"\bwithout\s+(?:the\s+need\s+for\s+)?(?:(?:current|now)\s+or\s+(?:future|in\s+the\s+future)\s+)?{_SPONSORSHIP}",
            r"\bsponsorship\s+(?:is\s+)?(?:not\s+available|unavailable|not\s+offered)",
        ]
    ),
    re.I,
)


def refuses_sponsorship(description: str) -> bool:
    return _NO_SPONSORSHIP.search(description) is not None


YEARS_TOLERANCE = 2
_MAX_PLAUSIBLE_YEARS = 20
# "5+ years", "3-5 years", "at least 8 years", "2 years of", "4 yrs experience"; a bare "for 25 years." doesn't count.
_YEARS = re.compile(
    r"(?P<lead>at least|minimum of|min\.?|over|more than)?\s*\b(?P<low>\d{1,2})\s*(?P<plus>\+|plus)?"
    r"(?:\s*(?:-|–|—|to)\s*(?P<high>\d{1,2})\s*\+?)?\s*(?:years?|yrs?)\b"
    r"(?P<tail>\s+(?:of|in|with|experience)\b|['’])?",
    re.I,
)


def required_years(description: str) -> tuple[int, int | None] | None:
    """The experience a posting asks for, as (minimum, maximum if it gives a range); its highest ask wins."""
    asks: list[tuple[int, int | None]] = []
    for match in _YEARS.finditer(description):
        if not (match["lead"] or match["plus"] or match["high"] or match["tail"]):
            continue
        low, high = int(match["low"]), int(match["high"]) if match["high"] else None
        if low <= _MAX_PLAUSIBLE_YEARS and (high is None or low <= high <= _MAX_PLAUSIBLE_YEARS):
            asks.append((low, high))
    return max(asks, key=lambda ask: ask[0], default=None)


def _years_problem(description: str, mine: int) -> str | None:
    ask = required_years(description)
    if ask is None:
        return None
    low, high = ask
    asked = f"{low}–{high}" if high is not None else f"{low}+"
    if low > mine + YEARS_TOLERANCE or (high is not None and mine > high + YEARS_TOLERANCE):
        return f"Asks for {asked} years of experience; you have {mine}."
    return None


# Levels are compared by position; a title two or more levels away from mine is "far" from my level.
_LEVELS = ("intern", "junior", "mid", "senior", "staff", "principal", "director")
_LEVEL_NAMES = {
    "intern": "Intern",
    "junior": "Junior",
    "mid": "Mid-level",
    "senior": "Senior",
    "staff": "Staff",
    "principal": "Principal",
    "director": "Director",
}
SENIORITY_TOLERANCE = 1
# Checked in order, so "Associate Director" is a director and "Senior Associate" is senior.
_TITLE_LEVELS = (
    ("director", re.compile(r"\b(director|head of|vp|vice president|chief)\b", re.I)),
    ("principal", re.compile(r"\b(principal|distinguished|fellow)\b", re.I)),
    ("staff", re.compile(r"\bstaff\b", re.I)),
    ("senior", re.compile(r"\b(senior|sr)\b", re.I)),
    ("intern", re.compile(r"\b(intern|internship|co-?op)\b", re.I)),
    ("junior", re.compile(r"\b(junior|jr|entry[- ]level|new grad|graduate|associate)\b", re.I)),
    ("staff", re.compile(r"\bIV\b")),
    ("senior", re.compile(r"\bIII\b")),
    ("mid", re.compile(r"\bII\b")),
    ("junior", re.compile(r"\bI\b")),
)


def title_level(title: str) -> str | None:
    """The seniority a title states, or None when it doesn't say."""
    return next((level for level, pattern in _TITLE_LEVELS if pattern.search(title)), None)


def _seniority_problem(title: str, mine: str | None) -> str | None:
    level = title_level(title)
    if mine is None or level is None:
        return None
    gap = _LEVELS.index(level) - _LEVELS.index(mine)
    if abs(gap) <= SENIORITY_TOLERANCE:
        return None
    direction = "above" if gap > 0 else "below"
    return f"{_LEVEL_NAMES[level]} title, well {direction} your level ({_LEVEL_NAMES[mine].lower()})."


def _location_problem(posting: Posting, settings: SearchSettings) -> str | None:
    if not posting.locations:
        return None  # nothing to judge by
    remote = posting.remote is True
    if remote and "remote" in settings.work_modes:
        return None
    if not any(_in_place(where, mine) for where in posting.locations for mine in settings.locations):
        if remote:
            return "Remote role, and you haven't chosen remote."
        return f"{' · '.join(posting.locations)} isn't one of your locations."
    if remote:
        return None  # remote, or from an office in one of my cities
    if "hybrid" in _words(" ".join([posting.title, *posting.locations])):
        return None if "hybrid" in settings.work_modes else "Hybrid role, and you haven't chosen hybrid."
    return None if "onsite" in settings.work_modes else "On-site role, and you haven't chosen on-site."


def _in_place(where: str, mine: str) -> bool:
    """Whether a posting location is in one of my locations, judged by its first part ("New York" of "New York, NY")."""
    place = re.findall(r"\w+", mine.split(",")[0].casefold())
    words = re.findall(r"\w+", where.casefold())
    return bool(place) and any(words[i : i + len(place)] == place for i in range(len(words) - len(place) + 1))


def _words(text: str, with_parts: bool = True) -> set[str]:
    """Lower-cased words. Hyphenated words are joined ("back-end" is "backend") and, with `with_parts`, also split."""
    words: set[str] = set()
    for chunk in re.findall(r"[\w+#]+(?:-[\w+#]+)*", text.casefold()):
        parts = chunk.split("-")
        words.add(_stem("".join(parts)))
        if with_parts:
            words.update(_stem(part) for part in parts)
    return words


def _stem(word: str) -> str:
    """Folds simple word forms together, so "Engineering" and "Engineers" match "Engineer"."""
    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _has_phrase_words(text: str, phrase: str) -> bool:
    """Every word of `phrase` appears somewhere in `text`, in any order."""
    wanted = _words(phrase, with_parts=False)
    return bool(wanted) and wanted <= _words(text)
