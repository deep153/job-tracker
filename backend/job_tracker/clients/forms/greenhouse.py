from collections.abc import Callable
from pathlib import Path

from job_tracker.clients.forms.filling import SubmitOutcome, submit_form
from job_tracker.clients.forms.reading import read_form
from job_tracker.models.answers import FormAnswer, FormField

# The current hosted job boards use #application-form; older boards and the embedded form use #application_form.
_FORM = "form#application-form, form#application_form"
_SUBMIT = "button[type=submit], input[type=submit]"


class GreenhouseForm:
    def __init__(self, visible: bool) -> None:
        self._visible = visible

    def read_fields(self, url: str) -> list[FormField]:
        return read_form(url, _FORM)

    def submit(
        self,
        url: str,
        answers: list[FormAnswer],
        resume_pdf: Path,
        screenshot: Path,
        on_handover: Callable[[str], None],
    ) -> SubmitOutcome:
        return submit_form(url, _FORM, _SUBMIT, answers, resume_pdf, screenshot, on_handover, self._visible)
