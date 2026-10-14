import type { Application, ApplicationSummary, TrackedStatus } from "../types/application";
import { request, sendJson } from "./client";

/** Every application, newest first. */
export const listApplications = () => request<ApplicationSummary[]>("/api/applications");

/** Refused until the application is submitted; `submitted` marks one I finished by hand. */
export const setApplicationStatus = (id: number, status: TrackedStatus | "submitted") =>
  request<Application>(`/api/applications/${id}/status`, sendJson("PUT", { status }));

/** Starts tailoring my resume for the job, or returns the job's open application. */
export const applyToJob = (jobId: number) => request<Application>(`/api/jobs/${jobId}/apply`, { method: "POST" });

export const getApplication = (id: number) => request<Application>(`/api/applications/${id}`);

/** Regenerates the tailored .docx and PDF from my edits. */
export const editTailoredResume = (id: number, edits: { summary: string[]; skills: string[][] }) =>
  request<Application>(`/api/applications/${id}/resume`, sendJson("PUT", edits));

export const editCoverLetter = (id: number, text: string) =>
  request<Application>(`/api/applications/${id}/cover-letter`, sendJson("PUT", { text }));

/** Saves answers I typed, by question key; an empty answer clears the question. */
export const answerQuestions = (id: number, answers: Record<string, string>) =>
  request<Application>(`/api/applications/${id}/answers`, sendJson("PUT", { answers }));

/** Saves the question's current answer into my answer bank, so later applications are answered with it. */
export const saveAnswerToBank = (id: number, key: string) =>
  request<Application>(`/api/applications/${id}/answers/save-to-bank`, sendJson("POST", { key }));

/** Refused while anything still needs fixing, such as a required question with no answer. */
export const approveApplication = (id: number) =>
  request<Application>(`/api/applications/${id}/approve`, { method: "POST" });

export const cancelApplication = (id: number) => request<void>(`/api/applications/${id}`, { method: "DELETE" });
