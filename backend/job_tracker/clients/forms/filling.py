"""Filling in and sending an application form with Playwright, shared by the platform adapters."""

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Frame, Page, sync_playwright

from job_tracker.clients.forms.reading import FormError, clean, field_locator, open_dropdown, open_form, raw_fields
from job_tracker.models.answers import FormAnswer

SubmitOutcome = Literal["submitted", "needs_manual"]

RESULT_TIMEOUT_S = 30
_HANDOVER_POLL_MS = 1000


class SubmitError(FormError):
    def __init__(self, message: str, screenshot: bool = False) -> None:
        super().__init__(message)
        self.screenshot = screenshot


# Runs in a frame: whether a CAPTCHA someone has to solve is showing. Invisible reCAPTCHA (which many forms load
# and which needs nobody) doesn't count.
_CAPTCHA = """
() => {
  const shown = (el) => {
    const box = el.getBoundingClientRect();
    return box.width > 0 && box.height > 0 && getComputedStyle(el).visibility !== "hidden";
  };
  const selectors = [
    ".g-recaptcha:not([data-size=invisible])", ".h-captcha", ".cf-turnstile",
    "iframe[src*='recaptcha/api2/bframe']", "iframe[src*='recaptcha/enterprise/bframe']",
    "iframe[title*='challenge' i]",
  ];
  return selectors.some((selector) => [...document.querySelectorAll(selector)].some(shown));
}
"""

# Runs in a frame: whether it shows the confirmation that the application went through.
_CONFIRMED = """
() => /confirmation/i.test(location.pathname)
  || document.querySelector("#application_confirmation, .application-confirmation") !== null
  || /thank you for (applying|your application)|application (has been )?(submitted|received)/i
       .test(document.body ? document.body.innerText : "")
"""

# Runs in a frame: the error messages it shows.
_ERRORS = """
() => [...document.querySelectorAll("[role=alert], .error-message, .helper-text--error, .field-error, .flash-error")]
  .map((el) => (el.innerText || "").trim()).filter(Boolean)
"""


def _in_any_frame(page: Page, script: str) -> list[Any]:
    results = []
    for frame in page.frames:
        try:
            results.append(frame.evaluate(script))
        except PlaywrightError:
            continue
    return results


def _captcha(page: Page) -> bool:
    return any(_in_any_frame(page, _CAPTCHA))


def _confirmed(page: Page) -> bool:
    return any(_in_any_frame(page, _CONFIRMED))


def _errors(page: Page) -> list[str]:
    return [message for messages in _in_any_frame(page, _ERRORS) for message in messages]


def _fill(frame: Frame, answer: FormAnswer, resume_pdf: Path) -> None:
    field = answer.field
    if field.kind == "file":
        if answer.source == "resume":
            frame.locator(
                f'input[type=file][id="{field.key}"], input[type=file][name="{field.key}"]'
            ).first.set_input_files(resume_pdf)
        return
    if answer.answer is None:
        return
    box = field_locator(frame, field.key)
    if field.kind in ("text", "textarea"):
        box.fill(answer.answer)
    elif field.kind == "select" and box.evaluate("(el) => el.tagName") == "SELECT":
        box.select_option(label=answer.answer)
    elif field.kind == "select":
        options = open_dropdown(frame, box)
        if answer.answer not in options:
            box.press("Escape")
            raise SubmitError(f"“{field.label}” no longer offers the answer “{answer.answer}”.")
        list_id = box.get_attribute("aria-controls")
        frame.locator(f'[id="{list_id}"] [role=option]').nth(options.index(answer.answer)).click()
    elif field.kind in ("radio", "checkbox") and field.options:
        inputs = frame.locator(f'input[name="{field.key}"]')
        labels = [
            clean(text) for text in inputs.evaluate_all("(els) => els.map((el) => el.labels?.[0]?.innerText || '')")
        ]
        if answer.answer not in labels:
            raise SubmitError(f"“{field.label}” no longer offers the answer “{answer.answer}”.")
        inputs.nth(labels.index(answer.answer)).check()
    elif field.kind == "checkbox":
        box.set_checked(answer.answer == "Yes")


def _unknown_required(frame: Frame, selector: str, answers: list[FormAnswer]) -> list[str]:
    """Labels of required questions on the form that weren't there when it was reviewed."""
    known = {answer.field.key for answer in answers}
    return [
        clean(field["label"])
        for field in raw_fields(frame, selector)
        if field["required"] and field["key"] not in known
    ]


def _screenshot(page: Page, path: Path) -> bool:
    try:
        page.screenshot(path=path, full_page=True)
    except PlaywrightError:
        return False
    return True


def _hand_over(page: Page, reason: str, on_handover: Callable[[str], None], visible: bool) -> SubmitOutcome:
    """Leave the browser to me until I close it; "submitted" if I finish and the confirmation shows meanwhile."""
    on_handover(reason)
    if not visible:
        return "needs_manual"
    while not page.is_closed():
        try:
            if _confirmed(page):
                return "submitted"
            page.wait_for_timeout(_HANDOVER_POLL_MS)
        except PlaywrightError:
            continue
    return "needs_manual"


def _await_result(page: Page, on_handover: Callable[[str], None], visible: bool) -> SubmitOutcome:
    deadline = time.monotonic() + RESULT_TIMEOUT_S
    while time.monotonic() < deadline:
        try:
            if _confirmed(page):
                return "submitted"
            errors = _errors(page)
            if errors:
                raise SubmitError(f"The form showed an error after submitting: {' '.join(errors[:3])}")
            if _captcha(page):
                return _hand_over(page, "A CAPTCHA appeared after submitting.", on_handover, visible)
            page.wait_for_timeout(250)
        except PlaywrightError:
            if page.is_closed():
                raise SubmitError("The browser was closed before the application finished sending.") from None
    raise SubmitError(
        f"No confirmation appeared within {RESULT_TIMEOUT_S} seconds of submitting. Check the screenshot and the "
        "company's site to see whether it went through before trying again."
    )


def submit_form(
    url: str,
    selector: str,
    submit_button: str,
    answers: list[FormAnswer],
    resume_pdf: Path,
    screenshot: Path,
    on_handover: Callable[[str], None],
    visible: bool,
) -> SubmitOutcome:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not visible)
        page = browser.new_page()
        try:
            frame = open_form(page, url, selector)
            unknown = _unknown_required(frame, selector, answers)
            for answer in answers:
                _fill(frame, answer, resume_pdf)
            if unknown:
                labels = ", ".join(f"“{label}”" for label in unknown)
                return _hand_over(
                    page,
                    f"The form asks required questions that weren't there in review: {labels}.",
                    on_handover,
                    visible,
                )
            if _captcha(page):
                return _hand_over(page, "The form has a CAPTCHA to solve.", on_handover, visible)
            frame.locator(selector).first.locator(submit_button).first.click()
            return _await_result(page, on_handover, visible)
        except SubmitError as error:
            raise SubmitError(error.message, _screenshot(page, screenshot)) from error
        except FormError:
            raise
        except PlaywrightError as error:
            raise SubmitError(
                f"The browser failed while submitting: {error.message}", _screenshot(page, screenshot)
            ) from error
        finally:
            browser.close()
