from dataclasses import dataclass, replace
from typing import Literal, get_args

AnswerCategory = Literal[
    "personal", "work_authorization", "sponsorship", "salary", "start_date", "links", "eeo", "other"
]
ANSWER_CATEGORIES: tuple[str, ...] = get_args(AnswerCategory)

FieldKind = Literal["text", "textarea", "select", "radio", "checkbox", "file"]

# Where an answer came from: my answer bank, the tailored resume (for the resume upload), drafted by the AI from
# my resume and the job, typed by me in review, or nowhere yet.
AnswerSource = Literal["bank", "resume", "ai", "you", "none"]


@dataclass(frozen=True)
class BankEntry:
    """One saved answer to a standard application question."""

    id: int
    question: str
    answer: str
    category: AnswerCategory
    created_at: str
    last_used_at: str | None


@dataclass(frozen=True)
class FormField:
    """One question on an application form, as read from the page."""

    key: str  # the field's name on the form, used to fill it
    label: str
    kind: FieldKind
    required: bool
    options: list[str]  # for selects, radio groups and checkbox groups


@dataclass(frozen=True)
class FormAnswer:
    field: FormField
    answer: str | None
    source: AnswerSource
    eeo: bool = False  # an EEO or demographic question, answered only from my saved choices

    @property
    def needs_input(self) -> bool:
        """Required, or an EEO question (which I answer deliberately, even if only to decline), and unanswered."""
        return (self.field.required or self.eeo) and self.answer is None

    def answered(self, answer: str | None, source: AnswerSource) -> "FormAnswer":
        return replace(self, answer=answer, source=source if answer is not None else "none")
