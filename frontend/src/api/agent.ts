import { apiPost } from "./client";

export type AgentPreviewType = "application" | "interview" | "status_update";

export interface AgentModelUsage {
  used: boolean;
  provider: string | null;
  name: string | null;
  fallback_reason?: string | null;
}

export interface AgentMissingFields {
  required: string[];
  recommended: string[];
}

export interface AgentPreview {
  preview_id: string;
  type: AgentPreviewType;
  fields: Record<string, unknown>;
  missing: AgentMissingFields | null;
  warnings: string[];
}

export interface AgentResponse {
  ok: boolean;
  intent: string;
  message: string;
  data: Record<string, unknown> | null;
  preview: AgentPreview | null;
  requires_confirmation: boolean;
  model: AgentModelUsage;
}

export function sendAgentMessage(text: string) {
  return apiPost<AgentResponse, { text: string }>("/agent/chat", { text });
}

export function confirmAgentPreview(previewId: string) {
  return apiPost<AgentResponse, { preview_id: string }>("/agent/confirm", {
    preview_id: previewId,
  });
}
