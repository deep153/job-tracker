export type Platform = "greenhouse" | "lever" | "ashby";

export type WorkMode = "remote" | "hybrid" | "onsite";

export type Seniority = "intern" | "junior" | "mid" | "senior" | "staff" | "principal";

/** Whether a secret is stored, and its last four characters; the API never sends the secret itself. */
export type StoredSecret = { set: boolean; last4: string | null };

export type SearchSettingsInput = {
  roles: string[];
  locations: string[];
  work_modes: WorkMode[];
  platforms: Platform[];
  excluded_keywords: string[];
  seniority: Seniority | null;
  years_experience: number | null;
  needs_sponsorship: boolean;
  min_salary: number | null;
  min_score: number;
};

export type SearchSettings = SearchSettingsInput & {
  available_platforms: { id: Platform; name: string; supported: boolean }[];
  search_api_key: StoredSecret;
  missing: string[];
  ready: boolean;
};
