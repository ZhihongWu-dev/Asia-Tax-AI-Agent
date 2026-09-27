import type { Case, FieldSpec, FactValue, KnowledgeResult } from "./workspace";

export class ApiError extends Error {
  constructor(public code: string) {
    super(code);
  }
}
export function isRetryable(code: string) {
  return [
    "network_error",
    "model_failed",
    "model_not_configured",
    "service_unavailable",
    "storage_unavailable",
    "knowledge_unavailable",
  ].includes(code);
}
export async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 65000);
  try {
    const response = await fetch(`/api${path}`, {
      method,
      credentials: "same-origin",
      signal: controller.signal,
      headers: { "Content-Type": "application/json", "X-AsiaTax-Request": "1" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok)
      throw new ApiError(
        typeof data.detail === "string" ? data.detail : "service_unavailable",
      );
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError("network_error");
  } finally {
    clearTimeout(timeout);
  }
}
export const api = {
  search: (query: string) =>
    request<KnowledgeResult>(
      `/knowledge/search?q=${encodeURIComponent(query)}`,
    ),
  session: () =>
    request<{ fields: FieldSpec[]; model_configured: boolean }>("/session"),
  list: () => request<Case[]>("/cases"),
  create: () => request<Case>("/cases", "POST"),
  get: (id: string) => request<Case>(`/cases/${id}`),
  mutate: (
    current: Case,
    action: "messages" | "facts" | "confirm" | "analyze",
    payload: Record<string, unknown> = {},
    requestId: string = crypto.randomUUID(),
  ) =>
    request<Case>(
      `/cases/${current.id}/${action}`,
      action === "facts" ? "PATCH" : "POST",
      { revision: current.revision, request_id: requestId, ...payload },
    ),
};
export type FactPatch = Record<string, FactValue | null>;
