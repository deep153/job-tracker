import type { Job } from "./job";

export type ApplicationStatus = "drafting" | "in_review" | "submitting" | "submitted" | "needs_manual" | "failed";

/** How each status reads as a badge on a job, and as the button that opens the application. */
export const APPLICATION_LABELS: Record<ApplicationStatus, { badge: string; action: string }> = {
  drafting: { badge: "Tailoring resume…", action: "View tailoring progress" },
  in_review: { badge: "Draft in review", action: "Review application" },
  submitting: { badge: "Sending…", action: "View sending progress" },
  submitted: { badge: "Applied", action: "View application" },
  needs_manual: { badge: "Finish by hand", action: "Finish application" },
  failed: { badge: "Failed", action: "See what went wrong" },
};

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

/** Where an answer came from: my answer bank, the tailored resume, drafted by the AI, typed by me in review, or
 * nowhere yet. */
export type AnswerSource = "bank" | "resume" | "ai" | "you" | "none";

export type FormQuestion = {
  key: string;
  label: string;
  kind: "text" | "textarea" | "select" | "radio" | "checkbox" | "file";
  required: boolean;
  options: string[];
  answer: string | null;
  source: AnswerSource;
  /** An EEO or demographic question: answered only from my saved choices, never by the AI. */
  eeo: boolean;
  /** Required (or EEO) and still unanswered, so the application can't be approved. */
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
  submitted_at: string | null;
  /** The page as it was when sending failed. */
  screenshot_url: string | null;
  can_approve: boolean;
  approval_problem: string | null;
};
