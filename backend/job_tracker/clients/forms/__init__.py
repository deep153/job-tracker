from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from job_tracker.clients.forms import ashby, greenhouse, lever
from job_tracker.clients.forms.adapter import PlatformForm
from job_tracker.clients.forms.filling import SubmitError, SubmitOutcome
from job_tracker.clients.forms.reading import FormError
from job_tracker.models.answers import FormAnswer, FormField
from job_tracker.models.platform import Platform

__all__ = ["FormError", "FormSubmitter", "SubmitError", "SubmitOutcome", "form_submitters"]


class FormSubmitter(Protocol):
    def read_fields(self, url: str) -> list[FormField]:
        """Every question on the application form at `url`, in page order. Raises FormError when the form
        can't be read."""
        ...

    def submit(
        self,
        url: str,
        answers: list[FormAnswer],
        resume_pdf: Path,
        cover_letter_pdf: Path | None,
        screenshot: Path,
        on_handover: Callable[[str], None],
    ) -> SubmitOutcome:
        """Fill in the form with `answers`, upload `resume_pdf` as the resume (and `cover_letter_pdf` as the cover
        letter), and send it; "submitted" once the confirmation shows.

        On a CAPTCHA, or a required question that wasn't there in review, calls `on_handover` with the reason and
        leaves the browser to me until I close it. Raises SubmitError on any other failure, after saving a
        screenshot of the page to `screenshot` when it can.
        """
        ...


def form_submitters(visible: bool) -> dict[Platform, FormSubmitter]:
    """The platforms whose application forms can be read and sent; `visible` shows the browser while sending."""
    return {
        "greenhouse": PlatformForm(greenhouse.LAYOUT, visible),
        "lever": PlatformForm(lever.LAYOUT, visible),
        "ashby": PlatformForm(ashby.LAYOUT, visible),
    }
