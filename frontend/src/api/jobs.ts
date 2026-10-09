import type { FilteredJob, Job } from "../types/job";
import { request } from "./client";

export const listJobs = () => request<Job[]>("/api/jobs");

export const listJobsBelowThreshold = () => request<Job[]>("/api/jobs/below-threshold");

export const listFilteredOutJobs = () => request<FilteredJob[]>("/api/jobs/filtered-out");
