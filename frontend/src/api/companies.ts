import type { Company } from "../types/company";
import { request, sendJson } from "./client";

export const listCompanies = () => request<Company[]>("/api/companies");

export const setCompanyBlocked = (id: number, blocked: boolean) =>
  request<Company>(`/api/companies/${id}`, sendJson("PATCH", { blocked }));
