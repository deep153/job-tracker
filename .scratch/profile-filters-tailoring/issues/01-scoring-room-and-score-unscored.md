# 01: Scoring has room to finish, plus "Score N unscored jobs"

**What to build:** Every job that passes the filters gets a score, including long postings. The Fit Scorer's output limit rises from 1,000 to 3,000 tokens, and its system prompt states the caps: at most 5 reasons, 15 matched keywords and 15 missing keywords. When some jobs still have no score (from earlier failures, or my first run's 26), the dashboard shows "Score N unscored jobs". Clicking it starts a scoring-only run: no discovery and no board fetching, just scoring the jobs a full run's scoring stage would pick (open, visible, passed the filters, no score for the current resume version and content). It uses the same lock, progress, error reporting and cost recording as a full run, and appears in run history labelled as scoring only.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] The Fit Scorer's output limit is 3,000 tokens and its prompt states the 5/15/15 caps
- [x] Runs have a kind, full or scoring-only; existing runs read as full
- [x] Starting a scoring-only run scores exactly the unscored jobs and makes no search or job-board calls
- [x] A scoring-only run is refused while another run is active, and a full run is refused while a scoring-only run is active
- [x] Scoring errors, progress counts and AI cost are recorded on a scoring-only run as they are on a full run
- [x] The dashboard data includes the number of unscored jobs
- [x] The dashboard shows "Score N unscored jobs" only when N > 0 and no run is active; progress shows through the existing run polling
- [x] Run history labels scoring-only runs
- [x] Test: a run where the fake LLM fails some titles with "cut off" leaves them unscored; a scoring-only run then scores exactly those and calls neither search nor the boards
- [x] Test: starting a scoring-only run during an active run is refused
