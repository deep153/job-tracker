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
