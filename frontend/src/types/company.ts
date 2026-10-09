import type { Platform } from "./searchSettings";

export type Company = {
  id: number;
  platform: Platform;
  board_id: string;
  discovered_at: string;
  discovered_query: string;
  blocked: boolean;
  last_fetched_at: string | null;
  last_error: string | null;
  open_jobs: number;
};
