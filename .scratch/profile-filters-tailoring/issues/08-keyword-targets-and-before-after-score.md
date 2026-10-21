# 08: Tailoring targets the scorer's keywords, with a before/after fit score

**What to build:** Tailoring aims at what actually lowers my score, and I can see whether it helped. The tailoring request includes target keywords: the job's latest Fit Scorer matched and missing keywords. If the job has no score yet, the tailor picks keywords itself as before. The tailoring answer adds gaps: target keywords it couldn't cover honestly. After rendering, the tailored text is scored by the Fit Scorer (scoring model), and the tailored resume version stores the before score (the job's latest score) and the after score.

Keyword coverage uses the target keywords, matched loosely: case- and punctuation-insensitive, with simple plural folding, and a skill with a parenthetical (such as "Observability (Grafana, Kibana)") counts for the term before the parenthesis. The review screen shows the fit score before and after, next to coverage. The gaps are stored and returned in the review bundle; their UI comes in ticket 10. The re-score's AI cost is recorded against the application.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The tailoring request includes the scorer's matched and missing keywords when the job has a score
- [ ] The tailoring answer schema includes gaps, and they're stored on the tailored resume version
- [ ] The tailored resume is re-scored after rendering; before and after scores are stored and returned in the review bundle
- [ ] Coverage before and after uses the target keywords with loose matching
- [ ] The re-score's cost is recorded as AI usage and added to the application's cost
- [ ] The review screen shows the before and after fit scores
- [ ] Applications tailored before this change display without scores or gaps
- [ ] The scripted fake LLM can script gaps in tailoring answers and a score for the tailored resume
- [ ] Test: after applying to a scored job, the review bundle has before and after scores and the scripted gaps
- [ ] Test: a resume line "Observability (Grafana, Kibana)" counts as covering the keyword "Observability", and "APIs" covers "API"
