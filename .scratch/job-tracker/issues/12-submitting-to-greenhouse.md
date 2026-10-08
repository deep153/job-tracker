# 12: Submitting to Greenhouse

**What to build:** After I click "Approve and submit", the application is sent by filling the company's public Greenhouse form in a visible browser I can watch. The application moves to `submitting`; the form is filled with my reviewed answers, the tailored PDF is uploaded as the resume, and the form is submitted. The confirmation page is detected and the application is recorded as `submitted`. If a CAPTCHA or an unrecognized required field appears, the browser stays open, control is handed to me, and the application becomes `needs_manual`. Any other failure is recorded as `failed` with the reason and a screenshot so I can retry or apply by hand. A job can have at most one application past `in_review`, so I can never submit twice to the same job.

**Blocked by:** 11 (Answer bank and reading the Greenhouse form)

**Status:** ready-for-agent

- [ ] Approving moves the application through `submitting` to `submitted`, `needs_manual` or `failed`
- [ ] The browser runs visibly; the tailored PDF is uploaded and reviewed answers are filled exactly as approved
- [ ] Confirmation is detected and the submitted time is recorded
- [ ] CAPTCHA or an unrecognized required field leaves the browser open and ends in `needs_manual`
- [ ] Failures record a reason and a screenshot, viewable from the application
- [ ] Starting or submitting a second application for a job that already has one past `in_review` is refused
- [ ] Fake Greenhouse pages include a normal form, a CAPTCHA placeholder variant, and an unknown-required-question variant
- [ ] Test: approving against the normal fake form ends in `submitted` and the fake page received the PDF and answers
- [ ] Test: a CAPTCHA form ends in `needs_manual`
- [ ] Test: a form that errors on submit ends in `failed` with a reason and screenshot
- [ ] Test: submitting the same job twice is refused
