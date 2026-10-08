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
- your work modes and which job board platforms to search (Greenhouse today);
- a [Brave Search API key](https://brave.com/search/api/). It's stored only in the local database.

Each run searches the web for company job boards matching every role and location (up to 20 searches per
run), remembers the companies it finds, and fetches open postings from all of them. Block a company in the
**Companies** panel to stop fetching it and hide its jobs.

## Checks

```sh
cd backend && .venv/bin/pytest && .venv/bin/mypy
cd frontend && npm run typecheck
```
