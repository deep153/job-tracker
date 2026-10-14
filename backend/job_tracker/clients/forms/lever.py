from job_tracker.clients.forms.reading import FormLayout

# Each question's label is a .application-label block, wrapped in a <label> with the input (and, for the
# location question, its suggestions list) or, for a company's own questions, beside it. The visible submit
# button isn't a submit button: it runs the invisible hCaptcha, then submits.
LAYOUT = FormLayout(
    form="form#application-form",
    submit="#btn-submit",
    question="li.application-question",
    question_label=".application-label",
)
