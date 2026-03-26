import { z, type ZodType } from "zod";

import { API_BASE } from "@/config/api";
import { getActiveApiKey } from "@/lib/auth";

const DEFAULT_TIMEOUT_MS = 30_000;

const jsonValueSchema = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.null(),
  z.array(z.unknown()),
  z.record(z.unknown()),
]);

const errorPayloadSchema = z
  .object({
    detail: z.string().optional(),
    message: z.string().optional(),
    error: z.string().optional(),
    status: z.number().optional(),
  })
  .catchall(jsonValueSchema);

export class ApiError extends Error {
  readonly status: number;
  readonly payload: Record<string, unknown> | null;

  constructor(message: string, status: number, payload: Record<string, unknown> | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  body?: unknown;
  headers?: Record<string, string>;
  timeoutMs?: number;
  signal?: AbortSignal;
};

type StreamOptions = Omit<RequestOptions, "method" | "body"> & {
  onEvent: (payload: Record<string, unknown>) => void;
};

function buildHeaders(extraHeaders?: Record<string, string>): Record<string, string> {
  const apiKey = getActiveApiKey();
  const base: Record<string, string> = {};
  if (apiKey) {
    base["X-AEGIS-API-Key"] = apiKey;
    base.Authorization = `Bearer ${apiKey}`;
  }
  return { ...base, ...(extraHeaders || {}) };
}

export function getApiHeaders(extraHeaders?: Record<string, string>): Record<string, string> {
  return buildHeaders(extraHeaders);
}

function withTimeout(signal: AbortSignal | undefined, timeoutMs: number): AbortSignal {
  if (signal) return signal;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  controller.signal.addEventListener(
    "abort",
    () => {
      window.clearTimeout(timeout);
    },
    { once: true },
  );
  return controller.signal;
}

async function parseJsonSafe(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

export async function apiRequest<T>(
  path: string,
  schema: ZodType<T>,
  options: RequestOptions = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const method = options.method || "GET";
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const body = options.body;

  const headers = buildHeaders({
    ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
  });

  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: withTimeout(options.signal, timeoutMs),
  });

  const payload = await parseJsonSafe(response);
  if (!response.ok) {
    const parsed = errorPayloadSchema.safeParse(payload);
    const detail =
      parsed.success
        ? parsed.data.detail || parsed.data.message || parsed.data.error
        : undefined;
    throw new ApiError(detail || `Request failed with status ${response.status}`, response.status, parsed.success ? parsed.data : null);
  }

  const parsed = schema.safeParse(payload);
  if (!parsed.success) {
    throw new ApiError("Invalid API response schema", 502, {
      issues: parsed.error.issues,
    });
  }
  return parsed.data;
}

export async function apiRequestBlob(
  path: string,
  options: RequestOptions = {},
): Promise<Blob> {
  const url = `${API_BASE}${path}`;
  const method = options.method || "GET";
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const body = options.body;
  const headers = buildHeaders({
    ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
  });

  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: withTimeout(options.signal, timeoutMs),
  });

  if (!response.ok) {
    const payload = await parseJsonSafe(response);
    const parsed = errorPayloadSchema.safeParse(payload);
    const detail =
      parsed.success
        ? parsed.data.detail || parsed.data.message || parsed.data.error
        : undefined;
    throw new ApiError(detail || `Request failed with status ${response.status}`, response.status, parsed.success ? parsed.data : null);
  }

  return response.blob();
}

export function apiGet<T>(path: string, schema: ZodType<T>, options: Omit<RequestOptions, "method" | "body"> = {}) {
  return apiRequest(path, schema, { ...options, method: "GET" });
}

export function apiPost<T>(
  path: string,
  schema: ZodType<T>,
  body: unknown,
  options: Omit<RequestOptions, "method" | "body"> = {},
) {
  return apiRequest(path, schema, { ...options, method: "POST", body });
}

export function apiPostBlob(
  path: string,
  body: unknown,
  options: Omit<RequestOptions, "method" | "body"> = {},
) {
  return apiRequestBlob(path, { ...options, method: "POST", body });
}

function dispatchSseEvents(buffer: string, onEvent: (payload: Record<string, unknown>) => void) {
  let remainder = buffer;
  let boundary = remainder.indexOf("\n\n");
  while (boundary >= 0) {
    const rawEvent = remainder.slice(0, boundary);
    remainder = remainder.slice(boundary + 2);
    const dataLines = rawEvent
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim());
    if (dataLines.length > 0) {
      const payload = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
      onEvent(payload);
    }
    boundary = remainder.indexOf("\n\n");
  }
  return remainder;
}

export async function apiStream(path: string, body: unknown, options: StreamOptions) {
  const url = `${API_BASE}${path}`;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const headers = buildHeaders({
    "Content-Type": "application/json",
    ...(options.headers || {}),
  });

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal: withTimeout(options.signal, timeoutMs),
  });

  if (!response.ok) {
    const payload = await parseJsonSafe(response);
    const parsed = errorPayloadSchema.safeParse(payload);
    const detail =
      parsed.success
        ? parsed.data.detail || parsed.data.message || parsed.data.error
        : undefined;
    throw new ApiError(detail || `Request failed with status ${response.status}`, response.status, parsed.success ? parsed.data : null);
  }

  if (!response.body) {
    throw new ApiError("Streaming response body was not available", 502, null);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    buffer = dispatchSseEvents(buffer, options.onEvent);
    if (done) break;
  }

  const trailing = buffer.trim();
  if (trailing) {
    const raw = trailing
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .join("\n");
    if (raw) {
      options.onEvent(JSON.parse(raw) as Record<string, unknown>);
    }
  }
}
