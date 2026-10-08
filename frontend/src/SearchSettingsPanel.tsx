import { useEffect, useState, type KeyboardEvent, type ReactNode } from "react";
import {
  getSearchSettings,
  saveSearchApiKey,
  saveSearchSettings,
  type Platform,
  type SearchSettings,
  type SearchSettingsInput,
  type Seniority,
  type WorkMode,
} from "./api";
import { KeyIcon, SlidersIcon } from "./icons";

const WORK_MODES: { id: WorkMode; label: string }[] = [
  { id: "remote", label: "Remote" },
  { id: "hybrid", label: "Hybrid" },
  { id: "onsite", label: "On-site" },
];

const SEARCH_API_SIGNUP = "https://brave.com/search/api/";

const SENIORITIES: { id: Seniority; label: string }[] = [
  { id: "intern", label: "Intern" },
  { id: "junior", label: "Junior" },
  { id: "mid", label: "Mid-level" },
  { id: "senior", label: "Senior" },
  { id: "staff", label: "Staff" },
  { id: "principal", label: "Principal" },
];

function toInput(settings: SearchSettings): SearchSettingsInput {
  const { roles, locations, work_modes, platforms } = settings;
  const { excluded_keywords, seniority, years_experience, needs_sponsorship, min_salary } = settings;
  return {
    roles,
    locations,
    work_modes,
    platforms,
    excluded_keywords,
    seniority,
    years_experience,
    needs_sponsorship,
    min_salary,
  };
}

function activeMoreFilters(input: SearchSettingsInput): number {
  return [
    input.excluded_keywords.length > 0,
    input.seniority !== null,
    input.years_experience !== null,
    input.needs_sponsorship,
    input.min_salary !== null,
  ].filter(Boolean).length;
}

function parseWholeNumber(text: string): number | null {
  const digits = text.replace(/\D/g, "");
  return digits === "" ? null : Number(digits);
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

        <MoreFilters draft={draft} onChange={edit} />

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

function MoreFilters({
  draft,
  onChange,
}: {
  draft: SearchSettingsInput;
  onChange: (change: Partial<SearchSettingsInput>) => void;
}) {
  const active = activeMoreFilters(draft);
  const [open, setOpen] = useState(active > 0);

  return (
    <div className="more-filters">
      <button
        type="button"
        className="more-filters-toggle"
        aria-expanded={open}
        aria-controls="more-filters-body"
        onClick={() => setOpen(!open)}
      >
        <span>More filters</span>
        {active > 0 && <span className="count count-small">{active} on</span>}
        <ChevronIcon open={open} />
      </button>
      <div className="more-filters-body" id="more-filters-body" hidden={!open}>
        <Field label="Excluded title keywords" hint="Drop jobs whose title contains any of these.">
          <TermInput
            label="Excluded keywords"
            terms={draft.excluded_keywords}
            placeholder="e.g. Manager, Principal"
            onChange={(excluded_keywords) => onChange({ excluded_keywords })}
          />
        </Field>

        <Field
          label="Seniority"
          htmlFor="seniority"
          hint="Drops titles two or more levels above or below yours. Titles that don't state a level are kept."
        >
          <select
            id="seniority"
            className="text-input"
            value={draft.seniority ?? ""}
            onChange={(event) => onChange({ seniority: (event.target.value || null) as Seniority | null })}
          >
            <option value="">Any level</option>
            {SENIORITIES.map((level) => (
              <option key={level.id} value={level.id}>
                {level.label}
              </option>
            ))}
          </select>
        </Field>

        <Field
          label="Years of experience"
          htmlFor="years-experience"
          hint="Drops postings asking for far more years than you have, or ranges far below it."
        >
          <input
            id="years-experience"
            className="text-input"
            inputMode="numeric"
            placeholder="Not set"
            value={draft.years_experience ?? ""}
            onChange={(event) => {
              const years = parseWholeNumber(event.target.value);
              onChange({ years_experience: years === null ? null : Math.min(years, 50) });
            }}
          />
        </Field>

        <Field
          label="Minimum salary"
          htmlFor="min-salary"
          hint="Yearly, in USD. Only applies when a posting lists pay; postings without pay are kept."
        >
          <div className="affix-input">
            <span aria-hidden="true">$</span>
            <input
              id="min-salary"
              inputMode="numeric"
              placeholder="Not set"
              value={draft.min_salary === null ? "" : draft.min_salary.toLocaleString("en-US")}
              onChange={(event) => {
                const salary = parseWholeNumber(event.target.value);
                onChange({ min_salary: salary === null ? null : Math.min(salary, 10_000_000) });
              }}
            />
          </div>
        </Field>

        <div className="field">
          <label className="switch-row switch-row-plain">
            <span>I need visa sponsorship</span>
            <input
              type="checkbox"
              className="switch"
              checked={draft.needs_sponsorship}
              onChange={(event) => onChange({ needs_sponsorship: event.target.checked })}
            />
          </label>
          <p className="field-hint">Drops postings that say they can't sponsor a visa.</p>
        </div>
      </div>
    </div>
  );
}

function SettingsSummary({ settings }: { settings: SearchSettings }) {
  const modes = WORK_MODES.filter((m) => settings.work_modes.includes(m.id)).map((m) => m.label);
  const platforms = settings.available_platforms.filter((p) => settings.platforms.includes(p.id)).map((p) => p.name);
  const more = activeMoreFilters(settings);
  const lines = [
    settings.roles.join(", "),
    [...settings.locations, ...modes].join(" · "),
    platforms.join(", "),
    more > 0 && `${more} more ${more === 1 ? "filter" : "filters"} on`,
  ].filter((line): line is string => Boolean(line));
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

export function Field({
  label,
  hint,
  htmlFor,
  children,
}: {
  label: string;
  hint?: string;
  htmlFor?: string;
  children: ReactNode;
}) {
  return (
    <div className="field">
      {htmlFor ? (
        <label className="field-label" htmlFor={htmlFor}>
          {label}
        </label>
      ) : (
        <div className="field-label">{label}</div>
      )}
      {children}
      {hint && <p className="field-hint">{hint}</p>}
    </div>
  );
}

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
