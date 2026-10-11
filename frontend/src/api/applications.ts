import type { Application } from "../types/application";
import { request } from "./client";

/** Starts tailoring my resume for the job, or returns the job's open application. */
export const applyToJob = (jobId: number) => request<Application>(`/api/jobs/${jobId}/apply`, { method: "POST" });

export const getApplication = (id: number) => request<Application>(`/api/applications/${id}`);

export const cancelApplication = (id: number) => request<void>(`/api/applications/${id}`, { method: "DELETE" });
