import type { Job } from "./job";

/** What I set by hand once an application has been submitted, as I hear back. */
export type TrackedStatus = "interviewing" | "rejected" | "offer" | "withdrawn";

export type ApplicationStatus =
  "drafting" | "in_review" | "submitting" | "submitted" | "needs_manual" | "failed" | TrackedStatus;

/** Statuses of an application that reached the company; its job is gone from the dashboard. */
export const APPLIED_STATUSES: ApplicationStatus[] = ["submitted", "interviewing", "rejected", "offer", "withdrawn"];

/** How each status reads as a badge on a job, and as the button that opens the application. */
export const APPLICATION_LABELS: Record<ApplicationStatus, { badge: string; action: string }> = {
  drafting: { badge: "Tailoring resume…", action: "View tailoring progress" },
  in_review: { badge: "Draft in review", action: "Review application" },
  submitting: { badge: "Sending…", action: "View sending progress" },
  submitted: { badge: "Applied", action: "View application" },
  needs_manual: { badge: "Finish by hand", action: "Finish application" },
  failed: { badge: "Failed", action: "See what went wrong" },
  interviewing: { badge: "Interviewing", action: "View application" },
  rejected: { badge: "Rejected", action: "View application" },
  offer: { badge: "Offer", action: "View application" },
  withdrawn: { badge: "Withdrawn", action: "View application" },
};

/** A row in the applications list. */
export type ApplicationSummary = {
  id: number;
  status: ApplicationStatus;
  /** When it was submitted, or started if it hasn't been. */
  date: string;
  job: Job;
};

export type SkillLine = { label: string | null; skills: string[] };

/** One experience bullet: the master's text after its label, the text in use, and the last rewrite the fact
 * check turned down (it changed a number, added an unlisted skill or grew too much), with why. */
export type BulletEdit = {
  index: number;
  label: string | null;
  master: string;
  tailored: string;
  reverted: { text: string; reason: string } | null;
};

export type TailoredResume = {
  master_version: number;
  summary: { master: string[]; tailored: string[] };
  skills: { master: SkillLine[]; tailored: SkillLine[] };
  /** Null on resumes tailored before bullets could be reworded; empty when none are marked. */
  bullets: BulletEdit[] | null;
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
  /** The job's keywords the tailor couldn't honestly cover; null on resumes tailored before gaps were kept. */
  gaps: string[] | null;
  /** The job's fit score before tailoring and the tailored resume's; null on resumes tailored before scores were
   * kept, and either side null when there was no score (unscored job, or the re-score failed). */
  fit_score: { before: number | null; after: number | null } | null;
  pdf_url: string;
  docx_url: string;
};

/** Where an answer came from: my answer bank, the tailored resume, the cover letter, drafted by the AI, typed by
 * me in review, or nowhere yet. */
export type AnswerSource = "bank" | "resume" | "cover_letter" | "ai" | "you" | "none";

export type CoverLetter = {
  text: string;
  /** Set when the form takes the letter as a file. */
  pdf_url: string | null;
};

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
  /** Only when the form has a cover letter field. */
  cover_letter: CoverLetter | null;
  form_error: string | null;
  submitted_at: string | null;
  /** The page as it was when sending failed. */
  screenshot_url: string | null;
  can_approve: boolean;
  approval_problem: string | null;
};
