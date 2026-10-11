import type { Job } from "./job";

export type ApplicationStatus = "drafting" | "in_review" | "failed";

export type SkillLine = { label: string | null; skills: string[] };

export type TailoredResume = {
  master_version: number;
  summary: { master: string[]; tailored: string[] };
  skills: { master: SkillLine[]; tailored: SkillLine[] };
  page_count: number;
  master_page_count: number;
  coverage: {
    keywords: { keyword: string; before: boolean; after: boolean }[];
    before: number;
    after: number;
    total: number;
  };
  pdf_url: string;
  docx_url: string;
};

export type Application = {
  id: number;
  status: ApplicationStatus;
  error: string | null;
  created_at: string;
  updated_at: string;
  cost_usd: number;
  job: Job;
  resume: TailoredResume | null;
};
