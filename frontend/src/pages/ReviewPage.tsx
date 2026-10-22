import { useEffect, useState } from "react";
import {
  answerQuestions,
  applyToJob,
  approveApplication,
  cancelApplication,
  editCoverLetter,
  editTailoredResume,
  getApplication,
  saveAnswerToBank,
  setApplicationStatus,
} from "../api/applications";
import { AlertIcon, CheckIcon, DownloadIcon, ExternalIcon } from "../components/icons";
import { CoverLetterPanel } from "../components/CoverLetterPanel";
import { answerDraft, changedAnswers, QuestionsPanel, SentAnswersPanel } from "../components/QuestionsPanel";
import { ScoreBadge } from "../components/Score";
import { Topbar } from "../components/Topbar";
import {
  APPLICATION_LABELS,
  APPLIED_STATUSES,
  type Application,
  type BulletEdit,
  type SkillLine,
  type TailoredResume,
  type TailoredResumeEdits,
  type TrackedStatus,
} from "../types/application";
import { companyName, formatCost, fullDate, timeAgo } from "../utils/format";

const POLL_MS = 1500;

function pages(count: number): string {
  return `${count} ${count === 1 ? "page" : "pages"}`;
}

export function ReviewPage({ id }: { id: number }) {
  const [application, setApplication] = useState<Application | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const working = application?.status === "drafting" || application?.status === "submitting";
  const sent = application !== null && APPLIED_STATUSES.includes(application.status);
  const submitFailed =
    application?.status === "failed" && application.resume !== null && application.questions !== null;

  useEffect(() => {
    let cancelled = false;
    getApplication(id).then(
      (a) => !cancelled && setApplication(a),
      (e: Error) => !cancelled && setLoadError(e.message),
    );
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    if (!working) return;
    const timer = window.setInterval(() => {
      getApplication(id).then(setApplication, () => {});
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [id, working]);

  return (
    <div className="app">
      <Topbar page={sent ? "applications" : "jobs"} />
      <main className="page">
        <a className="back-link" href={sent ? "#/applications" : "#/"}>
          {sent ? "← Applications" : "← Jobs"}
        </a>
        <div className="page-heading">
          <h1>{sent ? "Application" : "Review application"}</h1>
          {application && (
            <p className="subtitle review-job">
              <ScoreBadge score={application.job.score} />
              <span>
                <strong>{application.job.title}</strong> at {companyName(application.job.company)}
              </span>
            </p>
          )}
        </div>

        {loadError && (
          <div className="notice notice-error" role="alert">
            <AlertIcon />
            <span className="notice-text">{loadError}</span>
            <a className="button button-ghost" href="#/">
              Back to jobs
            </a>
          </div>
        )}
        {!application && !loadError && (
          <div className="skeleton resume-skeleton" aria-busy="true" aria-label="Loading" />
        )}
        {application?.status === "drafting" && <Drafting application={application} />}
        {application?.status === "submitting" && <Submitting />}
        {application && APPLIED_STATUSES.includes(application.status) && (
          <Sent application={application} onSaved={setApplication} />
        )}
        {application?.status === "needs_manual" && <NeedsManual application={application} onSaved={setApplication} />}
        {application?.status === "failed" && !submitFailed && <Failed application={application} />}
        {(application?.status === "in_review" || submitFailed) && application?.resume && (
          <InReview application={application} resume={application.resume} onSaved={setApplication} />
        )}
      </main>
    </div>
  );
}

function Drafting({ application }: { application: Application }) {
  return (
    <section className="panel review-status" aria-live="polite">
      <span className="spinner spinner-dark" aria-hidden="true" />
      <div>
        <h2 className="panel-title">Preparing your application…</h2>
        <p className="panel-empty">
          The application form is read and answered from your answer bank. Claude rewrites your Summary and reorders
          your Skills for this job, then the resume is converted to PDF and checked to still fit on the same number of
          pages. This usually takes under a minute.
        </p>
      </div>
      <CancelButton application={application} />
    </section>
  );
}

function Submitting() {
  return (
    <section className="panel review-status" aria-live="polite">
      <span className="spinner spinner-dark" aria-hidden="true" />
      <div>
        <h2 className="panel-title">Sending your application…</h2>
        <p className="panel-empty">
          A browser window opened on the company's application form. Your reviewed answers are being filled in and your
          tailored resume uploaded, then the form is submitted. You can watch, but please don't type in it.
        </p>
      </div>
    </section>
  );
}

const STATUS_CHOICES: (TrackedStatus | "submitted")[] = ["submitted", "interviewing", "offer", "rejected", "withdrawn"];

function Sent({ application, onSaved }: { application: Application; onSaved: (a: Application) => void }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function track(status: TrackedStatus | "submitted") {
    setSaving(true);
    setError(null);
    try {
      onSaved(await setApplicationStatus(application.id, status));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <section className="panel review-status" aria-live="polite">
        <CheckIcon />
        <div>
          <h2 className="panel-title">Application sent</h2>
          <p className="panel-empty">
            Submitted
            {application.submitted_at && (
              <>
                {" "}
                <time dateTime={application.submitted_at} title={fullDate(application.submitted_at)}>
                  {timeAgo(application.submitted_at)}
                </time>
              </>
            )}
            . Update the status as you hear back.
          </p>
          <div className="review-actions">
            <label className="job-filter">
              <span className="job-filter-label">Status</span>
              <select
                className="text-input"
                value={application.status}
                onChange={(e) => void track(e.target.value as TrackedStatus | "submitted")}
                disabled={saving}
                aria-busy={saving}
              >
                {STATUS_CHOICES.map((status) => (
                  <option key={status} value={status}>
                    {APPLICATION_LABELS[status].badge}
                  </option>
                ))}
              </select>
            </label>
            <a className="button button-secondary" href={application.resume?.pdf_url} target="_blank" rel="noreferrer">
              Resume you sent
              <ExternalIcon />
              <span className="visually-hidden">(opens in a new tab)</span>
            </a>
            {application.cover_letter?.pdf_url && (
              <a
                className="button button-ghost"
                href={application.cover_letter.pdf_url}
                target="_blank"
                rel="noreferrer"
              >
                Cover letter PDF
                <ExternalIcon />
                <span className="visually-hidden">(opens in a new tab)</span>
              </a>
            )}
          </div>
          {error && (
            <div className="notice notice-error" role="alert">
              <AlertIcon />
              <span className="notice-text">{error}</span>
            </div>
          )}
        </div>
      </section>
      {application.cover_letter && (
        <section className="panel" aria-labelledby="sent-letter-heading">
          <div className="panel-header">
            <h2 className="panel-title" id="sent-letter-heading">
              Cover letter you sent
            </h2>
          </div>
          <div className="panel-body sent-letter">{application.cover_letter.text}</div>
        </section>
      )}
      {application.questions && <SentAnswersPanel questions={application.questions} />}
    </>
  );
}

function NeedsManual({ application, onSaved }: { application: Application; onSaved: (a: Application) => void }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function markSubmitted() {
    setSaving(true);
    setError(null);
    try {
      onSaved(await setApplicationStatus(application.id, "submitted"));
    } catch (e) {
      setError((e as Error).message);
      setSaving(false);
    }
  }

  return (
    <div className="notice notice-warning notice-stacked" role="alert">
      <div className="notice-row">
        <AlertIcon />
        <span className="notice-text">
          <strong>Over to you.</strong> {application.error}
        </span>
      </div>
      <p className="notice-text">
        If the window is closed already, open the form, finish it by hand and submit it. Your tailored resume is ready
        to upload.
      </p>
      <div className="review-actions">
        <a className="button button-secondary" href={application.job.application_url} target="_blank" rel="noreferrer">
          Open the application form
          <ExternalIcon />
          <span className="visually-hidden">(opens in a new tab)</span>
        </a>
        <a className="button button-ghost" href={application.resume?.pdf_url} download>
          <DownloadIcon />
          Tailored resume
        </a>
        <button
          type="button"
          className="button button-primary"
          onClick={() => void markSubmitted()}
          disabled={saving}
          aria-busy={saving}
        >
          {saving && <span className="spinner" aria-hidden="true" />}
          I've submitted it
        </button>
      </div>
      {error && <p className="notice-text">{error}</p>}
    </div>
  );
}

function Failed({ application }: { application: Application }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function retry() {
    setBusy(true);
    setError(null);
    try {
      const next = await applyToJob(application.job.id);
      window.location.hash = `#/applications/${next.id}`;
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <>
      <div className="notice notice-error" role="alert">
        <AlertIcon />
        <span className="notice-text">
          <strong>Preparing the application failed.</strong> {application.error}
        </span>
      </div>
      {error && (
        <div className="notice notice-error" role="alert">
          <AlertIcon />
          <span className="notice-text">Couldn't try again. {error}</span>
        </div>
      )}
      <div className="review-actions">
        <button type="button" className="button button-primary" onClick={retry} disabled={busy} aria-busy={busy}>
          {busy && <span className="spinner" aria-hidden="true" />}
          Try again
        </button>
        <a className="button button-ghost" href="#/">
          Back to jobs
        </a>
        {application.cost_usd > 0 && <CostNote usd={application.cost_usd} />}
      </div>
    </>
  );
}

/** `bullets` holds each experience bullet's text after its label, by paragraph index. */
type Draft = { summary: string; skills: string[]; bullets: Record<number, string> };

function draftFrom(resume: TailoredResume): Draft {
  return {
    summary: resume.summary.tailored.join("\n\n"),
    skills: resume.skills.tailored.map((l) => l.skills.join(", ")),
    bullets: Object.fromEntries((resume.bullets ?? []).map((b) => [b.index, b.tailored])),
  };
}

/** Bullets the tailor reworded or tried to: the ones the review screen lets me edit. */
function changedBullets(resume: TailoredResume): BulletEdit[] {
  return (resume.bullets ?? []).filter((b) => b.tailored !== b.master || b.reverted);
}

/** Split "Go, AWS (Lambda, S3); SQL" into skills, keeping commas inside brackets. */
function splitSkills(text: string): string[] {
  const skills: string[] = [];
  let current = "";
  let depth = 0;
  for (const char of text) {
    depth += Number("([{".includes(char)) - Number(")]}".includes(char));
    if (",;".includes(char) && depth <= 0) {
      skills.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  skills.push(current);
  return skills.map((s) => s.trim()).filter(Boolean);
}

/** The edits to send: only the bullets whose text differs from what the resume has now. */
function editsFrom(draft: Draft, resume: TailoredResume): TailoredResumeEdits {
  const tailored = draftFrom(resume).bullets;
  return {
    summary: draft.summary.split(/\n\s*\n/),
    skills: draft.skills.map(splitSkills),
    bullets: Object.entries(draft.bullets)
      .filter(([index, text]) => text.trim() !== tailored[Number(index)])
      .map(([index, text]) => ({ index: Number(index), text })),
  };
}

function InReview({
  application,
  resume,
  onSaved,
}: {
  application: Application;
  resume: TailoredResume;
  onSaved: (application: Application) => void;
}) {
  const questions = application.questions ?? [];
  const [draft, setDraft] = useState(() => draftFrom(resume));
  const [answers, setAnswers] = useState(() => answerDraft(questions));
  const [letter, setLetter] = useState(application.cover_letter?.text ?? "");
  const [letterError, setLetterError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"regenerate" | "answers" | "letter" | "save" | "approve" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [answersError, setAnswersError] = useState<string | null>(null);
  const [savingToBank, setSavingToBank] = useState<string | null>(null);
  const [approveError, setApproveError] = useState<string | null>(null);
  const dirty = JSON.stringify(editsFrom(draft, resume)) !== JSON.stringify(editsFrom(draftFrom(resume), resume));
  const changed = changedAnswers(questions, answers);
  const answersDirty = Object.keys(changed).length > 0;
  const letterDirty = application.cover_letter !== null && letter.trim() !== application.cover_letter.text;

  async function regenerate(then?: () => void) {
    setBusy(then ? "save" : "regenerate");
    setError(null);
    try {
      const saved = await editTailoredResume(application.id, editsFrom(draft, resume));
      onSaved(saved);
      if (saved.resume) setDraft(draftFrom(saved.resume));
      then?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function saveAnswers(): Promise<boolean> {
    setBusy("answers");
    setAnswersError(null);
    try {
      const saved = await answerQuestions(application.id, changed);
      onSaved(saved);
      setAnswers(answerDraft(saved.questions ?? []));
      return true;
    } catch (e) {
      setAnswersError((e as Error).message);
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function saveLetter(): Promise<boolean> {
    setBusy("letter");
    setLetterError(null);
    try {
      const saved = await editCoverLetter(application.id, letter);
      onSaved(saved);
      setLetter(saved.cover_letter?.text ?? "");
      return true;
    } catch (e) {
      setLetterError((e as Error).message);
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function saveToBank(key: string) {
    setSavingToBank(key);
    setAnswersError(null);
    try {
      onSaved(await saveAnswerToBank(application.id, key));
    } catch (e) {
      setAnswersError((e as Error).message);
    } finally {
      setSavingToBank(null);
    }
  }

  async function saveDraft() {
    const exit = () => {
      window.location.hash = "#/";
    };
    if (answersDirty && !(await saveAnswers())) return;
    if (letterDirty && !(await saveLetter())) return;
    if (dirty) void regenerate(exit);
    else exit();
  }

  async function approve() {
    setBusy("approve");
    setApproveError(null);
    try {
      onSaved(await approveApplication(application.id));
    } catch (e) {
      setApproveError((e as Error).message);
      setBusy(null);
    }
  }

  const unsaved = dirty || answersDirty || letterDirty;
  const approveBlocker = unsaved ? "Save your changes first." : application.approval_problem;

  return (
    <>
      <div className="review-actions">
        <CancelButton application={application} />
        <button type="button" className="button button-secondary" onClick={saveDraft} disabled={busy !== null}>
          {busy === "save" && <span className="spinner spinner-dark" aria-hidden="true" />}
          Save draft
        </button>
        <button
          type="button"
          className="button button-primary"
          onClick={approve}
          disabled={busy !== null || unsaved || !application.can_approve}
          aria-busy={busy === "approve"}
          aria-describedby={approveBlocker ? "approve-blocker" : undefined}
        >
          {busy === "approve" && <span className="spinner" aria-hidden="true" />}
          {application.status === "failed" ? "Try submitting again" : "Approve and submit"}
        </button>
        {approveBlocker && (
          <span className="review-blocker" id="approve-blocker">
            {approveBlocker}
          </span>
        )}
        <span className="review-saved">Saved {timeAgo(application.updated_at)}</span>
        <CostNote usd={application.cost_usd} />
      </div>
      {application.status === "failed" && (
        <div className="notice notice-error notice-stacked" role="alert">
          <div className="notice-row">
            <AlertIcon />
            <span className="notice-text">
              <strong>Sending failed.</strong> {application.error} Fix anything below and try again, or apply by hand on
              the{" "}
              <a href={application.job.application_url} target="_blank" rel="noreferrer">
                company's form
              </a>
              .
            </span>
          </div>
          {application.screenshot_url && (
            <a href={application.screenshot_url} target="_blank" rel="noreferrer" className="review-screenshot">
              <img src={application.screenshot_url} alt="The application form when sending failed" />
            </a>
          )}
        </div>
      )}
      {approveError && (
        <div className="notice notice-error" role="alert">
          <AlertIcon />
          <span className="notice-text">Couldn't start sending. {approveError}</span>
        </div>
      )}
      {application.form_error && (
        <div className="notice notice-warning" role="alert">
          <AlertIcon />
          <span className="notice-text">
            <strong>The application form couldn't be read.</strong> {application.form_error}
          </span>
        </div>
      )}
      {!resume.fits && (
        <div className="notice notice-warning" role="alert">
          <AlertIcon />
          <span className="notice-text">
            The tailored resume runs to {pages(resume.page_count)}, longer than your {resume.master_page_count}-page
            master. Shorten the Summary or a bullet, or drop some skills, then regenerate.
          </span>
        </div>
      )}
      <div className="resume-layout">
        <div className="resume-main">
          {application.questions && (
            <QuestionsPanel
              questions={questions}
              draft={answers}
              onChange={(next) => {
                setAnswers(next);
                setAnswersError(null);
              }}
              onSave={() => void saveAnswers()}
              onUndo={() => {
                setAnswers(answerDraft(questions));
                setAnswersError(null);
              }}
              onSaveToBank={(key) => void saveToBank(key)}
              saving={busy === "answers"}
              savingToBank={savingToBank}
              error={answersError}
            />
          )}
          {application.cover_letter && (
            <CoverLetterPanel
              letter={application.cover_letter}
              draft={letter}
              onChange={(next) => {
                setLetter(next);
                setLetterError(null);
              }}
              onSave={() => void saveLetter()}
              onUndo={() => {
                setLetter(application.cover_letter?.text ?? "");
                setLetterError(null);
              }}
              saving={busy === "letter"}
              error={letterError}
            />
          )}
          <section className="panel" aria-labelledby="edit-heading">
            <div className="panel-header">
              <h2 className="panel-title" id="edit-heading">
                Edit
              </h2>
              {dirty && <span className="review-unsaved">Unsaved changes</span>}
            </div>
            <div className="panel-body">
              <label className="field">
                <span className="field-label">Summary</span>
                <textarea
                  className="text-input review-summary-input"
                  rows={5}
                  value={draft.summary}
                  onChange={(e) => setDraft({ ...draft, summary: e.target.value })}
                />
                {resume.summary.master.length > 1 && (
                  <span className="field-hint">Separate the paragraphs with a blank line.</span>
                )}
              </label>
              {resume.skills.master.map((line, index) => (
                <label className="field" key={index}>
                  <span className="field-label">{line.label ?? `Skills line ${index + 1}`}</span>
                  <input
                    className="text-input"
                    value={draft.skills[index]}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        skills: draft.skills.map((s, i) => (i === index ? e.target.value : s)),
                      })
                    }
                  />
                </label>
              ))}
              <p className="field-hint">
                Most relevant skills first, separated by commas. Only skills in your master skills list can be used.
              </p>
              {changedBullets(resume).map((b) => (
                <div className="field" key={b.index}>
                  <label className="field-label" htmlFor={`bullet-${b.index}`}>
                    {b.label ? `${b.label}:` : "Experience bullet"}
                  </label>
                  <textarea
                    id={`bullet-${b.index}`}
                    className="text-input review-bullet-input"
                    rows={2}
                    value={draft.bullets[b.index]}
                    onChange={(e) => setDraft({ ...draft, bullets: { ...draft.bullets, [b.index]: e.target.value } })}
                  />
                  <div className="review-bullet-actions">
                    <span className="field-hint">Original: {b.master}</span>
                    <button
                      type="button"
                      className="button button-ghost button-tiny"
                      onClick={() => setDraft({ ...draft, bullets: { ...draft.bullets, [b.index]: b.master } })}
                      disabled={draft.bullets[b.index] === b.master}
                    >
                      Use original
                    </button>
                  </div>
                </div>
              ))}
              {changedBullets(resume).length > 0 && (
                <p className="field-hint">
                  Bullets keep their label, every number and their length (15% longer at most), and can only name skills
                  from the original bullet or your master list; anything else goes back to the original.
                </p>
              )}
              {error && (
                <div className="notice notice-error" role="alert">
                  <AlertIcon />
                  <span className="notice-text">{error}</span>
                </div>
              )}
              <div className="panel-actions">
                <button
                  type="button"
                  className="button button-ghost"
                  onClick={() => {
                    setDraft(draftFrom(resume));
                    setError(null);
                  }}
                  disabled={!dirty || busy !== null}
                >
                  Undo changes
                </button>
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => void regenerate()}
                  disabled={!dirty || busy !== null}
                  aria-busy={busy === "regenerate"}
                >
                  {busy === "regenerate" && <span className="spinner" aria-hidden="true" />}
                  {busy === "regenerate" ? "Regenerating…" : "Regenerate PDF"}
                </button>
              </div>
            </div>
          </section>
          <SummaryDiff master={resume.summary.master} tailored={resume.summary.tailored} />
          <SkillsDiff master={resume.skills.master} tailored={resume.skills.tailored} />
          {resume.bullets && resume.bullets.length > 0 && <BulletsDiff bullets={resume.bullets} />}
          <Coverage coverage={resume.coverage} fitScore={resume.fit_score} />
        </div>
        <section className="panel resume-preview-panel" aria-labelledby="preview-heading">
          <div className="panel-header">
            <h2 className="panel-title" id="preview-heading">
              Tailored PDF
            </h2>
            <span className="count count-small" title={`Your master is ${pages(resume.master_page_count)}`}>
              {pages(resume.page_count)}
            </span>
            <a className="button button-ghost" href={resume.docx_url} download>
              <DownloadIcon />
              .docx
            </a>
            <a className="button button-ghost" href={resume.pdf_url} target="_blank" rel="noreferrer">
              Open
              <ExternalIcon />
              <span className="visually-hidden">(opens in a new tab)</span>
            </a>
          </div>
          <iframe
            key={application.updated_at}
            className="resume-preview"
            src={`${resume.pdf_url}?v=${encodeURIComponent(application.updated_at)}#view=FitH&navpanes=0`}
            title="PDF preview of the tailored resume"
          />
        </section>
      </div>
    </>
  );
}

function CostNote({ usd }: { usd: number }) {
  return <span className="review-cost">Tailoring cost about {formatCost(usd)}</span>;
}

function CancelButton({ application }: { application: Application }) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function cancel() {
    setBusy(true);
    setError(null);
    try {
      await cancelApplication(application.id);
      window.location.hash = "#/";
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  if (!confirming) {
    return (
      <button type="button" className="button button-secondary" onClick={() => setConfirming(true)}>
        Cancel application
      </button>
    );
  }
  return (
    <div className="review-confirm" role="group" aria-label="Confirm cancelling">
      <span>Discard this application? Nothing has been sent.</span>
      <button type="button" className="button button-danger" onClick={cancel} disabled={busy} aria-busy={busy}>
        Discard
      </button>
      <button type="button" className="button button-ghost" onClick={() => setConfirming(false)} disabled={busy}>
        Keep
      </button>
      {error && (
        <span className="review-confirm-error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}

type Segment = { text: string; changed: boolean };

/** Word-level diff: the words each side has that the other doesn't, by longest common subsequence. */
function diffWords(before: string, after: string): { before: Segment[]; after: Segment[] } {
  const a = before.split(/\s+/).filter(Boolean);
  const b = after.split(/\s+/).filter(Boolean);
  const lcs = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const left: Segment[] = [];
  const right: Segment[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) {
      left.push({ text: a[i++], changed: false });
      right.push({ text: b[j++], changed: false });
    } else if (j < b.length && (i === a.length || lcs[i][j + 1] >= lcs[i + 1][j])) {
      right.push({ text: b[j++], changed: true });
    } else {
      left.push({ text: a[i++], changed: true });
    }
  }
  return { before: left, after: right };
}

function Words({ segments, kind }: { segments: Segment[]; kind: "removed" | "added" }) {
  return (
    <>
      {segments.map((s, i) => (
        <span key={i}>
          {i > 0 && " "}
          {s.changed ? <mark className={`diff-${kind}`}>{s.text}</mark> : s.text}
        </span>
      ))}
    </>
  );
}

function SummaryDiff({ master, tailored }: { master: string[]; tailored: string[] }) {
  const diff = diffWords(master.join("\n"), tailored.join("\n"));
  return (
    <section className="panel" aria-labelledby="summary-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="summary-heading">
          Summary
        </h2>
      </div>
      <div className="diff-columns">
        <div className="diff-side">
          <h3 className="diff-side-title">Master</h3>
          <p>
            <Words segments={diff.before} kind="removed" />
          </p>
        </div>
        <div className="diff-side">
          <h3 className="diff-side-title">Tailored</h3>
          <p>
            <Words segments={diff.after} kind="added" />
          </p>
        </div>
      </div>
    </section>
  );
}

function SkillsDiff({ master, tailored }: { master: SkillLine[]; tailored: SkillLine[] }) {
  const key = (s: string) => s.toLowerCase();
  return (
    <section className="panel" aria-labelledby="skills-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="skills-heading">
          Skills
        </h2>
        <span className="diff-legend">
          <mark className="diff-added">added</mark> <mark className="diff-removed">left out</mark>
        </span>
      </div>
      <div className="diff-columns">
        {(["Master", "Tailored"] as const).map((side) => (
          <div className="diff-side" key={side}>
            <h3 className="diff-side-title">{side}</h3>
            {(side === "Master" ? master : tailored).map((line, index) => {
              const other = new Set((side === "Master" ? tailored : master)[index]?.skills.map(key) ?? []);
              return (
                <p className="diff-skill-line" key={index}>
                  {line.label && <span className="diff-skill-label">{line.label}:</span>}
                  {line.skills.map((skill) => {
                    const changed = !other.has(key(skill));
                    const kind = side === "Master" ? "removed" : "added";
                    return (
                      <span key={skill} className={`skill${changed ? ` diff-${kind}` : ""}`}>
                        {skill}
                      </span>
                    );
                  })}
                </p>
              );
            })}
          </div>
        ))}
      </div>
    </section>
  );
}

function BulletsDiff({ bullets }: { bullets: BulletEdit[] }) {
  const shown = bullets.filter((b) => b.tailored !== b.master || b.reverted);
  return (
    <section className="panel" aria-labelledby="bullets-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="bullets-heading">
          Experience bullets
        </h2>
        <span className="count count-small">
          {bullets.filter((b) => b.tailored !== b.master).length} of {bullets.length} reworded
        </span>
      </div>
      {shown.length === 0 ? (
        <p className="panel-empty bullet-empty">Every bullet already fit this job, so none were reworded.</p>
      ) : (
        <ul className="bullet-diffs">
          {shown.map((b) => {
            const diff = diffWords(b.master, b.tailored);
            return (
              <li className="bullet-diff" key={b.index}>
                <div className="diff-columns">
                  <div className="diff-side">
                    <h3 className="diff-side-title">Master</h3>
                    <p>
                      {b.label && <strong>{b.label}: </strong>}
                      <Words segments={diff.before} kind="removed" />
                    </p>
                  </div>
                  <div className="diff-side">
                    <h3 className="diff-side-title">Tailored</h3>
                    <p>
                      {b.label && <strong>{b.label}: </strong>}
                      <Words segments={diff.after} kind="added" />
                    </p>
                  </div>
                </div>
                {b.reverted && (
                  <p className="bullet-reverted" role="note">
                    <AlertIcon />
                    <span>
                      Kept the original. {b.reverted.reason} The rejected rewrite was: “{b.reverted.text}”
                    </span>
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function Coverage({
  coverage,
  fitScore,
}: {
  coverage: TailoredResume["coverage"];
  fitScore: TailoredResume["fit_score"];
}) {
  const percent = (n: number) => (coverage.total ? Math.round((n / coverage.total) * 100) : 0);
  return (
    <section className="panel" aria-labelledby="coverage-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="coverage-heading">
          {fitScore ? "Fit score and keyword coverage" : "Keyword coverage"}
        </h2>
      </div>
      <div className="panel-body">
        {fitScore && (
          <p className="coverage-numbers" aria-label="Fit score">
            <span>
              Fit <strong>{fitScore.before ?? "–"}</strong> before
            </span>
            <span aria-hidden="true">→</span>
            <span>
              <strong>{fitScore.after ?? "–"}</strong> after
            </span>
            {fitScore.after === null && <span className="panel-empty">The tailored resume couldn't be scored.</span>}
          </p>
        )}
        <p className="coverage-numbers">
          <span>
            <strong>{coverage.before}</strong> of {coverage.total} before ({percent(coverage.before)}%)
          </span>
          <span aria-hidden="true">→</span>
          <span>
            <strong>{coverage.after}</strong> of {coverage.total} after ({percent(coverage.after)}%)
          </span>
        </p>
        <p className="panel-empty">The posting's key skills and qualifications your resume mentions.</p>
        <div className="keywords">
          {coverage.keywords.map((k) => (
            <span
              key={k.keyword}
              className={`keyword ${k.after ? "keyword-matched" : "keyword-missing"}`}
              title={k.before ? "Already in your master resume" : k.after ? "Added by tailoring" : "Not in your resume"}
            >
              {k.after && <CheckIcon />}
              {k.keyword}
              {!k.before && k.after && <span className="keyword-new">new</span>}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
