# 02: Reliable runs: de-duplication, reposts, closing, isolating failures, progress

**What to build:** Runs that only do new work and never fall over because of one board. Every company the run covers is fetched in parallel. Only new or changed postings are stored, de-duplicated by platform + external job ID, with a content hash to catch reposts under a new ID. Postings that have disappeared from a board are marked closed. A failing board is recorded on that company and in the run's errors, and the run continues. Only one run can be active at a time. While a run is going I see its progress (companies fetched, new jobs), and afterwards a summary (when, how many new jobs, errors). Past runs are listed.

Runs execute in the background: starting a run returns immediately and the dashboard follows its progress. The database is not held open across network calls.

Until discovery exists (ticket 03), the companies a run covers are put in place by the test harness; no company is hardcoded into the app.

**Blocked by:** 01 (Walking skeleton)

**Status:** done (53f10d0)

- [x] Starting a run returns immediately; the run's status and counts can be polled
- [x] Companies are fetched in parallel
- [x] A posting already seen (same platform + external ID, same content) is not stored again; its last-seen time is updated
- [x] A changed posting updates the existing job rather than creating a new one
- [x] A repost (new external ID, same content hash) is detected and not shown as a second job
- [x] Jobs missing from their board on a run are marked closed and leave the dashboard; a job that reappears is reopened
- [x] A board that errors is recorded (company last error, run errors) and the remaining companies still complete; the run itself is always recorded
- [x] Starting a run while one is active is refused with a clear message
- [x] Run status endpoint reports progress; the dashboard shows it live and shows a summary when done
- [x] Past runs can be listed
- [x] The hardcoded starter company is removed from the app
- [x] Fixtures cover new, changed, reposted and closed postings, plus a failing board
- [x] Test: after two runs where the second fixture adds one posting, only one new job is recorded for the second run
- [x] Test: a reposted posting does not create a duplicate; a removed posting is marked closed
- [x] Test: a failing board appears in run errors while other companies' jobs are stored
- [x] Test: a second concurrent run start is refused
