import { useEffect, useState } from "react";
import {
  ApiError,
  getRun,
  getSearchSettings,
  listCompanies,
  listFilteredOutJobs,
  listJobs,
  listRuns,
  startRun,
  type Company,
  type FilterRule,
  type FilteredJob,
  type Job,
  type Run,
  type SearchSettings,
} from "./api";
import { CompaniesPanel } from "./CompaniesPanel";
import { FILTER_LABELS, PLATFORM_LABELS, companyName, fullDate, timeAgo, totalFilteredOut } from "./format";
import { AlertIcon, BriefcaseIcon, CheckIcon, ExternalIcon, PinIcon, PlayIcon, SlidersIcon } from "./icons";
import { SearchSettingsPanel } from "./SearchSettingsPanel";

const POLL_INTERVAL_MS = 700;

type Failure = { message: string; retry: () => void };

type View = "matches" | "filtered";

export function Dashboard() {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [filtered, setFiltered] = useState<FilteredJob[] | null>(null);
  const [view, setView] = useState<View>("matches");
  const [run, setRun] = useState<Run | null>(null);
  const [settings, setSettings] = useState<SearchSettings | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [starting, setStarting] = useState(false);
  const [failure, setFailure] = useState<Failure | null>(null);
  const running = starting || run?.status === "running";
  const ready = settings?.ready ?? false;
  const showTabs = jobs !== null && filtered !== null && (jobs.length > 0 || filtered.length > 0);

  async function load<T>(fetch: () => Promise<T>, apply: (value: T) => void) {
    try {
      apply(await fetch());
    } catch (e) {
      setFailure({ message: (e as Error).message, retry: loadAll });
    }
  }

  const loadJobs = () => Promise.all([load(listJobs, setJobs), load(listFilteredOutJobs, setFiltered)]);
  const loadCompanies = () => load(listCompanies, setCompanies);

  async function loadAll() {
    setFailure(null);
    await Promise.all([
      loadJobs(),
      loadCompanies(),
      load(getSearchSettings, setSettings),
      load(listRuns, ([latest]) => setRun(latest ?? null)),
    ]);
  }

  useEffect(() => {
    void loadAll();
  }, []);

  useEffect(() => {
    if (run?.status !== "running") return;
    const timer = setTimeout(async () => {
      try {
        const next = await getRun(run.id);
        if (next.companies_fetched !== run.companies_fetched || next.status !== "running") {
          void loadJobs();
        }
        if (next.stage !== run.stage || next.status !== "running") {
          void loadCompanies();
        }
        setRun(next);
      } catch (e) {
        setFailure({ message: (e as Error).message, retry: loadAll });
      }
    }, POLL_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [run]);

  async function startRunAndFollow() {
    setStarting(true);
    setFailure(null);
    try {
      setRun(await startRun());
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        await load(listRuns, ([latest]) => setRun(latest ?? null));
      } else if (e instanceof ApiError && e.status === 400) {
        await load(getSearchSettings, setSettings);
      } else {
        setFailure({ message: `Couldn't start the run. ${(e as Error).message}`, retry: startRunAndFollow });
      }
    } finally {
      setStarting(false);
    }
  }

  function updateCompany(updated: Company) {
    setCompanies((current) => current.map((c) => (c.id === updated.id ? updated : c)));
    void loadJobs();
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
          <RunButton running={running} ready={ready} onClick={startRunAndFollow} />
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          {settings ? (
            <SearchSettingsPanel
              settings={settings}
              disabled={running}
              onChange={(next) => {
                setSettings(next);
                void loadJobs();
              }}
            />
          ) : (
            !failure && <PanelSkeleton />
          )}
          {settings && <CompaniesPanel companies={companies} onChange={updateCompany} />}
        </aside>

        <main className="content">
          <div className="page-heading">
            <div className="page-title">
              <h1>Jobs</h1>
            </div>
            <p className="subtitle">
              Open postings from companies found with your search settings that pass your filters. Nothing is fetched
              until you click Run.
            </p>
          </div>

          {failure && (
            <ErrorBanner message={failure.message} onRetry={failure.retry} onDismiss={() => setFailure(null)} />
          )}
          {settings && !settings.ready && !running && <SetupNotice missing={settings.missing} />}
          {run?.status === "running" && <RunProgress run={run} />}
          {run && run.status !== "running" && <RunSummary run={run} onReview={() => setView("filtered")} />}

          {showTabs && jobs && filtered && (
            <ViewTabs view={view} matches={jobs.length} filteredOut={filtered.length} onChange={setView} />
          )}
          <div
            role={showTabs ? "tabpanel" : undefined}
            id="jobs-panel"
            aria-labelledby={showTabs ? `tab-${view}` : undefined}
          >
            {jobs === null || filtered === null ? (
              !failure && <JobListSkeleton />
            ) : view === "filtered" ? (
              filtered.length === 0 ? (
                <FilteredEmptyState />
              ) : (
                <JobList jobs={filtered} />
              )
            ) : jobs.length === 0 ? (
              <EmptyState
                running={running}
                ready={ready}
                hasRun={run !== null}
                filteredOut={filtered.length}
                onRun={startRunAndFollow}
                onReview={() => setView("filtered")}
              />
            ) : (
              <JobList jobs={jobs} />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

function RunButton({ running, ready, onClick }: { running: boolean; ready: boolean; onClick: () => void }) {
  return (
    <button
      className="button button-primary"
      onClick={onClick}
      disabled={running || !ready}
      aria-busy={running}
      title={!ready && !running ? "Finish your search settings to run." : undefined}
    >
      {running ? <span className="spinner" aria-hidden="true" /> : <PlayIcon />}
      {running ? "Running…" : "Run"}
    </button>
  );
}

function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

function formatSalary(salary: NonNullable<Job["salary"]>): string {
  const money = (n: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: salary.currency ?? "USD",
      notation: "compact",
      maximumFractionDigits: 0,
    }).format(n);
  const { min, max } = salary;
  if (min !== null && max !== null && min !== max) return `${money(min)}–${money(max)}`;
  return money((max ?? min) as number);
}

function SetupNotice({ missing }: { missing: string[] }) {
  return (
    <div className="notice notice-info notice-stacked" role="status">
      <div className="notice-row">
        <SlidersIcon />
        <span className="notice-text">Finish your search settings to run:</span>
      </div>
      <ul className="notice-list">
        {missing.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function RunProgress({ run }: { run: Run }) {
  if (run.stage === "discovering") {
    return (
      <div className="notice notice-info notice-stacked" role="status">
        <div className="notice-row">
          <span className="spinner spinner-dark" aria-hidden="true" />
          <span className="notice-text">Searching for companies that match your settings…</span>
        </div>
        <div className="progress progress-indeterminate" role="progressbar" aria-label="Searching">
          <div className="progress-bar" />
        </div>
      </div>
    );
  }
  const percent = run.companies_total === 0 ? 0 : (run.companies_fetched / run.companies_total) * 100;
  return (
    <div className="notice notice-info notice-stacked" role="status">
      <div className="notice-row">
        <span className="spinner spinner-dark" aria-hidden="true" />
        <span className="notice-text">
          Fetching boards: {run.companies_fetched} of {plural(run.companies_total, "company", "companies")}
          {run.new_jobs > 0 && ` · ${plural(run.new_jobs, "new job")} so far`}
          {totalFilteredOut(run.filtered_out) > 0 && ` · ${totalFilteredOut(run.filtered_out)} filtered out`}
        </span>
      </div>
      <div
        className="progress"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={run.companies_total}
        aria-valuenow={run.companies_fetched}
      >
        <div className="progress-bar" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function RunSummary({ run, onReview }: { run: Run; onReview: () => void }) {
  const finished = run.finished_at ?? run.started_at;
  const when = (
    <time dateTime={finished} title={fullDate(finished)}>
      {timeAgo(finished)}
    </time>
  );

  if (run.status === "failed" || run.status === "interrupted") {
    return (
      <div className="notice notice-error" role="status">
        <AlertIcon />
        <span className="notice-text">
          {run.status === "failed"
            ? "The last run stopped unexpectedly"
            : "The last run was interrupted because the server stopped"}{" "}
          {when}. Jobs fetched before that were kept; click Run to try again.
        </span>
      </div>
    );
  }

  const searchErrors = run.errors.filter((e) => e.kind === "search");
  const boardErrors = run.errors.filter((e) => e.kind === "board");
  const changes = [
    run.companies_discovered > 0 && plural(run.companies_discovered, "new company", "new companies"),
    `${plural(run.companies_total, "company", "companies")} checked`,
    run.new_jobs === 0 ? "no new jobs" : plural(run.new_jobs, "new job"),
    run.updated_jobs > 0 && `${run.updated_jobs} updated`,
    run.closed_jobs > 0 && `${run.closed_jobs} closed`,
  ].filter(Boolean);
  const filteredOut = totalFilteredOut(run.filtered_out);
  const byRule = (Object.entries(run.filtered_out) as [FilterRule, number][]).filter(([, count]) => count > 0);

  return (
    <>
      <div className="notice notice-success" role="status">
        <CheckIcon />
        <span className="notice-text">
          Run finished {when} · {changes.join(" · ")}
        </span>
      </div>
      {filteredOut > 0 && (
        <div className="notice notice-muted filter-summary" role="status">
          <span className="notice-text">
            <strong>{filteredOut} filtered out</strong> of the new and changed jobs:
            <span className="filter-counts">
              {byRule.map(([rule, count]) => (
                <span className="badge" key={rule}>
                  {FILTER_LABELS[rule]} <strong>{count}</strong>
                </span>
              ))}
            </span>
          </span>
          <button type="button" className="button button-ghost" onClick={onReview}>
            Review
          </button>
        </div>
      )}
      {searchErrors.map((error) => (
        <div className="notice notice-warning" role="status" key={error.message}>
          <AlertIcon />
          <span className="notice-text">
            Couldn't search for new companies. {error.message} Companies found earlier were still checked.
          </span>
        </div>
      ))}
      {run.search_queries_capped && (
        <div className="notice notice-muted" role="status">
          <span className="notice-text">
            Only the first {run.search_queries} role and location combinations were searched this run. Remove some
            roles or locations to cover them all.
          </span>
        </div>
      )}
      {boardErrors.length > 0 && (
        <div className="notice notice-warning notice-stacked" role="status">
          <div className="notice-row">
            <AlertIcon />
            <span className="notice-text">
              {plural(boardErrors.length, "board")} couldn't be fetched. The rest of the run completed normally.
            </span>
          </div>
          <ul className="board-errors">
            {boardErrors.map((error) => (
              <li key={`${error.platform}/${error.board_id}`}>
                <strong>{companyName(error.board_id)}</strong>{" "}
                <span className="badge">{PLATFORM_LABELS[error.platform]}</span> {error.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
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

function ViewTabs({
  view,
  matches,
  filteredOut,
  onChange,
}: {
  view: View;
  matches: number;
  filteredOut: number;
  onChange: (view: View) => void;
}) {
  const tabs: { id: View; label: string; count: number }[] = [
    { id: "matches", label: "Matches", count: matches },
    { id: "filtered", label: "Filtered out", count: filteredOut },
  ];
  return (
    <div className="view-tabs" role="tablist" aria-label="Jobs">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          id={`tab-${tab.id}`}
          aria-selected={view === tab.id}
          aria-controls="jobs-panel"
          className="view-tab"
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
          <span className="view-tab-count">{tab.count}</span>
        </button>
      ))}
    </div>
  );
}

function FilteredEmptyState() {
  return (
    <section className="empty">
      <div className="empty-icon" aria-hidden="true">
        <SlidersIcon size={28} />
      </div>
      <h2>Nothing filtered out</h2>
      <p>Jobs that don't fit your search settings or filters show up here, each with the reason it was dropped.</p>
    </section>
  );
}

function EmptyState({
  running,
  ready,
  hasRun,
  filteredOut,
  onRun,
  onReview,
}: {
  running: boolean;
  ready: boolean;
  hasRun: boolean;
  filteredOut: number;
  onRun: () => void;
  onReview: () => void;
}) {
  if (!ready) {
    return (
      <section className="empty">
        <div className="empty-icon" aria-hidden="true">
          <SlidersIcon size={28} />
        </div>
        <h2>Set up your search</h2>
        <p>
          Add the roles and locations you want, pick your job boards, and add a search API key. Job Tracker then finds
          matching companies and their open jobs for you.
        </p>
      </section>
    );
  }
  if (filteredOut > 0) {
    return (
      <section className="empty">
        <div className="empty-icon" aria-hidden="true">
          <SlidersIcon size={28} />
        </div>
        <h2>No jobs pass your filters</h2>
        <p>
          {plural(filteredOut, "open job was", "open jobs were")} filtered out. Review them to see whether a filter is
          too strict.
        </p>
        <button className="button button-secondary" onClick={onReview}>
          Review filtered jobs
        </button>
      </section>
    );
  }
  if (hasRun) {
    return (
      <section className="empty">
        <div className="empty-icon" aria-hidden="true">
          <BriefcaseIcon />
        </div>
        <h2>No open jobs right now</h2>
        <p>None of the companies you track have open postings. Run again later, or broaden your search settings.</p>
      </section>
    );
  }
  return (
    <section className="empty">
      <div className="empty-icon" aria-hidden="true">
        <BriefcaseIcon />
      </div>
      <h2>No jobs yet</h2>
      <p>Run a search to find companies hiring for your roles and pull in their open postings.</p>
      <button className="button button-primary" onClick={onRun} disabled={running}>
        {running ? "Running…" : "Run your first search"}
      </button>
    </section>
  );
}

function JobList({ jobs }: { jobs: (Job | FilteredJob)[] }) {
  return (
    <ul className="job-list">
      {jobs.map((job) => (
        <JobRow key={job.id} job={job} />
      ))}
    </ul>
  );
}

function JobRow({ job }: { job: Job | FilteredJob }) {
  const location = job.locations.join(" · ");
  const rejection = "rejection" in job ? job.rejection : null;
  return (
    <li className={`job${rejection ? " is-filtered" : ""}`}>
      <div className="job-main">
        <h3 className="job-title">{job.title}</h3>
        <div className="job-meta">
          <span className="job-company">{companyName(job.company)}</span>
          <span className="dot" aria-hidden="true" />
          <span className="badge">{PLATFORM_LABELS[job.platform]}</span>
          {job.salary && <span className="badge badge-green">{formatSalary(job.salary)}</span>}
        </div>
        {rejection && (
          <p className="job-rejection">
            <span className="badge badge-warning">{FILTER_LABELS[rejection.rule]}</span>
            {rejection.reason}
          </p>
        )}
      </div>
      <div className="job-location">
        <PinIcon />
        <span>{location || "Location not listed"}</span>
        {job.work_mode === "hybrid"
          ? !/hybrid/i.test(location) && <span className="badge">Hybrid</span>
          : (job.remote || job.work_mode === "remote") &&
            !/remote/i.test(location) && <span className="badge badge-green">Remote</span>}
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

function PanelSkeleton() {
  return (
    <section className="panel" aria-busy="true" aria-label="Loading search settings">
      <div className="panel-body">
        <div className="skeleton skeleton-title" />
        <div className="skeleton skeleton-line" />
        <div className="skeleton skeleton-line" />
      </div>
    </section>
  );
}
