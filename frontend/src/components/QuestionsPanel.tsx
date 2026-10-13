import type { FormQuestion } from "../types/application";
import { AlertIcon } from "./icons";

export type AnswerDraft = Record<string, string>;

export function answerDraft(questions: FormQuestion[]): AnswerDraft {
  return Object.fromEntries(questions.map((q) => [q.key, q.answer ?? ""]));
}

/** The answers I changed from the saved ones, by question key. */
export function changedAnswers(questions: FormQuestion[], draft: AnswerDraft): AnswerDraft {
  return Object.fromEntries(
    questions.filter((q) => (draft[q.key] ?? "").trim() !== (q.answer ?? "")).map((q) => [q.key, draft[q.key]]),
  );
}

function choices(question: FormQuestion): string[] {
  if (question.options.length) return question.options;
  return question.kind === "checkbox" ? ["Yes", "No"] : [];
}

function SourceBadge({ question }: { question: FormQuestion }) {
  if (question.needs_input) return <span className="badge badge-warning">Needs input</span>;
  if (question.source === "bank") return <span className="badge badge-green">From answer bank</span>;
  if (question.source === "resume") return <span className="badge badge-green">Tailored resume</span>;
  if (question.source === "you") return <span className="badge">Your answer</span>;
  return <span className="badge badge-muted">Optional</span>;
}

function AnswerInput({
  question,
  value,
  onChange,
}: {
  question: FormQuestion;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = `question-${question.key}`;
  if (question.kind === "file") {
    return (
      <p id={id} className="question-file">
        {question.source === "resume"
          ? "Your tailored resume PDF is uploaded here."
          : "Uploading other files isn't supported yet, so this is left empty."}
      </p>
    );
  }
  const options = choices(question);
  if (options.length) {
    return (
      <select id={id} className="text-input" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Choose…</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }
  if (question.kind === "textarea") {
    return (
      <textarea
        id={id}
        className="text-input review-summary-input"
        rows={3}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  return <input id={id} className="text-input" value={value} onChange={(e) => onChange(e.target.value)} />;
}

export function QuestionsPanel({
  questions,
  draft,
  onChange,
  onSave,
  onUndo,
  saving,
  error,
}: {
  questions: FormQuestion[];
  draft: AnswerDraft;
  onChange: (draft: AnswerDraft) => void;
  onSave: () => void;
  onUndo: () => void;
  saving: boolean;
  error: string | null;
}) {
  const dirty = Object.keys(changedAnswers(questions, draft)).length > 0;
  const needInput = questions.filter((q) => q.needs_input).length;
  return (
    <section className="panel" aria-labelledby="questions-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="questions-heading">
          Application questions
        </h2>
        {needInput > 0 && (
          <span className="badge badge-warning">
            {needInput} {needInput === 1 ? "needs" : "need"} input
          </span>
        )}
        {dirty && <span className="review-unsaved">Unsaved changes</span>}
      </div>
      <div className="panel-body">
        {questions.length === 0 && <p className="panel-empty">This form has no questions to answer.</p>}
        {questions.map((question) => (
          <div className="field question" key={question.key}>
            <div className="question-header">
              <label className="field-label" htmlFor={`question-${question.key}`}>
                {question.label}
                {question.required && (
                  <span className="question-required" aria-label="required">
                    *
                  </span>
                )}
              </label>
              <SourceBadge question={question} />
            </div>
            <AnswerInput
              question={question}
              value={draft[question.key] ?? ""}
              onChange={(value) => onChange({ ...draft, [question.key]: value })}
            />
          </div>
        ))}
        {error && (
          <div className="notice notice-error" role="alert">
            <AlertIcon />
            <span className="notice-text">{error}</span>
          </div>
        )}
        {questions.length > 0 && (
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
              Save answers
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
