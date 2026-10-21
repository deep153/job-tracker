# 10: Gaps list with "Add to my skills"

**What to build:** The review screen lists the gaps: the job's keywords the tailor couldn't honestly cover. Each gap has "Add to my skills" and a picker for which Skills line it goes on, with the best guess preselected from the line labels. Adding a gap saves it to my master skills list (so future applications can use it), places it on the chosen line of this application's resume, rebuilds the .docx and PDF, recomputes coverage and re-scores. There's no tailoring call. If adding it would push the resume past the master's page count, it's refused with a clear message, and neither the master list nor the resume changes.

**Blocked by:** 08 (Tailoring targets the scorer's keywords, with a before/after fit score)

**Status:** ready-for-agent

- [ ] The review screen shows the gaps list, each with "Add to my skills" and a Skills line picker
- [ ] The add-gap endpoint takes the keyword and the target Skills line
- [ ] Adding a gap adds it to the master skills list and to the chosen line of this resume, then rebuilds the files, recomputes coverage and re-scores
- [ ] No tailoring call is made
- [ ] An add that would exceed the master's page count is refused, and nothing changes
- [ ] The added gap leaves the gaps list
- [ ] Test: adding a gap puts it on the chosen Skills line in the PDF text, adds it to the master skills list, and makes no tailoring call
- [ ] Test: a later application can use the added skill on its Skills line
