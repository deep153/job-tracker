import type { AnswerCategory } from "./answers";

/** One proposed answer-bank entry, worded the way application forms ask it. */
export type ProfileField = {
  question: string;
  category: AnswerCategory;
  /** What my resume (or search settings) says; empty when nothing was found. */
  value: string;
  /** My answer bank's answer to the same question, if I have one. */
  current: string | null;
  /** Read from my resume, or a standard question a resume can't answer. */
  section: "resume" | "questions";
};

export type ProfileProposal = { fields: ProfileField[] };

/** An existing answer to the same question is replaced only if `replace`. */
export type ProfileAnswer = { question: string; category: AnswerCategory; answer: string; replace: boolean };
