# 08: Browsing the dashboard and acting on jobs

**What to build:** The dashboard becomes comfortable to work through. I can filter and sort matches by company, location, posted date and score. I can open a job to read its full description inside the dashboard, and follow a link to the original posting. I can dismiss jobs I'm not interested in so they stop appearing. Scored jobs I haven't acted on stay visible across runs until I dismiss them or they close. After updating my resume, I can re-score a single job on demand so its score reflects my current profile.

**Blocked by:** 07 (Fit Scorer and matches dashboard)

**Status:** done (ca10bd1)

- [x] Jobs list supports filtering by company, location and posted date, and sorting by score and posted date
- [x] Job detail shows the full description, score, reasons, matched/missing keywords and a link to the original posting
- [x] Dismissing a job removes it from the dashboard permanently, including after later runs
- [x] Unacted matched jobs remain on the dashboard across runs until dismissed or closed
- [x] Re-scoring a job calls the LLM once against the current master resume version and replaces the displayed score
- [x] Test: a dismissed job does not reappear after another run
- [x] Test: a matched job from run 1 is still listed after run 2 if it is still open
- [x] Test: re-scoring after replacing the master resume stores a score tied to the new resume version

"Posted date" is the posting's last-updated date, the only date the job boards give; the dashboard labels it "Updated".
