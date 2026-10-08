# Job Tracker

A local, single-user dashboard for on-demand job matching and tailored applications.

## Running

Backend (FastAPI, http://127.0.0.1:8000). Data is stored in `~/.job-tracker/job-tracker.db` unless `JOB_TRACKER_DB` is set:

```sh
cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn job_tracker.app:default_app --factory
```

Frontend (React + Vite, http://localhost:5173, proxies `/api` to the backend):

```sh
cd frontend && npm install && npm run dev
```

Nothing is fetched until you click **Run**.

## First run

Open **Search settings** on the dashboard and add:

- the roles you want (e.g. "Backend Engineer") and your locations, or choose Remote;
- your work modes and which job board platforms to search (Greenhouse, Lever and Ashby);
- a [Brave Search API key](https://brave.com/search/api/). It's stored only in the local database.

Each run searches the web for company job boards matching every role and location (up to 20 searches per
run), remembers the companies it finds, and fetches open postings from all of them. Block a company in the
**Companies** panel to stop fetching it and hide its jobs.

Jobs that don't fit are filtered out before anything else happens to them: titles must match a role, the
location and work mode must match yours, and the optional **More filters** (excluded title keywords,
seniority, years of experience, visa sponsorship, minimum salary) drop the rest. The **Filtered out** tab
lists every dropped job with the reason, and changing settings re-filters stored jobs without fetching again.

## Resume

On the **Resume** page, upload your resume as a Word `.docx`. Check the PDF preview, mark which paragraphs
are your Summary and which are your Skills section, and save. Your master skills list is filled in from the Skills
section; edit it so it holds every skill you have, because tailoring can only use skills from this list. Uploading a
newer resume creates a new version (earlier versions are kept) that you mark the same way. Resume files are
stored next to the database, in `~/.job-tracker/files/`.

## Checks

```sh
cd backend && .venv/bin/pytest && .venv/bin/mypy
cd frontend && npm run typecheck
```
