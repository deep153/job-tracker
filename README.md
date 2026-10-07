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

## Checks

```sh
cd backend && .venv/bin/pytest && .venv/bin/mypy
cd frontend && npm run typecheck
```
