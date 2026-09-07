import { apiGet } from "./client";

export interface ModelHealth {
  ok: boolean;
  provider: string;
  base_url: string;
  configured_model: string;
  loaded_models: string[];
  server_reachable: boolean;
  model_available: boolean;
  error: string | null;
}

export function getModelHealth() {
  return apiGet<ModelHealth>("/model/health");
}
