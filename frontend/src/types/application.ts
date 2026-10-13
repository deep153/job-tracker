import type { Job } from "./job";

export type ApplicationStatus = "drafting" | "in_review" | "failed";

export type SkillLine = { label: string | null; skills: string[] };

export type TailoredResume = {
  master_version: number;
  summary: { master: string[]; tailored: string[] };
  skills: { master: SkillLine[]; tailored: SkillLine[] };
  page_count: number;
  master_page_count: number;
  /** False when the tailored PDF has more pages than the master. */
  fits: boolean;
  coverage: {
    keywords: { keyword: string; before: boolean; after: boolean }[];
    before: number;
    after: number;
    total: number;
  };
  pdf_url: string;
  docx_url: string;
};

/** Where an answer came from: my answer bank, the tailored resume, typed by me in review, or nowhere yet. */
export type AnswerSource = "bank" | "resume" | "you" | "none";

export type FormQuestion = {
  key: string;
  label: string;
  kind: "text" | "textarea" | "select" | "radio" | "checkbox" | "file";
  required: boolean;
  options: string[];
  answer: string | null;
  source: AnswerSource;
  /** Required and still unanswered, so the application can't be approved. */
  needs_input: boolean;
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
  /** The application form's questions; null until it's read, or when it can't be. */
  questions: FormQuestion[] | null;
  form_error: string | null;
  can_approve: boolean;
  approval_problem: string | null;
};
