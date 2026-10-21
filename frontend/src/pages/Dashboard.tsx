import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { listCompanies } from "../api/companies";
import { dismissJob, listFilteredOutJobs, listJobs, listJobsBelowThreshold } from "../api/jobs";
import { getRun, getUnscoredCount, listRuns, startRun, startScoringRun } from "../api/runs";
import { getSearchSettings } from "../api/searchSettings";
import { CompaniesPanel } from "../components/CompaniesPanel";
import { AlertIcon, BriefcaseIcon, CheckIcon, ExternalIcon, PinIcon, PlayIcon, SlidersIcon } from "../components/icons";
import { JobDetail } from "../components/JobDetail";
import { JobFilters, NO_FILTERS, hasFilters } from "../components/JobFilters";
import { ScoreBadge, ScoreDetails } from "../components/Score";
import { SearchSettingsPanel } from "../components/SearchSettingsPanel";
import { Topbar } from "../components/Topbar";
import { APPLICATION_LABELS } from "../types/application";
import type { Company } from "../types/company";
import type { FilterRule, FilteredJob, Job, JobQuery } from "../types/job";
import type { Run } from "../types/run";
import type { SearchSettings } from "../types/searchSettings";
import {
  FILTER_LABELS,
  PLATFORM_LABELS,
  companyName,
  formatCost,
  formatSalary,
  fullDate,
  timeAgo,
  nearMisses,
} from "../utils/format";

const POLL_INTERVAL_MS = 700;
const LOCATION_DEBOUNCE_MS = 300;

type Failure = { message: string; retry: () => void };

type View = "matches" | "below" | "filtered";

export function Dashboard() {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [below, setBelow] = useState<Job[] | null>(null);
  const [filtered, setFiltered] = useState<FilteredJob[] | null>(null);
  const [view, setView] = useState<View>("matches");
  const [run, setRun] = useState<Run | null>(null);
  const [unscored, setUnscored] = useState(0);
  const [settings, setSettings] = useState<SearchSettings | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [starting, setStarting] = useState(false);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [query, setQuery] = useState<JobQuery>(NO_FILTERS);
  const [appliedQuery, setAppliedQuery] = useState<JobQuery>(NO_FILTERS);
  const appliedQueryRef = useRef(appliedQuery);
  appliedQueryRef.current = appliedQuery;
  const jobsRequest = useRef(0);
  const queryApplied = useRef(false);
  const [selected, setSelected] = useState<Job | FilteredJob | null>(null);
  const [dismissed, setDismissed] = useState<string | null>(null);
  const running = starting || run?.status === "running";
  const ready = settings?.ready ?? false;
  const loaded = jobs !== null && below !== null && filtered !== null;
  const filtering = hasFilters(appliedQuery);
  const showTabs = loaded && (jobs.length > 0 || below.length > 0 || filtered.length > 0 || filtering);

  async function load<T>(fetch: () => Promise<T>, apply: (value: T) => void) {
    try {
      apply(await fetch());
    } catch (e) {
      setFailure({ message: (e as Error).message, retry: loadAll });
    }
  }

  /** Only the latest request's lists are shown, so a slow answer for old filters can't replace a newer one. */
  async function loadJobs() {
    const request = ++jobsRequest.current;
    const current = appliedQueryRef.current;
    const latest = () => request === jobsRequest.current;
    await Promise.all([
      load(
        () => listJobs(current),
        (next) => latest() && setJobs(next),
      ),
      load(
        () => listJobsBelowThreshold(current),
        (next) => latest() && setBelow(next),
      ),
      load(listFilteredOutJobs, setFiltered),
    ]);
  }
  const loadCompanies = () => load(listCompanies, setCompanies);
  const loadUnscored = () => load(getUnscoredCount, setUnscored);

  async function loadAll() {
    setFailure(null);
    await Promise.all([
      loadJobs(),
      loadCompanies(),
      loadUnscored(),
      load(getSearchSettings, setSettings),
      load(listRuns, ([latest]) => setRun(latest ?? null)),
    ]);
  }

  useEffect(() => {
    void loadAll();
  }, []);

  useEffect(() => {
    const delay = query.location !== appliedQuery.location ? LOCATION_DEBOUNCE_MS : 0;
    const timer = setTimeout(() => setAppliedQuery(query), delay);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    // The first lists come with loadAll.
    if (!queryApplied.current) {
      queryApplied.current = true;
      return;
    }
    void loadJobs();
  }, [appliedQuery]);

  useEffect(() => {
    if (run?.status !== "running") return;
    const timer = setTimeout(async () => {
      try {
        const next = await getRun(run.id);
        if (
          next.companies_fetched !== run.companies_fetched ||
          next.scored_jobs !== run.scored_jobs ||
          next.status !== "running"
        ) {
          void loadJobs();
        }
        if (next.stage !== run.stage || next.status !== "running") {
          void loadCompanies();
        }
        if (next.status !== "running") {
          void loadUnscored();
        }
        setRun(next);
      } catch (e) {
        setFailure({ message: (e as Error).message, retry: loadAll });
      }
    }, POLL_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [run]);

  async function startAndFollow(start: () => Promise<Run>, retry: () => void) {
    setStarting(true);
    setFailure(null);
    try {
      setRun(await start());
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        await load(listRuns, ([latest]) => setRun(latest ?? null));
      } else if (e instanceof ApiError && e.status === 400) {
        await load(getSearchSettings, setSettings);
      } else {
        setFailure({ message: `Couldn't start the run. ${(e as Error).message}`, retry });
      }
    } finally {
      setStarting(false);
    }
  }
  const startRunAndFollow = () => startAndFollow(startRun, startRunAndFollow);
  const scoreUnscored = () => startAndFollow(startScoringRun, scoreUnscored);

  function updateCompany(updated: Company) {
    setCompanies((current) => current.map((c) => (c.id === updated.id ? updated : c)));
    void loadJobs();
  }

  function removeDismissed(job: Job | FilteredJob) {
    const without = <T extends Job>(list: T[] | null) => list && list.filter((j) => j.id !== job.id);
    setJobs(without);
    setBelow(without);
    setFiltered(without);
    setSelected(null);
    setDismissed(job.title);
  }

  async function dismiss(job: Job | FilteredJob) {
    try {
      await dismissJob(job.id);
      removeDismissed(job);
    } catch (e) {
      setFailure({ message: `Couldn't dismiss ${job.title}. ${(e as Error).message}`, retry: () => dismiss(job) });
    }
  }

  function updateRescored(job: Job | FilteredJob) {
    setSelected(job);
    void loadJobs();
    void loadUnscored();
  }

  return (
    <div className="app">
      <Topbar page="jobs">
        <RunButton running={running} ready={ready} onClick={startRunAndFollow} />
      </Topbar>

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
              Open postings that pass your filters and that Claude scored at or above your match threshold, best fit
              first. Nothing is fetched or scored until you click Run.
            </p>
          </div>

          {failure && (
            <ErrorBanner message={failure.message} onRetry={failure.retry} onDismiss={() => setFailure(null)} />
          )}
          {settings && !settings.ready && !running && <SetupNotice missing={settings.missing} />}
          {run?.status === "running" && <RunProgress run={run} />}
          {run && run.status !== "running" && <RunSummary run={run} onReview={() => setView("filtered")} />}
          {!running && unscored > 0 && <UnscoredNotice count={unscored} onScore={scoreUnscored} />}

          {dismissed && (
            <div className="notice notice-muted" role="status">
              <span className="notice-text">
                Dismissed <strong>{dismissed}</strong>. It won't come back, even after later runs.
              </span>
              <button className="icon-button" onClick={() => setDismissed(null)} aria-label="Close">
                ×
              </button>
            </div>
          )}

          {showTabs && (
            <ViewTabs
              view={view}
              counts={{ matches: jobs.length, below: below.length, filtered: filtered.length }}
              onChange={setView}
            />
          )}
          {showTabs && view !== "filtered" && <JobFilters query={query} companies={companies} onChange={setQuery} />}
          <div
            role={showTabs ? "tabpanel" : undefined}
            id="jobs-panel"
            aria-labelledby={showTabs ? `tab-${view}` : undefined}
          >
            {!loaded ? (
              !failure && <JobListSkeleton />
            ) : view === "filtered" ? (
              filtered.length === 0 ? (
                <FilteredEmptyState />
              ) : (
                <JobList jobs={filtered} onOpen={setSelected} onDismiss={dismiss} />
              )
            ) : view === "below" ? (
              below.length === 0 ? (
                filtering ? (
                  <NoFilterMatches onClear={() => setQuery({ ...NO_FILTERS, sort: query.sort })} />
                ) : (
                  <BelowEmptyState threshold={settings?.min_score ?? 70} />
                )
              ) : (
                <JobList jobs={below} onOpen={setSelected} onDismiss={dismiss} />
              )
            ) : jobs.length === 0 && filtering ? (
              <NoFilterMatches onClear={() => setQuery({ ...NO_FILTERS, sort: query.sort })} />
            ) : jobs.length === 0 ? (
              <EmptyState
                running={running}
                ready={ready}
                hasRun={run !== null}
                below={below.length}
                filteredOut={filtered.length}
                threshold={settings?.min_score ?? 70}
                onRun={startRunAndFollow}
                onReview={setView}
              />
            ) : (
              <JobList jobs={jobs} onOpen={setSelected} onDismiss={dismiss} />
            )}
          </div>
        </main>
      </div>

      {selected && (
        <JobDetail
          key={selected.id}
          job={selected}
          onClose={() => setSelected(null)}
          onRescored={updateRescored}
          onDismissed={removeDismissed}
        />
      )}
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
      title={!ready && !running ? "Finish setting up to run." : undefined}
    >
      {running ? <span className="spinner" aria-hidden="true" /> : <PlayIcon />}
      {running ? "Running…" : "Run"}
    </button>
  );
}

function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

/** Setup steps done on another page link to it; the rest are in the Search settings panel. */
function setupLink(item: string): { href: string; label: string } | null {
  if (/anthropic/i.test(item)) return { href: "#/settings", label: "Open Settings" };
  if (/resume/i.test(item)) return { href: "#/resume", label: "Open Resume" };
  return null;
}

function SetupNotice({ missing }: { missing: string[] }) {
  return (
    <div className="notice notice-info notice-stacked" role="status">
      <div className="notice-row">
        <SlidersIcon />
        <span className="notice-text">Finish setting up to run:</span>
      </div>
      <ul className="notice-list">
        {missing.map((item) => {
          const link = setupLink(item);
          return (
            <li key={item}>
              {item}
              {link && (
                <>
                  {" "}
                  <a href={link.href}>{link.label}</a>
                </>
              )}
            </li>
          );
        })}
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
  if (run.stage === "scoring") {
    const scoredPercent = run.scoring_total === 0 ? 0 : (run.scored_jobs / run.scoring_total) * 100;
    return (
      <div className="notice notice-info notice-stacked" role="status">
        <div className="notice-row">
          <span className="spinner spinner-dark" aria-hidden="true" />
          <span className="notice-text">
            Scoring fit with Claude: {run.scored_jobs} of {plural(run.scoring_total, "job")}
            {run.matched_jobs > 0 && ` · ${plural(run.matched_jobs, "match", "matches")} so far`}
          </span>
        </div>
        <div
          className="progress"
          role="progressbar"
          aria-label="Scoring"
          aria-valuemin={0}
          aria-valuemax={run.scoring_total}
          aria-valuenow={run.scored_jobs}
        >
          <div className="progress-bar" style={{ width: `${scoredPercent}%` }} />
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
          {nearMisses(run.filtered_out) > 0 && ` · ${nearMisses(run.filtered_out)} filtered out`}
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
  const scoringErrors = run.errors.filter((e) => e.kind === "scoring");
  const full = run.kind === "full";
  const changes = [
    full && run.companies_discovered > 0 && plural(run.companies_discovered, "new company", "new companies"),
    full && `${plural(run.companies_total, "company", "companies")} checked`,
    full && (run.new_jobs === 0 ? "no new jobs" : plural(run.new_jobs, "new job")),
    run.updated_jobs > 0 && `${run.updated_jobs} updated`,
    run.closed_jobs > 0 && `${run.closed_jobs} closed`,
    (run.scored_jobs > 0 || !full) && `${run.scored_jobs} scored`,
    run.scored_jobs > 0 && plural(run.matched_jobs, "new match", "new matches"),
    run.ai_cost_usd > 0 && `about ${formatCost(run.ai_cost_usd)} AI cost`,
  ].filter(Boolean);
  const filteredOut = nearMisses(run.filtered_out);
  const otherRoles = run.filtered_out.role ?? 0;
  const byRule = (Object.entries(run.filtered_out) as [FilterRule, number][]).filter(
    ([rule, count]) => rule !== "role" && count > 0,
  );

  return (
    <>
      <div className="notice notice-success" role="status">
        <CheckIcon />
        <span className="notice-text">
          {full ? "Run finished" : "Scoring-only run finished"} {when} · {changes.join(" · ")}
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
      {otherRoles > 0 && (
        <div className="notice notice-muted" role="status">
          <span className="notice-text">
            {otherRoles.toLocaleString()} other {otherRoles === 1 ? "role" : "roles"} at these companies skipped: their
            titles don't match your roles.
          </span>
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
      {scoringErrors.map((error) => (
        <div className="notice notice-warning" role="status" key={error.message}>
          <AlertIcon />
          <span className="notice-text">
            {error.message}
            {/API key|model|credit/i.test(error.message) && (
              <>
                {" "}
                <a href="#/settings">Open Settings</a>
              </>
            )}
          </span>
        </div>
      ))}
      {run.search_queries_capped && (
        <div className="notice notice-muted" role="status">
          <span className="notice-text">
            Only the first {run.search_queries} role and location combinations were searched this run. Remove some roles
            or locations to cover them all.
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

function UnscoredNotice({ count, onScore }: { count: number; onScore: () => void }) {
  return (
    <div className="notice notice-info" role="status">
      <AlertIcon />
      <span className="notice-text">
        {plural(count, "job passes", "jobs pass")} your filters but {count === 1 ? "has" : "have"} no score for your
        current resume. Scoring {count === 1 ? "it doesn't" : "them doesn't"} search or fetch boards.
      </span>
      <button type="button" className="button button-secondary" onClick={onScore}>
        Score {plural(count, "unscored job")}
      </button>
    </div>
  );
}

function ErrorBanner({ message, onRetry, onDismiss }: { message: string; onRetry: () => void; onDismiss: () => void }) {
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
  counts,
  onChange,
}: {
  view: View;
  counts: Record<View, number>;
  onChange: (view: View) => void;
}) {
  const tabs: { id: View; label: string; count: number }[] = [
    { id: "matches", label: "Matches", count: counts.matches },
    { id: "below", label: "Below threshold", count: counts.below },
    { id: "filtered", label: "Filtered out", count: counts.filtered },
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
      <p>
        Jobs whose title matches your roles but that another filter dropped (location, seniority, experience, salary or
        sponsorship) show up here, each with the reason. Other roles at the same companies aren't listed.
      </p>
    </section>
  );
}

function BelowEmptyState({ threshold }: { threshold: number }) {
  return (
    <section className="empty">
      <div className="empty-icon" aria-hidden="true">
        <SlidersIcon size={28} />
      </div>
      <h2>Nothing below your threshold</h2>
      <p>
        Jobs that pass your filters but score under {threshold}, and jobs not scored yet, show up here with Claude's
        reasons.
      </p>
    </section>
  );
}

function EmptyState({
  running,
  ready,
  hasRun,
  below,
  filteredOut,
  threshold,
  onRun,
  onReview,
}: {
  running: boolean;
  ready: boolean;
  hasRun: boolean;
  below: number;
  filteredOut: number;
  threshold: number;
  onRun: () => void;
  onReview: (view: View) => void;
}) {
  if (!ready) {
    return (
      <section className="empty">
        <div className="empty-icon" aria-hidden="true">
          <SlidersIcon size={28} />
        </div>
        <h2>Set up your search</h2>
        <p>
          Add the roles and locations you want, pick your job boards and add a search API key. Then add your Anthropic
          API key in Settings and your resume, so Claude can score how well each job fits you.
        </p>
      </section>
    );
  }
  if (below > 0) {
    return (
      <section className="empty">
        <div className="empty-icon" aria-hidden="true">
          <SlidersIcon size={28} />
        </div>
        <h2>No strong matches yet</h2>
        <p>
          {plural(below, "job passes", "jobs pass")} your filters but {below === 1 ? "isn't" : "aren't"} scored{" "}
          {threshold} or higher yet. Review them, or lower your match threshold in Search settings.
        </p>
        <button className="button button-secondary" onClick={() => onReview("below")}>
          Review jobs below threshold
        </button>
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
        <button className="button button-secondary" onClick={() => onReview("filtered")}>
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
        <h2>No open jobs for your roles right now</h2>
        <p>
          None of the companies you track have open postings matching your roles. Run again later, or broaden your
          search settings.
        </p>
      </section>
    );
  }
  return (
    <section className="empty">
      <div className="empty-icon" aria-hidden="true">
        <BriefcaseIcon />
      </div>
      <h2>No jobs yet</h2>
      <p>Run a search to find companies hiring for your roles, pull in their open postings and score each for fit.</p>
      <button className="button button-primary" onClick={onRun} disabled={running}>
        {running ? "Running…" : "Run your first search"}
      </button>
    </section>
  );
}

function NoFilterMatches({ onClear }: { onClear: () => void }) {
  return (
    <section className="empty">
      <div className="empty-icon" aria-hidden="true">
        <SlidersIcon size={28} />
      </div>
      <h2>No jobs match these filters</h2>
      <p>Try another company or location, or a longer time range.</p>
      <button className="button button-secondary" onClick={onClear}>
        Clear filters
      </button>
    </section>
  );
}

type JobActions = {
  onOpen: (job: Job | FilteredJob) => void;
  onDismiss: (job: Job | FilteredJob) => void;
};

function JobList({ jobs, ...actions }: { jobs: (Job | FilteredJob)[] } & JobActions) {
  return (
    <ul className="job-list">
      {jobs.map((job) => (
        <JobRow key={job.id} job={job} {...actions} />
      ))}
    </ul>
  );
}

function JobRow({ job, onOpen, onDismiss }: { job: Job | FilteredJob } & JobActions) {
  const location = job.locations.join(" · ");
  const rejection = "rejection" in job ? job.rejection : null;
  return (
    <li className={`job${rejection ? " is-filtered" : ""}`}>
      <div className="job-main">
        <h3 className="job-title">
          {!rejection && <ScoreBadge score={job.score} />}
          <button type="button" className="job-open" onClick={() => onOpen(job)}>
            {job.title}
          </button>
        </h3>
        <div className="job-meta">
          <span className="job-company">{companyName(job.company)}</span>
          <span className="dot" aria-hidden="true" />
          <span className="badge">{PLATFORM_LABELS[job.platform]}</span>
          {job.salary && <span className="badge badge-green">{formatSalary(job.salary)}</span>}
          {job.application && (
            <a
              className={`badge ${["failed", "needs_manual"].includes(job.application.status) ? "badge-warning" : "badge-link"}`}
              href={`#/applications/${job.application.id}`}
            >
              {APPLICATION_LABELS[job.application.status].badge}
            </a>
          )}
        </div>
        {rejection && (
          <p className="job-rejection">
            <span className="badge badge-warning">{FILTER_LABELS[rejection.rule]}</span>
            {rejection.reason}
          </p>
        )}
        {!rejection && job.score && <ScoreDetails score={job.score} />}
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
      <div className="job-actions">
        <a className="button button-secondary job-link" href={job.posting_url} target="_blank" rel="noreferrer">
          View posting
          <ExternalIcon />
          <span className="visually-hidden">(opens in a new tab)</span>
        </a>
        <button
          type="button"
          className="icon-button job-dismiss"
          onClick={() => onDismiss(job)}
          aria-label={`Dismiss ${job.title}`}
          title="Dismiss: hide this job for good"
        >
          ×
        </button>
      </div>
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
