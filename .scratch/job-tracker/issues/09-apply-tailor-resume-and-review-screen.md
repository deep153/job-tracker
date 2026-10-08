# 09: Apply: tailor the resume and open the review screen

**What to build:** I click "Apply" on a job and get a tailored resume to review. An application is created in `drafting`. The Resume Tailor asks Claude (the tailoring model) for a structured edit: a new summary reflecting the job's main requirements, and an ordered skills list with the most relevant first. Job-description keywords may be added to skills only if they're in my master skills list; this is enforced in code, not only in the prompt. Every tailoring prompt says never to invent experience, employers, dates, metrics or skills.

The Resume Renderer writes the edits into a copy of the master .docx by replacing text inside the existing formatting segments of the mapped Summary and Skills paragraphs, so fonts, styles and layout are preserved and nothing else changes. It converts to PDF with LibreOffice and checks the page count equals the master's; if it grew, the Tailor is asked to shorten and the render is retried once. Keyword coverage is computed before and after tailoring. The tailored .docx and PDF are saved as a resume version linked to the job.

The application then moves to `in_review`, and I land on a review screen showing a side-by-side diff of master vs tailored summary and skills, a preview of the tailored PDF, keyword coverage before/after, and a Cancel button that discards the application without sending anything. The tailoring's approximate AI cost is recorded and shown.

**Blocked by:** 07 (Fit Scorer and matches dashboard)

**Status:** ready-for-agent

- [ ] "Apply" on a job creates an application in `drafting`, then moves it to `in_review` once tailoring completes
- [ ] Only the mapped Summary and Skills paragraphs change; all other text in the tailored .docx is identical to the master
- [ ] Original formatting segments (fonts, styles) of the edited paragraphs are preserved
- [ ] Any skill returned by the LLM that is not in the master skills list is removed in code
- [ ] Tailored PDF page count equals the master's; if not, one shorten-and-retry happens; if it still fails, the error is surfaced clearly
- [ ] Keyword coverage before and after is stored and shown
- [ ] Tailored .docx and PDF are both kept and linked to the job via a resume version
- [ ] Review screen shows the summary/skills diff, PDF preview and coverage numbers
- [ ] Cancelling in review discards the application; nothing is submitted
- [ ] Tailoring cost is recorded and included in the Settings cost summary
- [ ] Tests use real python-docx and LibreOffice with a scripted fake LLM
- [ ] Test: the tailored PDF has the same page count as the master and its text contains only master-list skills, even when the fake LLM returns a skill not in the list
- [ ] Test: a fake LLM summary too long to fit triggers the shorten-and-retry and ends at the master's page count
