import type { SystemStatus } from "../types/status";
import { request } from "./client";

export const getStatus = () => request<SystemStatus>("/api/status");
