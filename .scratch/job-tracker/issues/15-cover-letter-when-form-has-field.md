# 15: Cover letter only when the form has a field for it

**What to build:** A tailored cover letter appears in review only when the application form actually has a cover letter field. The Cover Letter Writer uses only facts from my master resume and the job description, and the prompt forbids inventing experience. I can edit the cover letter in review. On submit, it's attached or pasted according to what the form expects, and saved with the application.

**Blocked by:** 11 (Answer bank and reading the Greenhouse form)

**Status:** done

- [x] A cover letter is generated only when the form's fields include a cover letter field
- [x] The cover letter is shown and editable in review
- [x] On submit, the cover letter is uploaded as a file or pasted into a text field, depending on the form
- [x] The final cover letter is saved with the application
- [x] Fake form pages include variants with and without a cover letter field
- [x] Test: a form without a cover letter field produces no cover letter and no LLM call for one
- [x] Test: a form with a cover letter field produces one in the review bundle, and the edited version is what gets submitted

**Notes:** A cover letter field is a file, text or textarea question whose label says "cover letter"; the Lever "Additional information" box (whose placeholder mentions a cover letter) doesn't count. The letter is written with the tailoring model (cost kind "cover_letter") after the resume and answers; if writing it fails, the application fails like a tailoring failure. When the form takes a file it's also made into `cover-letter.pdf` with LibreOffice (remade on every edit) and uploaded; text boxes get the letter as it is when sending starts. The letter is kept on the application. The fake Greenhouse form has a cover letter upload, the fake Lever and Ashby forms have none, and a text-box variant is added with `fake_forms.add_to_forms()`.
