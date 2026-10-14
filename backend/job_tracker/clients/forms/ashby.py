from job_tracker.clients.forms.reading import FormLayout

# There's no <form>: the app builds the questions (and, in a second container, the EEO survey) inside the
# Application tab, and sends them with a script. A required question is marked only by a class on its label.
LAYOUT = FormLayout(
    form="#form:has(.ashby-application-form-container)",
    submit=".ashby-application-form-submit-button",
    question="[data-field-path]",
    question_label=".ashby-application-form-question-title",
)
