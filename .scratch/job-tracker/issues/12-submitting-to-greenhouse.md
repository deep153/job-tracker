# 12: Submitting to Greenhouse

**What to build:** After I click "Approve and submit", the application is sent by filling the company's public Greenhouse form in a visible browser I can watch. The application moves to `submitting`; the form is filled with my reviewed answers, the tailored PDF is uploaded as the resume, and the form is submitted. The confirmation page is detected and the application is recorded as `submitted`. If a CAPTCHA or an unrecognized required field appears, the browser stays open, control is handed to me, and the application becomes `needs_manual`. Any other failure is recorded as `failed` with the reason and a screenshot so I can retry or apply by hand. A job can have at most one application past `in_review`, so I can never submit twice to the same job.

**Blocked by:** 11 (Answer bank and reading the Greenhouse form)

**Status:** done

- [x] Approving moves the application through `submitting` to `submitted`, `needs_manual` or `failed`
- [x] The browser runs visibly; the tailored PDF is uploaded and reviewed answers are filled exactly as approved
- [x] Confirmation is detected and the submitted time is recorded
- [x] CAPTCHA or an unrecognized required field leaves the browser open and ends in `needs_manual`
- [x] Failures record a reason and a screenshot, viewable from the application
- [x] Starting or submitting a second application for a job that already has one past `in_review` is refused
- [x] Fake Greenhouse pages include a normal form, a CAPTCHA placeholder variant, and an unknown-required-question variant
- [x] Test: approving against the normal fake form ends in `submitted` and the fake page received the PDF and answers
- [x] Test: a CAPTCHA form ends in `needs_manual`
- [x] Test: a form that errors on submit ends in `failed` with a reason and screenshot
- [x] Test: submitting the same job twice is refused

**Notes:** Tests run the browser headless (`create_app(visible_browser=False)`); the app shows it. A handover in a visible browser waits until I close the window, and records `submitted` if the confirmation appears while I finish. A submission interrupted by a server restart becomes `needs_manual`, never retried, so nothing is sent twice. Fake form variants are query parameters on the one fixture (`?captcha`, `?fail`) plus `fake_forms.add_to_forms()` for a question added after review.
