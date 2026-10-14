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
  if (question.source === "cover_letter") return <span className="badge badge-green">Cover letter</span>;
  if (question.source === "ai") return <span className="badge badge-ai">AI-drafted</span>;
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
  if (question.source === "cover_letter") {
    return (
      <p id={id} className="question-file">
        Your cover letter (edit it below) is {question.kind === "file" ? "uploaded as a PDF" : "pasted"} here.
      </p>
    );
  }
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

function sentAnswer(question: FormQuestion): string {
  if (question.source === "cover_letter") return "Your cover letter";
  if (question.kind === "file") return question.source === "resume" ? "Your tailored resume PDF" : "Left empty";
  return question.answer ?? "Left empty";
}

/** The answers as they were sent, read-only. */
export function SentAnswersPanel({ questions }: { questions: FormQuestion[] }) {
  return (
    <section className="panel" aria-labelledby="sent-answers-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="sent-answers-heading">
          Answers you sent
        </h2>
      </div>
      <div className="panel-body">
        {questions.length === 0 && <p className="panel-empty">The form had no questions.</p>}
        <dl className="sent-answers">
          {questions.map((question) => (
            <div className="sent-answer" key={question.key}>
              <dt className="question-header">
                <span className="field-label">{question.label}</span>
                {question.answer !== null || question.kind === "file" || question.source === "cover_letter" ? (
                  <SourceBadge question={question} />
                ) : null}
              </dt>
              <dd className={question.answer === null && question.kind !== "file" ? "sent-answer-empty" : undefined}>
                {sentAnswer(question)}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

export function QuestionsPanel({
  questions,
  draft,
  onChange,
  onSave,
  onUndo,
  onSaveToBank,
  saving,
  savingToBank,
  error,
}: {
  questions: FormQuestion[];
  draft: AnswerDraft;
  onChange: (draft: AnswerDraft) => void;
  onSave: () => void;
  onUndo: () => void;
  onSaveToBank: (key: string) => void;
  saving: boolean;
  /** The question whose answer is being saved into the answer bank. */
  savingToBank: string | null;
  error: string | null;
}) {
  const changed = changedAnswers(questions, draft);
  const dirty = Object.keys(changed).length > 0;
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
            {question.eeo && question.needs_input && (
              <p className="question-note">
                Voluntary self-identification is answered only from your saved choices, never by AI. Choose an answer
                (declining is fine).
              </p>
            )}
            {(question.source === "you" || question.source === "ai") && !(question.key in changed) && (
              <button
                type="button"
                className="button button-ghost button-tiny question-save"
                onClick={() => onSaveToBank(question.key)}
                disabled={savingToBank !== null || saving}
                aria-busy={savingToBank === question.key}
              >
                {savingToBank === question.key && <span className="spinner spinner-dark" aria-hidden="true" />}
                Save to answer bank
              </button>
            )}
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
