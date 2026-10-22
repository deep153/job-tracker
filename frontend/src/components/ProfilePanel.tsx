import { useEffect, useState } from "react";
import { applyProfile, extractProfile } from "../api/resume";
import type { ProfileField, ProfileProposal } from "../types/profile";
import { AlertIcon, CheckIcon } from "./icons";

/** My answer to one field, and whether to save it (for a field I already have an answer to: replace it). */
type Row = { answer: string; save: boolean };

/** A field my answer bank already answers the same way (or that has nothing new to offer) needs no review. */
function settled(field: ProfileField): boolean {
  return field.current !== null && (field.value === "" || field.value === field.current);
}

function rowsFrom(proposal: ProfileProposal): Record<string, Row> {
  return Object.fromEntries(
    proposal.fields.map((f) => [f.question, { answer: f.value, save: f.current === null && f.value !== "" }]),
  );
}

export function ProfilePanel({ onClose }: { onClose: () => void }) {
  const [proposal, setProposal] = useState<ProfileProposal | null>(null);
  const [rows, setRows] = useState<Record<string, Row>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<number | null>(null);

  async function load() {
    setError(null);
    try {
      const next = await extractProfile();
      setProposal(next);
      setRows(rowsFrom(next));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function update(question: string, row: Partial<Row>) {
    setRows((current) => ({ ...current, [question]: { ...current[question], ...row } }));
  }

  async function save() {
    if (!proposal) return;
    setSaving(true);
    setError(null);
    const answers = proposal.fields
      .filter((f) => !settled(f) && rows[f.question].save && rows[f.question].answer.trim())
      .map((f) => ({ question: f.question, category: f.category, answer: rows[f.question].answer, replace: true }));
    try {
      await applyProfile(answers);
      setSaved(answers.length);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const open = proposal?.fields.filter((f) => !settled(f)) ?? [];
  const settledCount = (proposal?.fields.length ?? 0) - open.length;
  const sections = [
    { key: "resume", title: "From your resume" },
    { key: "questions", title: "Questions your resume can't answer" },
  ] as const;

  return (
    <section className="panel profile-panel" aria-labelledby="profile-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="profile-heading">
          Your profile
        </h2>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>
      <div className="panel-body">
        {saved !== null ? (
          <div className="notice notice-success" role="status">
            <CheckIcon />
            <span className="notice-text">
              Saved {saved} {saved === 1 ? "answer" : "answers"} to your answer bank. Application forms will be filled
              from them.
            </span>
            <button type="button" className="button button-ghost" onClick={onClose}>
              Done
            </button>
          </div>
        ) : (
          <>
            <p className="field-hint">
              Read from your resume. Check each answer before saving: they go into your answer bank and fill in
              application forms. Nothing is saved until you do.
            </p>
            {error && (
              <div className="notice notice-error" role="alert">
                <AlertIcon />
                <span className="notice-text">{error}</span>
                {!proposal && (
                  <button className="button button-ghost" onClick={load}>
                    Retry
                  </button>
                )}
              </div>
            )}
            {!proposal && !error && <div className="skeleton profile-skeleton" aria-busy="true" aria-label="Reading" />}
            {proposal &&
              sections.map((section) => {
                const fields = open.filter((f) => f.section === section.key);
                if (fields.length === 0) return null;
                return (
                  <fieldset className="profile-section" key={section.key}>
                    <legend className="answer-group-title">{section.title}</legend>
                    {fields.map((field) => (
                      <ProfileRow
                        key={field.question}
                        field={field}
                        row={rows[field.question]}
                        onChange={(row) => update(field.question, row)}
                      />
                    ))}
                  </fieldset>
                );
              })}
            {proposal && (
              <div className="panel-actions">
                {settledCount > 0 && (
                  <span className="save-status">
                    {settledCount} {settledCount === 1 ? "answer already matches" : "answers already match"} your answer
                    bank
                  </span>
                )}
                <button type="button" className="button button-ghost" onClick={onClose}>
                  Not now
                </button>
                <button
                  type="button"
                  className="button button-primary button-small"
                  onClick={save}
                  disabled={saving}
                  aria-busy={saving}
                >
                  {saving ? "Saving…" : "Save to answer bank"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function ProfileRow({
  field,
  row,
  onChange,
}: {
  field: ProfileField;
  row: Row;
  onChange: (row: Partial<Row>) => void;
}) {
  const id = `profile-${field.question.replace(/\W+/g, "-")}`;
  const conflict = field.current !== null;
  return (
    <div className="profile-row">
      <label className="field-label" htmlFor={id}>
        {field.question}
      </label>
      <input
        id={id}
        className="text-input"
        value={row.answer}
        disabled={conflict && !row.save}
        onChange={(e) => onChange({ answer: e.target.value, save: conflict ? row.save : e.target.value.trim() !== "" })}
      />
      <label className="profile-choice">
        <input type="checkbox" checked={row.save} onChange={(e) => onChange({ save: e.target.checked })} />
        {conflict ? `Replace my current answer “${field.current}”` : "Save"}
      </label>
    </div>
  );
}
