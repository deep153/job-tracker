import type { FilterRule } from "./job";
import type { Platform } from "./searchSettings";

export type RunStatus = "running" | "finished" | "failed" | "interrupted";

export type RunError =
  | { kind: "board"; platform: Platform; board_id: string; message: string }
  | { kind: "search" | "scoring"; platform: null; board_id: null; message: string };

export type Run = {
  id: number;
  status: RunStatus;
  stage: "discovering" | "fetching" | "scoring";
  started_at: string;
  finished_at: string | null;
  search_queries: number;
  search_queries_capped: boolean;
  companies_discovered: number;
  companies_total: number;
  companies_fetched: number;
  new_jobs: number;
  updated_jobs: number;
  closed_jobs: number;
  filtered_out: Record<FilterRule, number>;
  errors: RunError[];
  scoring_total: number;
  scored_jobs: number;
  matched_jobs: number;
  ai_cost_usd: number;
};
