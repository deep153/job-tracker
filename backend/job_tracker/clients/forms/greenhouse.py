from job_tracker.clients.forms.reading import FormLayout

# The current hosted job boards use #application-form; older boards and the embedded form use #application_form.
LAYOUT = FormLayout(
    form="form#application-form, form#application_form",
    submit="button[type=submit], input[type=submit]",
)
