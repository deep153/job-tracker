import { useState } from "react";
import { setCompanyBlocked, type Company } from "./api";
import { PLATFORM_LABELS, companyName, fullDate } from "./format";
import { AlertIcon, BuildingIcon } from "./icons";

export function CompaniesPanel({
  companies,
  onChange,
}: {
  companies: Company[];
  onChange: (company: Company) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const active = companies.filter((c) => !c.blocked);
  const blocked = companies.filter((c) => c.blocked);

  async function setBlocked(company: Company, value: boolean) {
    setError(null);
    try {
      onChange(await setCompanyBlocked(company.id, value));
    } catch (e) {
      setError(`Couldn't update ${companyName(company.board_id)}. ${(e as Error).message}`);
    }
  }

  return (
    <section className="panel" aria-labelledby="companies-heading">
      <header className="panel-header">
        <BuildingIcon />
        <h2 id="companies-heading">Companies</h2>
        {companies.length > 0 && <span className="count count-small">{active.length}</span>}
      </header>
      <div className="panel-body panel-body-scroll">
        {error && (
          <p className="field-error" role="alert">
            {error}
          </p>
        )}
        {companies.length === 0 ? (
          <p className="panel-empty">
            Companies are found automatically from your search settings each time you click Run.
          </p>
        ) : (
          <>
            <ul className="company-list">
              {active.map((company) => (
                <CompanyRow key={company.id} company={company} onToggle={() => setBlocked(company, true)} />
              ))}
            </ul>
            {blocked.length > 0 && (
              <>
                <div className="company-group-label">Blocked · never fetched</div>
                <ul className="company-list">
                  {blocked.map((company) => (
                    <CompanyRow key={company.id} company={company} onToggle={() => setBlocked(company, false)} />
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function CompanyRow({ company, onToggle }: { company: Company; onToggle: () => void }) {
  const name = companyName(company.board_id);
  const details = [
    `Found by search on ${fullDate(company.discovered_at)}`,
    `Query: ${company.discovered_query}`,
    company.last_fetched_at && `Last fetched ${fullDate(company.last_fetched_at)}`,
  ]
    .filter(Boolean)
    .join("\n");
  return (
    <li className={`company${company.blocked ? " is-blocked" : ""}`}>
      <div className="company-main" title={details}>
        <span className="company-name">{name}</span>
        <span className="company-meta">
          {PLATFORM_LABELS[company.platform]}
          {!company.blocked && ` · ${company.open_jobs} open`}
        </span>
      </div>
      {company.last_error && !company.blocked && (
        <span className="company-error" title={company.last_error} aria-label={`Last fetch failed: ${company.last_error}`}>
          <AlertIcon />
        </span>
      )}
      <button type="button" className="button button-ghost button-tiny" onClick={onToggle}>
        {company.blocked ? "Unblock" : "Block"}
        <span className="visually-hidden"> {name}</span>
      </button>
    </li>
  );
}
