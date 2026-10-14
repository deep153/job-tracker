import { useEffect, useState } from "react";
import { listApplications } from "../api/applications";
import { AlertIcon } from "../components/icons";
import { ScoreBadge } from "../components/Score";
import { Topbar } from "../components/Topbar";
import { APPLICATION_LABELS, type ApplicationStatus, type ApplicationSummary } from "../types/application";
import { companyName, fullDate, timeAgo } from "../utils/format";

type Sort = "date" | "status";

// Sorting by status puts what's still live first and what's over last.
const STATUS_ORDER: ApplicationStatus[] = [
  "offer",
  "interviewing",
  "submitted",
  "needs_manual",
  "failed",
  "submitting",
  "in_review",
  "drafting",
  "rejected",
  "withdrawn",
];

function statusBadgeClass(status: ApplicationStatus): string {
  if (status === "offer" || status === "interviewing") return "badge badge-green";
  if (status === "needs_manual" || status === "failed") return "badge badge-warning";
  if (status === "rejected" || status === "withdrawn") return "badge badge-muted";
  return "badge";
}

function sorted(applications: ApplicationSummary[], sort: Sort): ApplicationSummary[] {
  const byDate = (a: ApplicationSummary, b: ApplicationSummary) => b.date.localeCompare(a.date);
  if (sort === "date") return [...applications].sort(byDate);
  return [...applications].sort(
    (a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status) || byDate(a, b),
  );
}

export function ApplicationsPage() {
  const [applications, setApplications] = useState<ApplicationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<Sort>("date");

  useEffect(() => {
    listApplications().then(setApplications, (e: Error) => setError(e.message));
  }, []);

  return (
    <div className="app">
      <Topbar page="applications" />
      <main className="page">
        <div className="page-heading">
          <h1>Applications</h1>
          <p className="subtitle">
            Everything you've applied to, with the resume and answers you sent. Update the status as you hear back.
          </p>
        </div>
        {error && (
          <div className="notice notice-error" role="alert">
            <AlertIcon />
            <span className="notice-text">{error}</span>
          </div>
        )}
        {!applications && !error && <div className="skeleton resume-skeleton" aria-busy="true" aria-label="Loading" />}
        {applications && (
          <section className="panel" aria-labelledby="applications-heading">
            <div className="panel-header">
              <h2 className="panel-title" id="applications-heading">
                All applications
              </h2>
              <span className="count count-small">{applications.length}</span>
              <label className="job-filter applications-sort">
                <span className="job-filter-label">Sort by</span>
                <select className="text-input" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
                  <option value="date">Date</option>
                  <option value="status">Status</option>
                </select>
              </label>
            </div>
            {applications.length === 0 ? (
              <div className="panel-body">
                <p className="panel-empty">
                  No applications yet. Open a job on the <a href="#/">Jobs</a> page and choose Apply.
                </p>
              </div>
            ) : (
              <table className="cost-table applications-table">
                <thead>
                  <tr>
                    <th scope="col">Company</th>
                    <th scope="col">Role</th>
                    <th scope="col">Date</th>
                    <th scope="col">Score</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted(applications, sort).map((application) => (
                    <tr key={application.id}>
                      <td>{companyName(application.job.company)}</td>
                      <td>
                        <a href={`#/applications/${application.id}`}>{application.job.title}</a>
                      </td>
                      <td>
                        <time dateTime={application.date} title={fullDate(application.date)}>
                          {timeAgo(application.date)}
                        </time>
                      </td>
                      <td>
                        <ScoreBadge score={application.job.score} />
                      </td>
                      <td>
                        <span className={statusBadgeClass(application.status)}>
                          {APPLICATION_LABELS[application.status].badge}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
