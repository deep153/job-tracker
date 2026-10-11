import type { Company } from "../types/company";
import type { JobQuery, JobSort } from "../types/job";
import { companyName } from "../utils/format";

export const NO_FILTERS: JobQuery = { company: null, location: "", posted_within_days: null, sort: "score" };

const POSTED_OPTIONS: { days: number | null; label: string }[] = [
  { days: null, label: "Any time" },
  { days: 1, label: "Past 24 hours" },
  { days: 7, label: "Past week" },
  { days: 30, label: "Past month" },
];

export function hasFilters(query: JobQuery): boolean {
  return query.company !== null || query.location.trim() !== "" || query.posted_within_days !== null;
}

export function JobFilters({
  query,
  companies,
  onChange,
}: {
  query: JobQuery;
  companies: Company[];
  onChange: (query: JobQuery) => void;
}) {
  const boards = [...new Set(companies.filter((c) => !c.blocked && c.open_jobs > 0).map((c) => c.board_id))].sort();
  const update = (changes: Partial<JobQuery>) => onChange({ ...query, ...changes });

  return (
    <div className="job-filters" role="search" aria-label="Filter jobs">
      <label className="job-filter">
        <span className="job-filter-label">Company</span>
        <select
          className="text-input"
          value={query.company ?? ""}
          onChange={(e) => update({ company: e.target.value || null })}
        >
          <option value="">All companies</option>
          {boards.map((board) => (
            <option key={board} value={board}>
              {companyName(board)}
            </option>
          ))}
        </select>
      </label>
      <label className="job-filter">
        <span className="job-filter-label">Location</span>
        <input
          className="text-input"
          type="search"
          placeholder="Any location"
          value={query.location}
          onChange={(e) => update({ location: e.target.value })}
        />
      </label>
      <label className="job-filter">
        <span className="job-filter-label">Updated</span>
        <select
          className="text-input"
          value={query.posted_within_days ?? ""}
          onChange={(e) => update({ posted_within_days: e.target.value ? Number(e.target.value) : null })}
        >
          {POSTED_OPTIONS.map((option) => (
            <option key={option.label} value={option.days ?? ""}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="job-filter">
        <span className="job-filter-label">Sort by</span>
        <select
          className="text-input"
          value={query.sort}
          onChange={(e) => update({ sort: e.target.value as JobSort })}
        >
          <option value="score">Best fit</option>
          <option value="posted">Recently updated</option>
        </select>
      </label>
      {hasFilters(query) && (
        <button
          type="button"
          className="button button-ghost job-filters-clear"
          onClick={() => onChange({ ...NO_FILTERS, sort: query.sort })}
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
