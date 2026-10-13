import type { Application } from "../types/application";
import { request, sendJson } from "./client";

/** Starts tailoring my resume for the job, or returns the job's open application. */
export const applyToJob = (jobId: number) => request<Application>(`/api/jobs/${jobId}/apply`, { method: "POST" });

export const getApplication = (id: number) => request<Application>(`/api/applications/${id}`);

/** Regenerates the tailored .docx and PDF from my edits. */
export const editTailoredResume = (id: number, edits: { summary: string[]; skills: string[][] }) =>
  request<Application>(`/api/applications/${id}/resume`, sendJson("PUT", edits));

/** Saves answers I typed, by question key; an empty answer clears the question. */
export const answerQuestions = (id: number, answers: Record<string, string>) =>
  request<Application>(`/api/applications/${id}/answers`, sendJson("PUT", { answers }));

/** Refused while anything still needs fixing, such as a required question with no answer. */
export const approveApplication = (id: number) =>
  request<Application>(`/api/applications/${id}/approve`, { method: "POST" });

export const cancelApplication = (id: number) => request<void>(`/api/applications/${id}`, { method: "DELETE" });
