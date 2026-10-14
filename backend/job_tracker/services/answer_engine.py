"""Answers an application form's questions from my answer bank, matching questions however they're worded, and
picks out the open-ended ones the AI may draft. EEO and demographic questions are never among those."""

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from job_tracker.models.answers import BankEntry, FormAnswer, FormField

RESUME_ANSWER = "Tailored resume (PDF)"

# A question matches a bank entry when one's words are (nearly) all among the other's, and the two are still
# alike overall, so "Email" doesn't answer "Do you consent to email updates?" nor "Name" answer "First Name".
_MIN_SHARED = 90
_MIN_ALIKE = 60
_MIN_OPTION = 85

_SAME_MEANING = [
    (re.compile(r"\bu\.s\.(?:a\.)?|\busa\b|\bunited states(?: of america)?\b"), " us "),
    (re.compile(r"\be-mail\b"), " email "),
    (re.compile(r"\bcv\b"), " resume "),
]
# Words that make a question about a different thing, so "Name" isn't answered with my "Last Name".
_QUALIFIERS = {"first", "last", "middle", "preferred"}
_FILLER = set(
    "a an and are as at be by can do does for from have if in is it of on or our please the this to we what "
    "when which will with would you your".split()
)


_EEO = re.compile(
    r"\b(gender|sex|sexual orientation|transgender|pronouns?|race|racial|ethnicity|ethnic|hispanic|latin[aox]?|"
    r"veterans?|disability|disabilities|disabled|demographics?|self[- ]identif\w*)\b",
    re.I,
)
# A free-text question this long, or ending in "?", asks for more than a fact like a name or a link.
_OPEN_ENDED_WORDS = 6


def is_eeo(field: FormField) -> bool:
    return _EEO.search(field.label) is not None


def open_ended(answer: FormAnswer) -> bool:
    """An unanswered free-text question the AI may draft from my resume and the job."""
    field = answer.field
    if answer.answer is not None or answer.eeo or field.kind not in ("text", "textarea") or field.options:
        return False
    return field.kind == "textarea" or field.label.endswith("?") or len(field.label.split()) >= _OPEN_ENDED_WORDS


def _words(text: str) -> str:
    text = re.sub(r"\([^)]*\)", " ", text.casefold())
    for pattern, replacement in _SAME_MEANING:
        text = pattern.sub(replacement, text)
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def _question(text: str) -> str:
    return " ".join(word for word in _words(text).split() if word not in _FILLER)


@dataclass(frozen=True)
class DraftedAnswers:
    answers: list[FormAnswer]
    used: set[int]  # ids of the bank entries that answered something


def choices(field: FormField) -> list[str]:
    """The answers a field accepts, or [] for free text; a lone checkbox is checked or not."""
    if field.options:
        return field.options
    return ["Yes", "No"] if field.kind == "checkbox" else []


def exact_choice(answer: str, field: FormField) -> str | None:
    """The field's option that is `answer`, ignoring case and spacing; free text is returned as is."""
    options = choices(field)
    if not options:
        return answer
    wanted = " ".join(answer.split()).casefold()
    return next((option for option in options if " ".join(option.split()).casefold() == wanted), None)


def _closest_choice(answer: str, field: FormField) -> str | None:
    options = choices(field)
    if not options:
        return answer
    wanted = _words(answer)

    def score(option: str) -> tuple[bool, float]:
        # Options often add detail after the answer, like "United States +1" or "Yes, I am authorized"; when
        # several do, the closest one wins.
        words = _words(option)
        return words.startswith(f"{wanted} "), fuzz.ratio(wanted, words)

    best = max(options, key=score)
    starts, alike = score(best)
    return best if starts or alike >= _MIN_OPTION else None


def _best_entry(field: FormField, bank: list[BankEntry]) -> BankEntry | None:
    question = _question(field.label)
    if not question:
        return None
    best: tuple[float, BankEntry] | None = None
    for entry in bank:
        saved = _question(entry.question)
        if not saved or _QUALIFIERS & set(question.split()) != _QUALIFIERS & set(saved.split()):
            continue
        shared = fuzz.token_set_ratio(question, saved)
        alike = fuzz.token_sort_ratio(question, saved)
        if shared >= _MIN_SHARED and alike >= _MIN_ALIKE and (best is None or shared + alike > best[0]):
            best = (shared + alike, entry)
    return None if best is None else best[1]


def draft_answers(fields: list[FormField], bank: list[BankEntry]) -> DraftedAnswers:
    answers = []
    used = set()
    for field in fields:
        if field.kind == "file":
            is_resume = "resume" in _words(field.label).split()
            answers.append(FormAnswer(field, RESUME_ANSWER, "resume") if is_resume else FormAnswer(field, None, "none"))
            continue
        eeo = is_eeo(field)
        entry = _best_entry(field, bank)
        answer = None if entry is None else _closest_choice(entry.answer, field)
        if entry is not None and answer is not None:
            used.add(entry.id)
            answers.append(FormAnswer(field, answer, "bank", eeo))
        else:
            answers.append(FormAnswer(field, None, "none", eeo))
    return DraftedAnswers(answers, used)
