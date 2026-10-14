import type { CoverLetter } from "../types/application";
import { AlertIcon } from "./icons";

export function CoverLetterPanel({
  letter,
  draft,
  onChange,
  onSave,
  onUndo,
  saving,
  error,
}: {
  letter: CoverLetter;
  draft: string;
  onChange: (draft: string) => void;
  onSave: () => void;
  onUndo: () => void;
  saving: boolean;
  error: string | null;
}) {
  const dirty = draft.trim() !== letter.text;
  return (
    <section className="panel" aria-labelledby="cover-letter-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="cover-letter-heading">
          Cover letter
        </h2>
        {dirty && <span className="review-unsaved">Unsaved changes</span>}
        {letter.pdf_url && !dirty && (
          <a className="badge badge-link" href={letter.pdf_url} target="_blank" rel="noreferrer">
            View PDF
          </a>
        )}
      </div>
      <div className="panel-body">
        <p className="field-hint">
          Written from your resume and the job description only. It's{" "}
          {letter.pdf_url ? "uploaded as a PDF" : "pasted into the form"} as you leave it here.
        </p>
        <textarea
          aria-label="Cover letter"
          className="text-input cover-letter-input"
          rows={14}
          value={draft}
          onChange={(e) => onChange(e.target.value)}
        />
        {error && (
          <div className="notice notice-error" role="alert">
            <AlertIcon />
            <span className="notice-text">{error}</span>
          </div>
        )}
        <div className="panel-actions">
          <button type="button" className="button button-ghost" onClick={onUndo} disabled={!dirty || saving}>
            Undo changes
          </button>
          <button
            type="button"
            className="button button-primary"
            onClick={onSave}
            disabled={!dirty || saving}
            aria-busy={saving}
          >
            {saving && <span className="spinner" aria-hidden="true" />}
            Save cover letter
          </button>
        </div>
      </div>
    </section>
  );
}
