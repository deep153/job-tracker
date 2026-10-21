# 07: Tailor rewords bullets, with the code check on facts

**What to build:** When I apply to a job, the Resume Tailor may reword my marked experience bullets toward the posting's wording, where my experience backs it up. The tailoring request includes each bullet's number, label and text after the label. The answer lists only the bullets it changed. Prompt rules: reword only the text after the label, keep every number, stay within about 10% of the original length, and leaving a bullet unchanged is fine.

A fact check in code runs on every rewritten bullet. It reverts the bullet to the original, and records why, if any of these hold:
- its numbers (including percentages and "+" forms, compared as a multiset) differ from the original's;
- it names a skill from my master skills list or the job's keywords that appears in neither the original bullet nor my master skills list;
- it is more than 15% longer than the original.

The renderer replaces only the text after the label inside the existing runs, so the bold label and all formatting stay exactly as in the master. Paragraphs that weren't marked stay identical. The shorten-and-retry step passes the bullets back too, so the page count still matches the master. The tailored resume version stores the master bullets, the tailored bullets, and the reverted bullets with reasons. The review screen shows a before/after diff for each changed bullet, and marks reverted bullets with their reason. Editing comes in ticket 09.

**Blocked by:** 06 (Marking experience bullets on the Resume page)

**Status:** ready-for-agent

- [ ] The tailoring request includes the marked bullets; the answer schema accepts changed bullets by number
- [ ] The fact check reverts bullets with changed numbers, unlisted skills or more than 15% growth, and records the reason
- [ ] Rewritten bullets appear in the tailored .docx and PDF with the label run untouched and still bold
- [ ] All unmarked paragraphs in the tailored .docx are identical to the master
- [ ] Shorten-and-retry includes bullets, and the final page count equals the master's
- [ ] The review bundle includes master, tailored and reverted bullets with reasons, and older applications without bullets display as before
- [ ] The review screen shows a diff per changed bullet and marks reverted ones with their reason
- [ ] The scripted fake LLM can script bullet rewrites in tailoring answers
- [ ] Test: a scripted rewrite appears in the tailored .docx text with its label still bold, and other paragraphs are unchanged
- [ ] Test: a rewrite changing "60%" to "70%" is reverted and its reason is in the review bundle
- [ ] Test: a rewrite adding a skill that's in neither the original bullet nor the master list is reverted
- [ ] Test: the tailored PDF's page count equals the master's
