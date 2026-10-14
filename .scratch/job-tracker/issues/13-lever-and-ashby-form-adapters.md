# 13: Lever and Ashby form adapters

**What to build:** I can apply to Lever and Ashby jobs exactly as I can to Greenhouse ones. Each platform gets its own Form Submitter adapter that reads the form's fields before review, then fills, uploads, submits and detects confirmation after approval, with the same hand-over to me on CAPTCHA or unknown required fields.

**Blocked by:** 12 (Submitting to Greenhouse)

**Status:** done

- [x] Lever adapter reads fields, fills, uploads the PDF, submits and detects confirmation
- [x] Ashby adapter reads fields, fills, uploads the PDF, submits and detects confirmation
- [x] Both hand over (`needs_manual`) on CAPTCHA or unrecognized required fields, and record failures with reason and screenshot
- [x] Local fake Lever and Ashby form pages exist, including CAPTCHA and unknown-question variants
- [x] Test (per platform): approving against the normal fake form ends in `submitted`
- [x] Test (per platform): the CAPTCHA variant ends in `needs_manual`

**Notes:** Each platform is a `FormLayout` (where the form, its submit button and each question's label are) over the shared Playwright reading and filling. The fake pages are trimmed from real ones (a Lever `/apply` page and a rendered Ashby application, October 2026): Lever labels questions with `.application-label` and marks required ones with "✱", keeps a hidden upload-size `.error-message` in the page, and submits from a `type=button`; Ashby has no `<form>`, renders after load, marks required questions only by a class on the label, and asks Yes/No questions with toggle buttons (read as a two-option radio). Not handled yet: Ashby's location autocomplete and date picker have no name or id, so they're not read; a required one makes Ashby refuse the submission, which ends in `failed` with its message and a screenshot.
