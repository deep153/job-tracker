import type { SearchSettings, SearchSettingsInput } from "../types/searchSettings";
import { request, sendJson } from "./client";

export const getSearchSettings = () => request<SearchSettings>("/api/search-settings");

export const saveSearchSettings = (settings: SearchSettingsInput) =>
  request<SearchSettings>("/api/search-settings", sendJson("PUT", settings));
