import { useEffect, useState } from "react";
import { addAnswer, deleteAnswer, listAnswers, updateAnswer } from "../api/answerBank";
import { type AnswerCategory, type BankEntry, type BankEntryIn, CATEGORY_LABELS } from "../types/answers";
import { timeAgo } from "../utils/format";
import { AlertIcon } from "./icons";

const EMPTY: BankEntryIn = { question: "", answer: "", category: "personal" };

export function AnswerBankPanel() {
  const [entries, setEntries] = useState<BankEntry[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editing, setEditing] = useState<number | null>(null);

  async function load() {
    setLoadError(null);
    try {
      setEntries(await listAnswers());
    } catch (e) {
      setLoadError((e as Error).message);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const categories = Object.keys(CATEGORY_LABELS) as AnswerCategory[];
  return (
    <section className="panel" aria-labelledby="answers-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="answers-heading">
          Answer bank
        </h2>
        {entries && <span className="count count-small">{entries.length}</span>}
      </div>
      <div className="panel-body">
        <p className="field-hint">
          Your answers to the questions application forms ask again and again. They fill in each form, matched to
          the form's questions however they're worded, and you check them before anything is sent.
        </p>
        {loadError && (
          <div className="notice notice-error" role="alert">
            <AlertIcon />
            <span className="notice-text">{loadError}</span>
            <button className="button button-ghost" onClick={load}>
              Retry
            </button>
          </div>
        )}
        {entries?.length === 0 && <p className="panel-empty">No saved answers yet. Add your first one below.</p>}
        {entries &&
          categories
            .filter((category) => entries.some((e) => e.category === category))
            .map((category) => (
              <div className="answer-group" key={category}>
                <h3 className="answer-group-title">{CATEGORY_LABELS[category]}</h3>
                <ul className="answer-list">
                  {entries
                    .filter((e) => e.category === category)
                    .map((entry) =>
                      editing === entry.id ? (
                        <li key={entry.id}>
                          <AnswerForm
                            initial={entry}
                            submitLabel="Save"
                            onSubmit={async (edited) => {
                              await updateAnswer(entry.id, edited);
                              setEditing(null);
                              await load();
                            }}
                            onCancel={() => setEditing(null)}
                          />
                        </li>
                      ) : (
                        <AnswerRow
                          key={entry.id}
                          entry={entry}
                          onEdit={() => setEditing(entry.id)}
                          onDeleted={load}
                        />
                      ),
                    )}
                </ul>
              </div>
            ))}
        {entries && (
          <div className="answer-add">
            <h3 className="answer-group-title">Add an answer</h3>
            <AnswerForm
              initial={EMPTY}
              submitLabel="Add answer"
              resetOnSubmit
              onSubmit={async (entry) => {
                await addAnswer(entry);
                await load();
              }}
            />
          </div>
        )}
      </div>
    </section>
  );
}

function AnswerRow({ entry, onEdit, onDeleted }: { entry: BankEntry; onEdit: () => void; onDeleted: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      await deleteAnswer(entry.id);
      onDeleted();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <li className="answer-row">
      <div className="answer-text">
        <span className="answer-question">{entry.question}</span>
        <span className="answer-value">{entry.answer}</span>
        <span className="answer-used">
          {entry.last_used_at ? `Last used ${timeAgo(entry.last_used_at)}` : "Not used yet"}
        </span>
        {error && (
          <span className="field-error" role="alert">
            {error}
          </span>
        )}
      </div>
      <button type="button" className="button button-ghost button-small" onClick={onEdit} disabled={busy}>
        Edit
      </button>
      <button
        type="button"
        className="button button-ghost button-small"
        onClick={remove}
        disabled={busy}
        aria-label={`Delete the answer to “${entry.question}”`}
      >
        Delete
      </button>
    </li>
  );
}

function AnswerForm({
  initial,
  submitLabel,
  resetOnSubmit = false,
  onSubmit,
  onCancel,
}: {
  initial: BankEntryIn;
  submitLabel: string;
  resetOnSubmit?: boolean;
  onSubmit: (entry: BankEntryIn) => Promise<void>;
  onCancel?: () => void;
}) {
  const [entry, setEntry] = useState<BankEntryIn>({
    question: initial.question,
    answer: initial.answer,
    category: initial.category,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const complete = entry.question.trim() !== "" && entry.answer.trim() !== "";

  function change(next: Partial<BankEntryIn>) {
    setEntry({ ...entry, ...next });
    setError(null);
  }

  return (
    <form
      className="answer-form"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!complete || saving) return;
        setSaving(true);
        setError(null);
        try {
          await onSubmit(entry);
          if (resetOnSubmit) setEntry({ ...EMPTY, category: entry.category });
        } catch (e) {
          setError((e as Error).message);
        } finally {
          setSaving(false);
        }
      }}
    >
      <label className="field">
        <span className="field-label">Question</span>
        <input
          className="text-input"
          placeholder="Are you authorized to work in the US?"
          value={entry.question}
          onChange={(e) => change({ question: e.target.value })}
        />
      </label>
      <label className="field">
        <span className="field-label">Answer</span>
        <textarea
          className="text-input review-summary-input"
          rows={2}
          value={entry.answer}
          onChange={(e) => change({ answer: e.target.value })}
        />
      </label>
      <label className="field">
        <span className="field-label">Category</span>
        <select
          className="text-input"
          value={entry.category}
          onChange={(e) => change({ category: e.target.value as AnswerCategory })}
        >
          {(Object.entries(CATEGORY_LABELS) as [AnswerCategory, string][]).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
      <div className="panel-actions">
        {onCancel && (
          <button type="button" className="button button-ghost button-small" onClick={onCancel} disabled={saving}>
            Cancel
          </button>
        )}
        <button type="submit" className="button button-primary button-small" disabled={!complete || saving}>
          {saving ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
