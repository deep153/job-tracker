import type { AnswerCategory } from "./answers";

/** One proposed answer-bank entry, worded the way application forms ask it. */
export type ProfileField = {
  question: string;
  category: AnswerCategory;
  /** What my resume (or search settings) says; empty when nothing was found. */
  value: string;
  /** My answer bank's answer to the same question, if I have one. */
  current: string | null;
  /** Read from my resume, taken from the chosen education entry, or a standard question a resume can't answer. */
  section: "resume" | "education" | "questions";
};

export type Education = {
  school: string;
  /** Written in full, such as "Master of Science". */
  degree: string;
  discipline: string;
  end_month: string;
  end_year: string;
};

export type ProfileProposal = {
  fields: ProfileField[];
  /** As the resume lists them. */
  education: Education[];
  /** The entry the education fields come from: the highest degree. */
  selected_education: number | null;
  /** Why my name, location and education weren't read, if they weren't. */
  ai_note: string | null;
};

/** An existing answer to the same question is replaced only if `replace`. */
export type ProfileAnswer = { question: string; category: AnswerCategory; answer: string; replace: boolean };
