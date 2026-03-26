import { z } from "zod";

import { apiGet } from "@/lib/apiClient";

export const aegisChatPingSchema = z.object({
  status: z.string(),
  llm_enabled: z.boolean(),
  llm_available: z.boolean(),
  deterministic_fallback_available: z.boolean(),
  provider: z.string().nullable().optional(),
  model: z.string().nullable().optional(),
  detail: z.string().nullable().optional(),
});

export type AegisChatPingResponse = z.infer<typeof aegisChatPingSchema>;

export function fetchAegisChatPing() {
  return apiGet("/api/v1/chat/ping", aegisChatPingSchema);
}
