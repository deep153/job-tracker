import type { FilteredJob, Job, JobQuery } from "../types/job";
import { request } from "./client";

function queryString(query: JobQuery): string {
  const params = new URLSearchParams({ sort: query.sort });
  if (query.company) params.set("company", query.company);
  if (query.location.trim()) params.set("location", query.location.trim());
  if (query.posted_within_days) params.set("posted_within_days", String(query.posted_within_days));
  return params.toString();
}

export const listJobs = (query: JobQuery) => request<Job[]>(`/api/jobs?${queryString(query)}`);

export const listJobsBelowThreshold = (query: JobQuery) =>
  request<Job[]>(`/api/jobs/below-threshold?${queryString(query)}`);

export const listFilteredOutJobs = () => request<FilteredJob[]>("/api/jobs/filtered-out");

export const dismissJob = (id: number) => request<void>(`/api/jobs/${id}/dismiss`, { method: "POST" });

export const rescoreJob = (id: number) => request<Job | FilteredJob>(`/api/jobs/${id}/rescore`, { method: "POST" });
