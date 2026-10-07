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

export type Run = {
  id: number;
  started_at: string;
  finished_at: string | null;
};

const UNREACHABLE = "Can't reach the Job Tracker server. Make sure the backend is running.";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new Error(UNREACHABLE);
  }
  // The dev server's proxy answers 502-504 when the backend isn't running.
  if ([502, 503, 504].includes(response.status)) {
    throw new Error(UNREACHABLE);
  }
  if (!response.ok) {
    throw new Error(
      response.status >= 500
        ? "The Job Tracker server ran into a problem. Check the backend logs and try again."
        : `Request failed (${response.status}).`,
    );
  }
  return response.json() as Promise<T>;
}

export const listJobs = () => request<Job[]>("/api/jobs");

export const startRun = () => request<Run>("/api/runs", { method: "POST" });
