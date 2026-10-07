export type Platform = "greenhouse";

export type Job = {
  id: number;
  platform: Platform;
  company: string;
  external_id: string;
  title: string;
  locations: string[];
  remote: boolean | null;
  salary: { min: number | null; max: number | null; currency: string | null } | null;
  description: string;
  posting_url: string;
  application_url: string;
  updated_at: string;
};

export type RunStatus = "running" | "finished" | "failed" | "interrupted";

export type BoardError = {
  platform: Platform;
  board_id: string;
  message: string;
};

export type Run = {
  id: number;
  status: RunStatus;
  started_at: string;
  finished_at: string | null;
  companies_total: number;
  companies_fetched: number;
  new_jobs: number;
  updated_jobs: number;
  closed_jobs: number;
  errors: BoardError[];
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
    const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${response.status}).`;
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export const listJobs = () => request<Job[]>("/api/jobs");

export const startRun = () => request<Run>("/api/runs", { method: "POST" });

export const getRun = (id: number) => request<Run>(`/api/runs/${id}`);

export const listRuns = () => request<Run[]>("/api/runs");
