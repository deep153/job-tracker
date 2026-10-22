import type { BankEntry } from "../types/answers";
import type { ProfileAnswer, ProfileProposal } from "../types/profile";
import type { Resume, ResumeMapping, ResumeVersion } from "../types/resume";
import { request, sendJson } from "./client";

export const getResume = () => request<Resume | null>("/api/resume");

export const listResumeVersions = () => request<ResumeVersion[]>("/api/resume/versions");

export function uploadResume(file: File) {
  const body = new FormData();
  body.append("file", file);
  return request<Resume>("/api/resume", { method: "POST", body });
}

export const saveResumeMapping = (mapping: ResumeMapping) =>
  request<Resume>("/api/resume/mapping", sendJson("PUT", mapping));

export const saveResumeSkills = (skills: string[]) =>
  request<Resume>("/api/resume/skills", sendJson("PUT", { skills }));

/** Proposed answer-bank entries from my current resume; nothing is saved. */
export const extractProfile = () => request<ProfileProposal>("/api/resume/profile", { method: "POST" });

/** Saves my confirmed profile answers into the answer bank, and returns it. */
export const applyProfile = (answers: ProfileAnswer[]) =>
  request<BankEntry[]>("/api/resume/profile", sendJson("PUT", { answers }));
