# 01: Walking skeleton: Run fetches Greenhouse jobs into the dashboard

**What to build:** The thinnest end-to-end path through the whole stack. I open the local dashboard, click "Run", and the app fetches open postings from one Greenhouse company board and lists them on the dashboard (no filtering or scoring yet). This sets up the single-user local web app (Python FastAPI backend, React + Vite frontend, SQLite storage, no auth, no scheduler) and the testing pattern every later ticket follows: tests drive the backend HTTP API, with a temporary SQLite database per test and a fake HTTP layer serving recorded Greenhouse fixtures.

The Job Board Source port is introduced here: given a company board ID, return a list of normalized postings (source platform, company board ID, external job ID, title, location(s), remote flag if known, salary range if given, description text, posting URL, application URL, posted/updated timestamp). Greenhouse is the first adapter, using the public read-only job-board API.

**Blocked by:** None (can start immediately)

**Status:** done (b7e5488)

- [x] Backend and frontend start locally with one documented command each; nothing runs until I click "Run"
- [x] A companies table exists with at least one seeded Greenhouse company
- [x] Clicking "Run" starts a run via the HTTP API; the run is recorded with start and finish times
- [x] Greenhouse postings are normalized into the shared posting shape and stored as jobs
- [x] The dashboard lists stored jobs with title, company, location and a link to the original posting
- [x] API-level test harness exists: temp SQLite per test, fake HTTP layer serving recorded Greenhouse fixtures
- [x] Test: a run against the Greenhouse fixture stores the expected jobs and the jobs list endpoint returns them
