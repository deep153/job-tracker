import { useEffect, useState, type KeyboardEvent, type ReactNode } from "react";
import {
  getSearchSettings,
  saveSearchApiKey,
  saveSearchSettings,
  type Platform,
  type SearchSettings,
  type SearchSettingsInput,
  type WorkMode,
} from "./api";
import { KeyIcon, SlidersIcon } from "./icons";

const WORK_MODES: { id: WorkMode; label: string }[] = [
  { id: "remote", label: "Remote" },
  { id: "hybrid", label: "Hybrid" },
  { id: "onsite", label: "On-site" },
];

const SEARCH_API_SIGNUP = "https://brave.com/search/api/";

function toInput(settings: SearchSettings): SearchSettingsInput {
  const { roles, locations, work_modes, platforms } = settings;
  return { roles, locations, work_modes, platforms };
}

function sameInput(a: SearchSettingsInput, b: SearchSettingsInput): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

function toggle<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item];
}

export function SearchSettingsPanel({
  settings,
  disabled,
  onChange,
}: {
  settings: SearchSettings;
  disabled: boolean;
  onChange: (settings: SearchSettings) => void;
}) {
  const [draft, setDraft] = useState(() => toInput(settings));
  const [expanded, setExpanded] = useState(!settings.ready);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = !sameInput(draft, toInput(settings));

  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), 2500);
    return () => clearTimeout(timer);
  }, [saved]);

  function edit(change: Partial<SearchSettingsInput>) {
    setDraft((current) => ({ ...current, ...change }));
    setSaved(false);
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const next = await saveSearchSettings(draft);
      setDraft(toInput(next));
      onChange(next);
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel" aria-labelledby="search-settings-heading">
      <h2 className="panel-heading">
        <button
          type="button"
          className="panel-header panel-toggle"
          id="search-settings-heading"
          aria-expanded={expanded}
          aria-controls="search-settings-body"
          onClick={() => setExpanded(!expanded)}
        >
          <SlidersIcon />
          <span className="panel-title">Search settings</span>
          <ChevronIcon open={expanded} />
        </button>
      </h2>
      {!expanded && <SettingsSummary settings={settings} />}

      <div className="panel-body" id="search-settings-body" hidden={!expanded}>
        <Field label="Roles" hint="Job titles to search for. Press Enter to add each one.">
          <TermInput
            label="Roles"
            terms={draft.roles}
            placeholder="e.g. Backend Engineer"
            onChange={(roles) => edit({ roles })}
          />
        </Field>

        <Field label="Locations" hint="Cities or regions you'd work in.">
          <TermInput
            label="Locations"
            terms={draft.locations}
            placeholder="e.g. New York, NY"
            onChange={(locations) => edit({ locations })}
          />
        </Field>

        <Field label="Work mode">
          <div className="toggle-group" role="group" aria-label="Work mode">
            {WORK_MODES.map((mode) => (
              <button
                key={mode.id}
                type="button"
                className="toggle"
                aria-pressed={draft.work_modes.includes(mode.id)}
                onClick={() => edit({ work_modes: toggle(draft.work_modes, mode.id) })}
              >
                {mode.label}
              </button>
            ))}
          </div>
        </Field>

        <Field label="Job boards">
          <ul className="platforms">
            {settings.available_platforms.map((platform) => (
              <li key={platform.id}>
                <label className={`switch-row${platform.supported ? "" : " is-disabled"}`}>
                  <span>
                    {platform.name}
                    {!platform.supported && <span className="badge badge-muted">Coming soon</span>}
                  </span>
                  <input
                    type="checkbox"
                    className="switch"
                    checked={draft.platforms.includes(platform.id)}
                    disabled={!platform.supported}
                    onChange={() => edit({ platforms: toggle<Platform>(draft.platforms, platform.id) })}
                  />
                </label>
              </li>
            ))}
          </ul>
        </Field>

        {error && (
          <p className="field-error" role="alert">
            {error}
          </p>
        )}
        <div className="panel-actions">
          <span className="save-status" aria-live="polite">
            {saved ? "Saved" : dirty ? "Unsaved changes" : ""}
          </span>
          {dirty && (
            <button type="button" className="button button-ghost" onClick={() => setDraft(toInput(settings))}>
              Discard
            </button>
          )}
          <button
            type="button"
            className="button button-primary button-small"
            onClick={save}
            disabled={!dirty || saving || disabled}
            title={disabled ? "Settings can't change while a run is in progress." : undefined}
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>

        <SearchApiKeyField settings={settings} onChange={onChange} />
      </div>
    </section>
  );
}

function SettingsSummary({ settings }: { settings: SearchSettings }) {
  const modes = WORK_MODES.filter((m) => settings.work_modes.includes(m.id)).map((m) => m.label);
  const platforms = settings.available_platforms.filter((p) => settings.platforms.includes(p.id)).map((p) => p.name);
  const lines = [
    settings.roles.join(", "),
    [...settings.locations, ...modes].join(" · "),
    platforms.join(", "),
  ].filter(Boolean);
  return (
    <div className="panel-summary">
      {lines.map((line) => (
        <p key={line}>{line}</p>
      ))}
      {!settings.ready && <p className="field-error">{settings.missing[0]}</p>}
    </div>
  );
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`chevron${open ? " is-open" : ""}`}
      width={16}
      height={16}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="field">
      <div className="field-label">{label}</div>
      {children}
      {hint && <p className="field-hint">{hint}</p>}
    </div>
  );
}

function TermInput({
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

function SearchApiKeyField({
  settings,
  onChange,
}: {
  settings: SearchSettings;
  onChange: (settings: SearchSettings) => void;
}) {
  const stored = settings.search_api_key;
  const [editing, setEditing] = useState(!stored.set);
  const [key, setKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await saveSearchApiKey(key);
      onChange(await getSearchSettings());
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
      <div className="field-label">Search API key</div>
      {editing ? (
        <form
          className="api-key-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (key.trim()) void save();
          }}
        >
          <input
            className="text-input"
            type="password"
            autoComplete="off"
            aria-label="Search API key"
            placeholder="Paste your Brave Search API key"
            value={key}
            onChange={(event) => setKey(event.target.value)}
            onKeyDown={(event) => {
              if (event.key !== "Enter") return;
              event.preventDefault();
              if (key.trim() && !saving) void save();
            }}
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
      <p className="field-hint">
        Used to find company job boards. Stored only on this machine.{" "}
        <a href={SEARCH_API_SIGNUP} target="_blank" rel="noreferrer">
          Get a key
        </a>
      </p>
    </div>
  );
}
