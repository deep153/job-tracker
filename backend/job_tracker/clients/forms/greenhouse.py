from job_tracker.clients.forms.reading import read_form
from job_tracker.models.answers import FormField

# The current hosted job boards use #application-form; older boards and the embedded form use #application_form.
_FORM = "form#application-form, form#application_form"


class GreenhouseForm:
    def read_fields(self, url: str) -> list[FormField]:
        return read_form(url, _FORM)
