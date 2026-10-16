"""Reading an application form's questions from a page with Playwright, shared by the platform adapters."""

from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Frame, Locator, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from job_tracker.models.answers import FormField

PAGE_TIMEOUT_MS = 30_000


class FormError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# Runs in the page: the questions in the form matching `selector`, or null when the frame has no such form.
# Labels come from <label for>, aria-labelledby, or a fieldset's legend; a trailing "*" marks a required field
# on forms that don't set `required` or `aria-required`.
_READ_FIELDS = """
(selector) => {
  const form = document.querySelector(selector);
  if (!form) return null;
  const text = (el) => (el ? el.innerText || el.textContent || "" : "");
  const byIds = (ids) => (ids || "").split(/\\s+/).map((id) => text(document.getElementById(id))).join(" ");
  const labelOf = (el) => {
    if (el.labels && el.labels.length) return text(el.labels[0]);
    if (el.getAttribute("aria-labelledby")) return byIds(el.getAttribute("aria-labelledby"));
    return el.getAttribute("aria-label") || el.getAttribute("placeholder") || el.name || el.id;
  };
  const isRequired = (el, label) =>
    el.required || el.getAttribute("aria-required") === "true" || /\\*\\s*$/.test(label.trim());
  const fields = [];
  const seen = new Set();
  for (const el of form.querySelectorAll("input, select, textarea")) {
    const type = (el.getAttribute("type") || el.tagName).toLowerCase();
    if (["hidden", "submit", "button", "reset", "image"].includes(type)) continue;
    const key = el.name || el.id;
    if (!key || seen.has(key)) continue;
    seen.add(key);
    if (type === "radio" || type === "checkbox") {
      const group = [...form.querySelectorAll("input")].filter((other) => other.name === el.name);
      if (type === "radio" || group.length > 1) {
        const fieldset = el.closest("fieldset");
        const container = el.closest("[role=group], [role=radiogroup]");
        let label = fieldset ? text(fieldset.querySelector("legend")) : "";
        if (!label && container) label = byIds(container.getAttribute("aria-labelledby"));
        const groupRequired = fieldset && fieldset.getAttribute("aria-required") === "true";
        fields.push({
          key, label: label || key, kind: type,
          required: groupRequired || group.some((one) => isRequired(one, label)),
          options: group.map((one) => labelOf(one)),
          combobox: false,
        });
        continue;
      }
    }
    // A file input's own label is its "Attach" button; the question is the label of the group around it.
    const group = type === "file" ? el.closest("[role=group][aria-labelledby]") : null;
    const label = group ? byIds(group.getAttribute("aria-labelledby")) : labelOf(el);
    const combobox = el.getAttribute("role") === "combobox";
    const kind = el.tagName === "SELECT" || combobox ? "select" : el.tagName === "TEXTAREA" ? "textarea"
      : ["file", "checkbox"].includes(type) ? type : "text";
    const options = el.tagName === "SELECT" ? [...el.options].filter((o) => o.value !== "").map((o) => text(o)) : [];
    const required = isRequired(el, label) || (group !== null && group.getAttribute("aria-required") === "true");
    fields.push({ key, label, kind, required, options, combobox });
  }
  return fields;
}
"""

# Runs in the page: the options of the open dropdown `box` controls, or null while it hasn't opened yet.
_OPEN_OPTIONS = """
(box) => {
  const list = document.getElementById(box.getAttribute("aria-controls") || "");
  if (!list) return null;
  return [...list.querySelectorAll("[role=option]")].map((option) => option.innerText || option.textContent || "");
}
"""
_OPEN_TIMEOUT_MS = 3_000


def clean(text: str) -> str:
    return " ".join(text.replace("*", " ").split())


def _fields(raw: list[dict[str, Any]]) -> list[FormField]:
    return [
        FormField(
            key=field["key"],
            label=clean(field["label"]),
            kind=field["kind"],
            required=bool(field["required"]),
            options=[clean(option) for option in field["options"]],
        )
        for field in raw
    ]


def read_form(url: str, selector: str) -> list[FormField]:
    """The questions in the first form matching `selector` on the page at `url` or in one of its frames."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            frame = open_form(browser.new_page(), url, selector)
            raw = raw_fields(frame, selector)
            for field in raw:
                if field["combobox"]:
                    field["options"] = _dropdown_options(frame, field["key"])
            return _fields(raw)
        except PlaywrightError as error:
            raise FormError(f"Couldn't open the application form at {url}: {error.message}") from error
        finally:
            browser.close()


def open_form(page: Page, url: str, selector: str) -> Frame:
    """Open `url` and find the frame holding the form matching `selector`."""
    response = page.goto(url, wait_until="load", timeout=PAGE_TIMEOUT_MS)
    if response is not None and not response.ok:
        raise FormError(f"Couldn't open the application form at {url} (HTTP {response.status}).")
    for frame in page.frames:
        try:
            if frame.evaluate("(selector) => document.querySelector(selector) !== null", selector):
                return frame
        except PlaywrightError:
            continue
    raise FormError(f"Couldn't find an application form at {url}. The job may have closed.")


def raw_fields(frame: Frame, selector: str) -> list[dict[str, Any]]:
    """The form's questions as the page script reads them (custom dropdowns without their options)."""
    result: list[dict[str, Any]] = frame.evaluate(_READ_FIELDS, selector)
    return result


def open_dropdown(frame: Frame, box: Locator) -> list[str]:
    """Open a custom dropdown and return its options, as shown; [] if it didn't open."""
    box.click()
    try:
        opened = frame.wait_for_function(_OPEN_OPTIONS, arg=box.element_handle(), timeout=_OPEN_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        return []
    return [clean(option) for option in opened.json_value()]


def field_locator(frame: Frame, key: str) -> Locator:
    return frame.locator(f'[id="{key}"], [name="{key}"]').first


def _dropdown_options(frame: Frame, key: str) -> list[str]:
    """A custom dropdown's options are only in the page while it's open, so open it, read them, and close it."""
    box = field_locator(frame, key)
    try:
        return open_dropdown(frame, box)
    finally:
        box.press("Escape")
