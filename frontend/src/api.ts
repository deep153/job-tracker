export type Platform = "greenhouse" | "lever" | "ashby";

export type WorkMode = "remote" | "hybrid" | "onsite";

export type Seniority = "intern" | "junior" | "mid" | "senior" | "staff" | "principal";

export type SearchSettingsInput = {
  roles: string[];
  locations: string[];
  work_modes: WorkMode[];
  platforms: Platform[];
  excluded_keywords: string[];
  seniority: Seniority | null;
  years_experience: number | null;
  needs_sponsorship: boolean;
  min_salary: number | null;
};

export type FilterRule = "role" | "excluded_keyword" | "location" | "seniority" | "experience" | "sponsorship" | "salary";

export type SearchSettings = SearchSettingsInput & {
  available_platforms: { id: Platform; name: string; supported: boolean }[];
  search_api_key: { set: boolean; last4: string | null };
  missing: string[];
  ready: boolean;
};

export type Company = {
  id: number;
  platform: Platform;
  board_id: string;
  discovered_at: string;
  discovered_query: string;
  blocked: boolean;
  last_fetched_at: string | null;
  last_error: string | null;
  open_jobs: number;
};

export type Job = {
  id: number;
  platform: Platform;
  company: string;
  external_id: string;
  title: string;
  locations: string[];
  remote: boolean | null;
  work_mode: WorkMode | null;
  salary: { min: number | null; max: number | null; currency: string | null } | null;
  description: string;
  posting_url: string;
  application_url: string;
  updated_at: string;
};

export type FilteredJob = Job & { rejection: { rule: FilterRule; reason: string } };

export type RunStatus = "running" | "finished" | "failed" | "interrupted";

export type RunError =
  | { kind: "board"; platform: Platform; board_id: string; message: string }
  | { kind: "search"; platform: null; board_id: null; message: string };

export type Run = {
  id: number;
  status: RunStatus;
  stage: "discovering" | "fetching";
  started_at: string;
  finished_at: string | null;
  search_queries: number;
  search_queries_capped: boolean;
  companies_discovered: number;
  companies_total: number;
  companies_fetched: number;
  new_jobs: number;
  updated_jobs: number;
  closed_jobs: number;
  filtered_out: Record<FilterRule, number>;
  errors: RunError[];
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message);
  }
}

const UNREACHABLE = "Can't reach the Job Tracker server. Make sure the backend is running.";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError(UNREACHABLE, null);
  }
  // The dev server's proxy answers 502-504 when the backend isn't running.
  if ([502, 503, 504].includes(response.status)) {
    throw new ApiError(UNREACHABLE, response.status);
  }
  if (!response.ok) {
    if (response.status >= 500) {
      throw new ApiError(
        "The Job Tracker server ran into a problem. Check the backend logs and try again.",
        response.status,
      );
    }
    const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    throw new ApiError(errorDetail(body?.detail) ?? `Request failed (${response.status}).`, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

/** FastAPI sends a string for our own errors and a list of field errors for request validation. */
function errorDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === "string") {
    return (detail[0].msg as string).replace(/^Value error, /, "");
  }
  return null;
}

function sendJson(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export const getSearchSettings = () => request<SearchSettings>("/api/search-settings");

export const saveSearchSettings = (settings: SearchSettingsInput) =>
  request<SearchSettings>("/api/search-settings", sendJson("PUT", settings));

export const saveSearchApiKey = (key: string) =>
  request<void>("/api/settings/search-api-key", sendJson("PUT", { key }));

export const listCompanies = () => request<Company[]>("/api/companies");

export const setCompanyBlocked = (id: number, blocked: boolean) =>
  request<Company>(`/api/companies/${id}`, sendJson("PATCH", { blocked }));

export const listJobs = () => request<Job[]>("/api/jobs");

export const listFilteredOutJobs = () => request<FilteredJob[]>("/api/jobs/filtered-out");

export const startRun = () => request<Run>("/api/runs", { method: "POST" });

export const getRun = (id: number) => request<Run>(`/api/runs/${id}`);

export const listRuns = () => request<Run[]>("/api/runs");
