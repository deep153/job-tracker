export type AnswerCategory =
  | "personal"
  | "work_authorization"
  | "sponsorship"
  | "salary"
  | "start_date"
  | "links"
  | "eeo"
  | "other";

export const CATEGORY_LABELS: Record<AnswerCategory, string> = {
  personal: "Personal details",
  work_authorization: "Work authorization",
  sponsorship: "Sponsorship",
  salary: "Salary",
  start_date: "Start date",
  links: "Links",
  eeo: "Voluntary self-identification",
  other: "Other",
};

export type BankEntry = {
  id: number;
  question: string;
  answer: string;
  category: AnswerCategory;
  created_at: string;
  last_used_at: string | null;
};

export type BankEntryIn = Pick<BankEntry, "question" | "answer" | "category">;
