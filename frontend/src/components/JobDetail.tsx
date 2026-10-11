import { type ReactNode, useEffect, useRef, useState } from "react";
import { dismissJob, rescoreJob } from "../api/jobs";
import type { FilteredJob, Job } from "../types/job";
import { FILTER_LABELS, PLATFORM_LABELS, companyName, formatSalary, fullDate, timeAgo } from "../utils/format";
import { AlertIcon, ExternalIcon, PinIcon } from "./icons";
import { ScoreBadge, ScoreDetails } from "./Score";

type Action = "rescore" | "dismiss";

export function JobDetail({
  job,
  onClose,
  onRescored,
  onDismissed,
}: {
  job: Job | FilteredJob;
  onClose: () => void;
  onRescored: (job: Job | FilteredJob) => void;
  onDismissed: (job: Job | FilteredJob) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState<Action | null>(null);
  const [error, setError] = useState<string | null>(null);
  const rejection = "rejection" in job ? job.rejection : null;
  const location = job.locations.join(" · ");

  useEffect(() => {
    dialog.current?.showModal();
  }, []);

  async function act(action: Action) {
    setBusy(action);
    setError(null);
    try {
      if (action === "rescore") {
        onRescored(await rescoreJob(job.id));
      } else {
        await dismissJob(job.id);
        onDismissed(job);
      }
    } catch (e) {
      const verb = action === "rescore" ? "re-score" : "dismiss";
      setError(`Couldn't ${verb} this job. ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <dialog
      ref={dialog}
      className="job-detail"
      aria-labelledby="job-detail-title"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onKeyDown={(e) => {
        if (e.key !== "Escape") return;
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => e.target === dialog.current && onClose()}
    >
      <div className="job-detail-inner">
        <header className="job-detail-header">
          <div className="job-detail-heading">
            <h2 className="job-title" id="job-detail-title">
              {!rejection && <ScoreBadge score={job.score} />}
              {job.title}
            </h2>
            <div className="job-meta">
              <span className="job-company">{companyName(job.company)}</span>
              <span className="dot" aria-hidden="true" />
              <span className="badge">{PLATFORM_LABELS[job.platform]}</span>
              {job.salary && <span className="badge badge-green">{formatSalary(job.salary)}</span>}
            </div>
            <div className="job-detail-facts">
              <span className="job-location">
                <PinIcon />
                {location || "Location not listed"}
              </span>
              <time dateTime={job.updated_at} title={fullDate(job.updated_at)}>
                Updated {timeAgo(job.updated_at)}
              </time>
            </div>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <div className="job-detail-actions">
          <a className="button button-primary" href={job.posting_url} target="_blank" rel="noreferrer">
            View original posting
            <ExternalIcon />
            <span className="visually-hidden">(opens in a new tab)</span>
          </a>
          <button
            type="button"
            className="button button-secondary"
            onClick={() => act("rescore")}
            disabled={busy !== null}
            aria-busy={busy === "rescore"}
          >
            {busy === "rescore" && <span className="spinner spinner-dark" aria-hidden="true" />}
            {busy === "rescore" ? "Scoring…" : job.score ? "Re-score" : "Score now"}
          </button>
          <button
            type="button"
            className="button button-ghost"
            onClick={() => act("dismiss")}
            disabled={busy !== null}
            title="Hide this job for good, including after later runs"
          >
            Dismiss
          </button>
        </div>

        {error && (
          <div className="notice notice-error" role="alert">
            <AlertIcon />
            <span className="notice-text">{error}</span>
          </div>
        )}

        {rejection && (
          <section className="job-detail-section">
            <h3>Filtered out</h3>
            <p className="job-rejection">
              <span className="badge badge-warning">{FILTER_LABELS[rejection.rule]}</span>
              {rejection.reason}
            </p>
          </section>
        )}

        <section className="job-detail-section">
          <h3>Fit</h3>
          {job.score ? (
            <>
              <p className="job-detail-note">
                Scored {job.score.score} of 100 against resume version {job.score.resume_version} by{" "}
                {job.score.model}, {timeAgo(job.score.scored_at)}.
              </p>
              <ScoreDetails score={job.score} />
            </>
          ) : (
            <p className="job-detail-note">Not scored yet. It's scored on the next run, or you can score it now.</p>
          )}
        </section>

        <section className="job-detail-section">
          <h3>Description</h3>
          <Description text={job.description} />
        </section>
      </div>
    </dialog>
  );
}

/** The stored description is plain text: blank lines between blocks, and "- " before list items. */
function Description({ text }: { text: string }) {
  if (!text.trim()) return <p className="job-detail-note">The posting has no description.</p>;
  const blocks: ReactNode[] = [];
  let bullets: string[] = [];
  let lines: string[] = [];
  const flush = () => {
    if (bullets.length > 0) {
      blocks.push(
        <ul key={blocks.length}>
          {bullets.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>,
      );
    }
    if (lines.length > 0) {
      blocks.push(
        <p key={blocks.length}>
          {lines.map((line, i) => (
            <span key={i}>
              {i > 0 && <br />}
              {line}
            </span>
          ))}
        </p>,
      );
    }
    bullets = [];
    lines = [];
  };
  for (const line of text.split("\n")) {
    if (line.startsWith("- ")) {
      if (lines.length > 0) flush();
      bullets.push(line.slice(2));
    } else if (line.trim() === "") {
      flush();
    } else {
      if (bullets.length > 0) flush();
      lines.push(line);
    }
  }
  flush();
  return <div className="job-description">{blocks}</div>;
}
