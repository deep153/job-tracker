from typing import Protocol

from job_tracker.clients.forms.greenhouse import GreenhouseForm
from job_tracker.clients.forms.reading import FormError
from job_tracker.models.answers import FormField
from job_tracker.models.platform import Platform

__all__ = ["FormError", "FormSubmitter", "form_submitters"]


class FormSubmitter(Protocol):
    def read_fields(self, url: str) -> list[FormField]:
        """Every question on the application form at `url`, in page order. Raises FormError when the form
        can't be read."""
        ...


def form_submitters() -> dict[Platform, FormSubmitter]:
    """The platforms whose application forms can be read; the others come later."""
    return {"greenhouse": GreenhouseForm()}
