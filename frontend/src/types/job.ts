import type { Platform, WorkMode } from "./searchSettings";

export type FilterRule = "role" | "excluded_keyword" | "location" | "seniority" | "experience" | "sponsorship" | "salary";

export type FitScore = {
  score: number;
  reasons: string[];
  matched_keywords: string[];
  missing_keywords: string[];
  model: string;
  resume_version: number;
  scored_at: string;
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
  score: FitScore | null;
};

export type FilteredJob = Job & { rejection: { rule: FilterRule; reason: string } };
