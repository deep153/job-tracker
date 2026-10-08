import { useEffect, useState } from "react";
import {
  getAiCosts,
  getAiSettings,
  saveAnthropicApiKey,
  saveModels,
  type AiCosts,
  type AiSettings,
} from "./api";
import { formatCost, fullDate, timeAgo } from "./format";
import { AlertIcon } from "./icons";
import { ApiKeyField, Field } from "./SearchSettingsPanel";
import { Topbar } from "./Topbar";

const ANTHROPIC_CONSOLE = "https://console.anthropic.com/settings/keys";

const KIND_LABELS: Record<string, string> = { scoring: "Fit scoring", tailoring: "Resume tailoring" };

export function SettingsPage() {
  const [settings, setSettings] = useState<AiSettings | null>(null);
  const [costs, setCosts] = useState<AiCosts | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  async function load() {
    setLoadError(null);
    try {
      const [ai, spent] = await Promise.all([getAiSettings(), getAiCosts()]);
      setSettings(ai);
      setCosts(spent);
    } catch (e) {
      setLoadError((e as Error).message);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="app">
      <Topbar page="settings" />
      <main className="page page-narrow">
        <div className="page-heading">
          <h1>Settings</h1>
          <p className="subtitle">
            Job Tracker uses Claude to score how well each job fits your resume, and later to tailor your resume.
            Everything stays on this machine except what's sent to Claude.
          </p>
        </div>

        {loadError && (
          <div className="notice notice-error" role="alert">
            <AlertIcon />
            <span className="notice-text">{loadError}</span>
            <button className="button button-ghost" onClick={load}>
              Retry
            </button>
          </div>
        )}

        {settings === null ? (
          !loadError && <div className="skeleton settings-skeleton" aria-busy="true" aria-label="Loading settings" />
        ) : (
          <>
            <section className="panel" aria-labelledby="claude-heading">
              <div className="panel-header">
                <h2 className="panel-title" id="claude-heading">
                  Claude
                </h2>
              </div>
              <div className="panel-body">
                <ApiKeyField
                  label="Anthropic API key"
                  placeholder="Paste your Anthropic API key (sk-ant-…)"
                  stored={settings.anthropic_api_key}
                  onSave={async (key) => setSettings(await saveAnthropicApiKey(key))}
                >
                  Stored only on this machine and sent only to Anthropic.{" "}
                  <a href={ANTHROPIC_CONSOLE} target="_blank" rel="noreferrer">
                    Get a key
                  </a>
                </ApiKeyField>
                <ModelsForm
                  key={`${settings.scoring_model}|${settings.tailoring_model}`}
                  settings={settings}
                  onSaved={setSettings}
                />
              </div>
            </section>
            {costs && <CostSummary costs={costs} />}
          </>
        )}
      </main>
    </div>
  );
}

function ModelsForm({ settings, onSaved }: { settings: AiSettings; onSaved: (settings: AiSettings) => void }) {
  const [scoring, setScoring] = useState(settings.scoring_model);
  const [tailoring, setTailoring] = useState(settings.tailoring_model);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = scoring.trim() !== settings.scoring_model || tailoring.trim() !== settings.tailoring_model;

  async function save() {
    setSaving(true);
    setError(null);
    try {
      onSaved(await saveModels(scoring, tailoring));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      className="models-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (dirty && !saving) void save();
      }}
    >
      <datalist id="suggested-models">
        {settings.suggested_models.map((model) => (
          <option key={model} value={model} />
        ))}
      </datalist>
      <Field
        label="Scoring model"
        htmlFor="scoring-model"
        hint="Scores every new job, so a fast, inexpensive Haiku model is the default."
      >
        <input
          id="scoring-model"
          className="text-input"
          list="suggested-models"
          spellCheck={false}
          value={scoring}
          onChange={(event) => setScoring(event.target.value)}
        />
      </Field>
      <Field
        label="Tailoring model"
        htmlFor="tailoring-model"
        hint="Rewrites your Summary for each application, so a stronger Sonnet model is the default."
      >
        <input
          id="tailoring-model"
          className="text-input"
          list="suggested-models"
          spellCheck={false}
          value={tailoring}
          onChange={(event) => setTailoring(event.target.value)}
        />
      </Field>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
      <div className="panel-actions">
        <span className="save-status" aria-live="polite">
          {dirty ? "Unsaved changes" : ""}
        </span>
        <button type="submit" className="button button-primary button-small" disabled={!dirty || saving}>
          {saving ? "Saving…" : "Save models"}
        </button>
      </div>
    </form>
  );
}

function CostSummary({ costs }: { costs: AiCosts }) {
  return (
    <section className="panel" aria-labelledby="costs-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="costs-heading">
          AI cost
        </h2>
        <span className="cost-total">{formatCost(costs.total_usd)} so far</span>
      </div>
      <div className="panel-body">
        {costs.by_kind.length === 0 ? (
          <p className="panel-empty">No AI calls yet. Each run's estimated cost shows up here.</p>
        ) : (
          <>
            <table className="cost-table">
              <thead>
                <tr>
                  <th scope="col">Use</th>
                  <th scope="col">Calls</th>
                  <th scope="col">Tokens in / out</th>
                  <th scope="col">Cost</th>
                </tr>
              </thead>
              <tbody>
                {costs.by_kind.map((row) => (
                  <tr key={row.kind}>
                    <td>{KIND_LABELS[row.kind] ?? row.kind}</td>
                    <td>{row.calls.toLocaleString()}</td>
                    <td>
                      {row.input_tokens.toLocaleString()} / {row.output_tokens.toLocaleString()}
                    </td>
                    <td>{formatCost(row.cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {costs.recent_runs.length > 0 && (
              <table className="cost-table">
                <caption>Recent runs</caption>
                <thead>
                  <tr>
                    <th scope="col">Run</th>
                    <th scope="col">Started</th>
                    <th scope="col">Jobs scored</th>
                    <th scope="col">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {costs.recent_runs.map((run) => (
                    <tr key={run.id}>
                      <td>#{run.id}</td>
                      <td>
                        <time dateTime={run.started_at} title={fullDate(run.started_at)}>
                          {timeAgo(run.started_at)}
                        </time>
                      </td>
                      <td>{run.scored_jobs.toLocaleString()}</td>
                      <td>{formatCost(run.ai_cost_usd)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
        <p className="field-hint">
          Estimated from token counts and Anthropic's list prices; your Anthropic console shows the exact amount.
        </p>
      </div>
    </section>
  );
}
