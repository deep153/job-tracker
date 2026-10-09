import type { AiCosts, AiSettings } from "../types/settings";
import { request, sendJson } from "./client";

export const saveSearchApiKey = (key: string) =>
  request<void>("/api/settings/search-api-key", sendJson("PUT", { key }));

export const getAiSettings = () => request<AiSettings>("/api/settings");

export const saveAnthropicApiKey = (key: string) =>
  request<AiSettings>("/api/settings/anthropic-api-key", sendJson("PUT", { key }));

export const saveModels = (scoring_model: string, tailoring_model: string) =>
  request<AiSettings>("/api/settings/models", sendJson("PUT", { scoring_model, tailoring_model }));

export const getAiCosts = () => request<AiCosts>("/api/settings/costs");
