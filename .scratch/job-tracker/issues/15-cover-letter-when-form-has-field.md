# 15: Cover letter only when the form has a field for it

**What to build:** A tailored cover letter appears in review only when the application form actually has a cover letter field. The Cover Letter Writer uses only facts from my master resume and the job description, and the prompt forbids inventing experience. I can edit the cover letter in review. On submit, it's attached or pasted according to what the form expects, and saved with the application.

**Blocked by:** 11 (Answer bank and reading the Greenhouse form)

**Status:** ready-for-agent

- [ ] A cover letter is generated only when the form's fields include a cover letter field
- [ ] The cover letter is shown and editable in review
- [ ] On submit, the cover letter is uploaded as a file or pasted into a text field, depending on the form
- [ ] The final cover letter is saved with the application
- [ ] Fake form pages include variants with and without a cover letter field
- [ ] Test: a form without a cover letter field produces no cover letter and no LLM call for one
- [ ] Test: a form with a cover letter field produces one in the review bundle, and the edited version is what gets submitted
