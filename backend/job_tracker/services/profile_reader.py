"""The Profile Reader: my name, location and education, read from my resume by one structured AI call, then
tidied by code so forms can match them (proper-cased names, degrees in full, month names)."""

import re
from dataclasses import dataclass
from typing import Any

from job_tracker.clients.claude import LLM, LLMError
from job_tracker.models.profile import Education

MAX_OUTPUT_TOKENS = 2_000

SYSTEM_PROMPT = """You read a job seeker's resume and return their name, location and education exactly as the \
resume states them, so job application forms can be filled in.

Rules:
- Never guess. Leave a field empty ("") when the resume doesn't state it.
- first_name and last_name in proper case ("Deep Gandhi", not "DEEP GANDHI").
- city, region (state or province) and country of where they live, as the resume's contact details give them. \
Give the country's full name ("United States") when the city or region makes it clear.
- One education entry per degree, in the order the resume lists them. Write each degree in full ("Master of \
Science", not "MS"; "Bachelor of Technology", not "B.Tech."). discipline is the field of study. end_month is the \
full month name and end_year four digits, of graduation or expected graduation."""

_TEXT = {"type": "string"}
SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "first_name": _TEXT,
        "last_name": _TEXT,
        "city": _TEXT,
        "region": _TEXT,
        "country": _TEXT,
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "school": _TEXT,
                    "degree": _TEXT,
                    "discipline": _TEXT,
                    "end_month": _TEXT,
                    "end_year": _TEXT,
                },
                "required": ["school", "degree", "discipline", "end_month", "end_year"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["first_name", "last_name", "city", "region", "country", "education"],
    "additionalProperties": False,
}

_INVALID = "Claude's reading of the resume didn't have the expected fields."

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

# Abbreviations, compared without dots, spaces or case, and the degree written in full.
_DEGREES = {
    "aa": "Associate of Arts",
    "as": "Associate of Science",
    "ba": "Bachelor of Arts",
    "ab": "Bachelor of Arts",
    "bs": "Bachelor of Science",
    "bsc": "Bachelor of Science",
    "be": "Bachelor of Engineering",
    "beng": "Bachelor of Engineering",
    "btech": "Bachelor of Technology",
    "bba": "Bachelor of Business Administration",
    "bfa": "Bachelor of Fine Arts",
    "bcom": "Bachelor of Commerce",
    "bca": "Bachelor of Computer Applications",
    "ma": "Master of Arts",
    "ms": "Master of Science",
    "msc": "Master of Science",
    "meng": "Master of Engineering",
    "me": "Master of Engineering",
    "mtech": "Master of Technology",
    "mba": "Master of Business Administration",
    "mfa": "Master of Fine Arts",
    "mca": "Master of Computer Applications",
    "mph": "Master of Public Health",
    "phd": "Doctor of Philosophy",
    "dphil": "Doctor of Philosophy",
    "md": "Doctor of Medicine",
    "jd": "Juris Doctor",
}

# A degree's level by the first of these words it contains; higher is higher.
_LEVELS = [("doctor", 4), ("juris", 4), ("master", 3), ("bachelor", 2), ("associate", 1)]


@dataclass(frozen=True)
class ProfileReading:
    first_name: str
    last_name: str
    location: str  # "City, Region"
    country: str
    education: list[Education]
    model: str
    input_tokens: int
    output_tokens: int


def proper_case(name: str) -> str:
    """A name in proper case, if it's written all in capitals or all in lowercase; otherwise as written."""
    name = " ".join(name.split())
    if name != name.upper() and name != name.lower():
        return name
    return re.sub(r"[^\W\d_]+", lambda word: word[0].capitalize(), name.lower())


def degree_in_full(degree: str) -> str:
    degree = " ".join(degree.split())
    return _DEGREES.get(re.sub(r"[\s.]", "", degree).lower(), degree)


def month_name(month: str) -> str:
    """The full month name for "5", "05", "May" or "may.", or the text as given if it's none of those."""
    month = month.strip().rstrip(".")
    if month.isdigit() and 1 <= int(month) <= 12:
        return MONTHS[int(month) - 1]
    return next((name for name in MONTHS if len(month) >= 3 and name.lower().startswith(month.lower())), month)


def preferred(education: list[Education]) -> int | None:
    """The index of the highest degree, the most recent among equals; None if there are none."""
    if not education:
        return None

    def rank(n: int) -> tuple[int, int, int]:
        degree = education[n].degree.lower()
        level = next((value for word, value in _LEVELS if word in degree), 0)
        year = int(education[n].end_year) if education[n].end_year.isdigit() else 0
        month = MONTHS.index(education[n].end_month) + 1 if education[n].end_month in MONTHS else 0
        return level, year, month

    return max(range(len(education)), key=rank)


def build_prompt(resume_text: str) -> str:
    return f"<resume>\n{resume_text}\n</resume>\n\nRead my name, location and education from my resume."


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise LLMError(_INVALID)
    return " ".join(value.split())


class ProfileReader:
    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    def read(self, api_key: str, model: str, resume_text: str) -> ProfileReading:
        """Raises LLMError if the call fails or the answer doesn't make sense."""
        response = self._llm.generate(
            api_key=api_key,
            model=model,
            system=SYSTEM_PROMPT,
            prompt=build_prompt(resume_text),
            schema=SCHEMA,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        data = response.data
        entries = data.get("education")
        if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
            raise LLMError(_INVALID)
        education = [
            Education(
                school=_text(entry, "school"),
                degree=degree_in_full(_text(entry, "degree")),
                discipline=_text(entry, "discipline"),
                end_month=month_name(_text(entry, "end_month")),
                end_year=_text(entry, "end_year"),
            )
            for entry in entries
        ]
        location = ", ".join(part for part in (_text(data, "city"), _text(data, "region")) if part)
        return ProfileReading(
            first_name=proper_case(_text(data, "first_name")),
            last_name=proper_case(_text(data, "last_name")),
            location=location,
            country=_text(data, "country"),
            education=[entry for entry in education if entry.school or entry.degree],
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
