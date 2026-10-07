export type Job = {
  id: number;
  platform: string;
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const listJobs = () => request<Job[]>("/api/jobs");

export const startRun = () => request<Run>("/api/runs", { method: "POST" });
