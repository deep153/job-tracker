import { useState, type KeyboardEvent } from "react";

export function TermInput({
  label,
  terms,
  placeholder,
  onChange,
}: {
  label: string;
  terms: string[];
  placeholder: string;
  onChange: (terms: string[]) => void;
}) {
  const [text, setText] = useState("");

  function commit() {
    const term = text.trim().replace(/\s+/g, " ");
    if (term && !terms.some((t) => t.toLowerCase() === term.toLowerCase())) {
      onChange([...terms, term]);
    }
    setText("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      commit();
    } else if (event.key === "Backspace" && text === "" && terms.length > 0) {
      onChange(terms.slice(0, -1));
    }
  }

  return (
    <div className="term-input">
      {terms.map((term) => (
        <span className="chip" key={term}>
          {term}
          <button
            type="button"
            className="chip-remove"
            aria-label={`Remove ${term}`}
            onClick={() => onChange(terms.filter((t) => t !== term))}
          >
            ×
          </button>
        </span>
      ))}
      <input
        aria-label={`Add ${label.toLowerCase()}`}
        value={text}
        placeholder={terms.length === 0 ? placeholder : "Add another…"}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
        onBlur={commit}
      />
    </div>
  );
}
