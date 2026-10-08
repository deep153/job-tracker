# 13: Lever and Ashby form adapters

**What to build:** I can apply to Lever and Ashby jobs exactly as I can to Greenhouse ones. Each platform gets its own Form Submitter adapter that reads the form's fields before review, then fills, uploads, submits and detects confirmation after approval, with the same hand-over to me on CAPTCHA or unknown required fields.

**Blocked by:** 12 (Submitting to Greenhouse)

**Status:** ready-for-agent

- [ ] Lever adapter reads fields, fills, uploads the PDF, submits and detects confirmation
- [ ] Ashby adapter reads fields, fills, uploads the PDF, submits and detects confirmation
- [ ] Both hand over (`needs_manual`) on CAPTCHA or unrecognized required fields, and record failures with reason and screenshot
- [ ] Local fake Lever and Ashby form pages exist, including CAPTCHA and unknown-question variants
- [ ] Test (per platform): approving against the normal fake form ends in `submitted`
- [ ] Test (per platform): the CAPTCHA variant ends in `needs_manual`
