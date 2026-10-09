import type { Run } from "../types/run";
import { request } from "./client";

export const startRun = () => request<Run>("/api/runs", { method: "POST" });

export const getRun = (id: number) => request<Run>(`/api/runs/${id}`);

export const listRuns = () => request<Run[]>("/api/runs");
