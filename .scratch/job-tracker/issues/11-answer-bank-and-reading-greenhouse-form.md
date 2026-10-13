# 11: Answer bank and reading the form's fields (Greenhouse)

**What to build:** The review screen shows every question on the real application form, already answered where possible. I manage an answer bank in Settings for standard questions (work authorization, sponsorship, salary expectation, start date, LinkedIn/GitHub/portfolio links, EEO and demographic answers including "decline to answer"), and can add, edit and delete entries.

This introduces the Form Submitter port with a Playwright adapter for Greenhouse forms. When an application is started, it opens the job's application URL and reads the form's fields. The Answer Engine matches each question to answer-bank entries using normalized text plus fuzzy matching, so small wording differences don't cause misses, and labels each answer as "from bank" or "needs input". In review I see every question with its answer and label, and can edit any answer. "Approve and submit" is disabled while any required question still needs input.

Tests run real Playwright against local fake pages imitating a Greenhouse application form.

**Blocked by:** 09 (Apply: tailor and review screen)

**Status:** done

- [x] Answer bank entries (canonical question, answer, category including EEO) can be listed, added, updated and deleted via API and Settings
- [x] Starting an application on a Greenhouse job reads the form's fields and required flags
- [x] Each question is matched to a bank entry by normalized + fuzzy matching, and labelled "from bank" or "needs input"
- [x] Review bundle includes all form questions with answers and source labels; every answer is editable
- [x] Approval is refused by the API, and the button disabled in the UI, while any required question needs input
- [x] A local fake Greenhouse form page exists for tests
- [x] Test: a question worded differently from the bank entry is still matched
- [x] Test: approve is rejected while a required question is unanswered, and allowed once it is filled

**Notes:** Approving only checks the application is ready for now; ticket 12 makes it fill in and submit the form. The reader handles Greenhouse's React-select dropdowns (it opens each to list its options) and its grouped file uploads, checked against a live Greenhouse form. Jobs on other platforms reach review with a note that their forms aren't supported yet, and can't be approved.
