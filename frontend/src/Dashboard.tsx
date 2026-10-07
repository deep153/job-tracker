import { useEffect, useState } from "react";
import { listJobs, startRun, type Job, type Run } from "./api";
import { PLATFORM_LABELS, companyName, fullDate, timeAgo } from "./format";

// newJobs is null when the job list before the run was unknown.
type RunOutcome = { run: Run; newJobs: number | null };

type Failure = { message: string; retry: () => void };

export function Dashboard() {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [running, setRunning] = useState(false);
  const [lastRun, setLastRun] = useState<RunOutcome | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);

  async function loadJobs() {
    setFailure(null);
    try {
      setJobs(await listJobs());
    } catch (e) {
      setFailure({ message: (e as Error).message, retry: loadJobs });
    }
  }

  useEffect(() => {
    void loadJobs();
  }, []);

  async function startRunAndRefresh() {
    setRunning(true);
    setFailure(null);
    setLastRun(null);
    try {
      const before = jobs && new Set(jobs.map((job) => job.id));
      const run = await startRun();
      const updated = await listJobs();
      setJobs(updated);
      setLastRun({ run, newJobs: before && updated.filter((job) => !before.has(job.id)).length });
    } catch (e) {
      setFailure({ message: `Run failed. ${(e as Error).message}`, retry: startRunAndRefresh });
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">
              JT
            </span>
            <span className="brand-name">Job Tracker</span>
          </div>
          <RunButton running={running} onClick={startRunAndRefresh} />
        </div>
      </header>

      <main className="content">
        <div className="page-heading">
          <div className="page-title">
            <h1>Jobs</h1>
            {jobs && jobs.length > 0 && (
              <span className="count">
                {jobs.length} {jobs.length === 1 ? "job" : "jobs"}
              </span>
            )}
          </div>
          <p className="subtitle">
            Open postings from the company boards you track. Nothing is fetched until you click Run.
          </p>
        </div>

        {failure && (
          <ErrorBanner message={failure.message} onRetry={failure.retry} onDismiss={() => setFailure(null)} />
        )}
        {running && <RunProgress />}
        {!running && lastRun && <RunSummary outcome={lastRun} />}

        {jobs === null ? (
          !failure && <JobListSkeleton />
        ) : jobs.length === 0 ? (
          <EmptyState running={running} onRun={startRunAndRefresh} />
        ) : (
          <JobList jobs={jobs} />
        )}
      </main>
    </div>
  );
}

function RunButton({ running, onClick }: { running: boolean; onClick: () => void }) {
  return (
    <button className="button button-primary" onClick={onClick} disabled={running} aria-busy={running}>
      {running ? <span className="spinner" aria-hidden="true" /> : <PlayIcon />}
      {running ? "Running…" : "Run"}
    </button>
  );
}

function RunProgress() {
  return (
    <div className="notice notice-info" role="status">
      <span className="spinner spinner-dark" aria-hidden="true" />
      Fetching the latest postings from your company boards…
    </div>
  );
}

function RunSummary({ outcome }: { outcome: RunOutcome }) {
  const { run, newJobs } = outcome;
  const finished = run.finished_at ?? run.started_at;
  return (
    <div className="notice notice-success" role="status">
      <CheckIcon />
      <span>
        Run finished <time dateTime={finished} title={fullDate(finished)}>{timeAgo(finished)}</time>
        {newJobs !== null && " · "}
        {newJobs === null ? null : newJobs === 0 ? "no new jobs" : `${newJobs} new ${newJobs === 1 ? "job" : "jobs"}`}
      </span>
    </div>
  );
}

function ErrorBanner({
  message,
  onRetry,
  onDismiss,
}: {
  message: string;
  onRetry: () => void;
  onDismiss: () => void;
}) {
  return (
    <div className="notice notice-error" role="alert">
      <AlertIcon />
      <span className="notice-text">{message}</span>
      <button className="button button-ghost" onClick={onRetry}>
        Retry
      </button>
      <button className="icon-button" onClick={onDismiss} aria-label="Dismiss">
        ×
      </button>
    </div>
  );
}

function EmptyState({ running, onRun }: { running: boolean; onRun: () => void }) {
  return (
    <section className="empty">
      <div className="empty-icon" aria-hidden="true">
        <BriefcaseIcon />
      </div>
      <h2>No jobs yet</h2>
      <p>Run a fetch to pull open postings from the company boards you track.</p>
      <button className="button button-primary" onClick={onRun} disabled={running}>
        {running ? "Running…" : "Run your first fetch"}
      </button>
    </section>
  );
}

function JobList({ jobs }: { jobs: Job[] }) {
  return (
    <ul className="job-list">
      {jobs.map((job) => (
        <JobRow key={job.id} job={job} />
      ))}
    </ul>
  );
}

function JobRow({ job }: { job: Job }) {
  const location = job.locations.join(" · ");
  return (
    <li className="job">
      <div className="job-main">
        <h3 className="job-title">{job.title}</h3>
        <div className="job-meta">
          <span className="job-company">{companyName(job.company)}</span>
          <span className="dot" aria-hidden="true" />
          <span className="badge">{PLATFORM_LABELS[job.platform]}</span>
        </div>
      </div>
      <div className="job-location">
        <PinIcon />
        <span>{location || "Location not listed"}</span>
        {job.remote && !/remote/i.test(location) && <span className="badge badge-green">Remote</span>}
      </div>
      <time className="job-updated" dateTime={job.updated_at} title={`Updated ${fullDate(job.updated_at)}`}>
        Updated {timeAgo(job.updated_at)}
      </time>
      <a className="button button-secondary job-link" href={job.posting_url} target="_blank" rel="noreferrer">
        View posting
        <ExternalIcon />
        <span className="visually-hidden">(opens in a new tab)</span>
      </a>
    </li>
  );
}

function JobListSkeleton() {
  return (
    <ul className="job-list" aria-busy="true" aria-label="Loading jobs">
      {[0, 1, 2].map((i) => (
        <li className="job" key={i}>
          <div className="job-main">
            <div className="skeleton skeleton-title" />
            <div className="skeleton skeleton-line" />
          </div>
          <div className="skeleton skeleton-line" />
          <div className="skeleton skeleton-line" />
          <div className="skeleton skeleton-button" />
        </li>
      ))}
    </ul>
  );
}

const iconProps = {
  width: 16,
  height: 16,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

function PlayIcon() {
  return (
    <svg {...iconProps}>
      <polygon points="6 4 20 12 6 20 6 4" fill="currentColor" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg {...iconProps}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function PinIcon() {
  return (
    <svg {...iconProps} width={14} height={14}>
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

function ExternalIcon() {
  return (
    <svg {...iconProps} width={14} height={14}>
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

function BriefcaseIcon() {
  return (
    <svg {...iconProps} width={28} height={28} strokeWidth={1.5}>
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  );
}
