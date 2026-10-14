from collections.abc import Callable
from pathlib import Path

from job_tracker.clients.forms.filling import SubmitOutcome, submit_form
from job_tracker.clients.forms.reading import FormLayout, read_form
from job_tracker.models.answers import FormAnswer, FormField


class PlatformForm:
    """A platform's application forms, read and sent with Playwright according to their layout."""

    def __init__(self, layout: FormLayout, visible: bool) -> None:
        self._layout = layout
        self._visible = visible

    def read_fields(self, url: str) -> list[FormField]:
        return read_form(url, self._layout)

    def submit(
        self,
        url: str,
        answers: list[FormAnswer],
        resume_pdf: Path,
        cover_letter_pdf: Path | None,
        screenshot: Path,
        on_handover: Callable[[str], None],
    ) -> SubmitOutcome:
        documents = {"resume": resume_pdf} | ({"cover_letter": cover_letter_pdf} if cover_letter_pdf else {})
        return submit_form(url, self._layout, answers, documents, screenshot, on_handover, self._visible)
