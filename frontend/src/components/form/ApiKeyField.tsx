import { useState, type ReactNode } from "react";
import type { StoredSecret } from "../../types/searchSettings";
import { KeyIcon } from "../icons";

export function ApiKeyField({
  label,
  placeholder,
  stored,
  onSave,
  children,
}: {
  label: string;
  placeholder: string;
  stored: StoredSecret;
  onSave: (key: string) => Promise<void>;
  children: ReactNode;
}) {
  const [editing, setEditing] = useState(!stored.set);
  const [key, setKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await onSave(key);
      setKey("");
      setEditing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="field api-key">
      <div className="field-label">{label}</div>
      {editing ? (
        <form
          className="api-key-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (key.trim() && !saving) void save();
          }}
        >
          <input
            className="text-input"
            type="password"
            autoComplete="off"
            aria-label={label}
            placeholder={placeholder}
            value={key}
            onChange={(event) => setKey(event.target.value)}
          />
          <button type="submit" className="button button-secondary button-small" disabled={!key.trim() || saving}>
            {saving ? "Saving…" : "Save key"}
          </button>
          {stored.set && (
            <button type="button" className="button button-ghost" onClick={() => setEditing(false)}>
              Cancel
            </button>
          )}
        </form>
      ) : (
        <div className="api-key-saved">
          <KeyIcon />
          <span>
            Key ending in <code>{stored.last4}</code>
          </span>
          <button type="button" className="button button-ghost" onClick={() => setEditing(true)}>
            Replace
          </button>
        </div>
      )}
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
      <p className="field-hint">{children}</p>
    </div>
  );
}
