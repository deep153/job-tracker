import type { StoredSecret } from "./searchSettings";

export type AiSettings = {
  anthropic_api_key: StoredSecret;
  scoring_model: string;
  tailoring_model: string;
  suggested_models: string[];
};

export type AiCosts = {
  total_usd: number;
  by_kind: { kind: string; calls: number; cost_usd: number; input_tokens: number; output_tokens: number }[];
  recent_runs: { id: number; started_at: string; scored_jobs: number; ai_cost_usd: number }[];
};
