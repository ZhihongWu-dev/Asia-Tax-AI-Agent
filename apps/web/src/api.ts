import type { ActivityItem, Case, RunState } from "./workspace";

export class ApiError extends Error {
  constructor(public code: string) {
    super(code);
  }
}
export function isRetryable(code: string) {
  return ["network_error", "service_unavailable", "storage_unavailable", "auth_unavailable"].includes(code);
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
      headers: { "Content-Type": "application/json", "X-Taxrora-Request": "1" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401 && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("taxora:unauthorized"));
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
  stream: async (doc: Case, text: string, requestId: string, signal: AbortSignal,
                 delta: (text: string, reset?: boolean) => void,
                 activity: (item: ActivityItem) => void): Promise<Case> => {
    const response = await fetch(`/api/cases/${doc.id}/messages`, {
      method: "POST", credentials: "same-origin", signal,
      headers: { "Content-Type": "application/json", "Accept": "text/event-stream", "X-Taxrora-Request": "1" },
      body: JSON.stringify({ text, revision: doc.revision, request_id: requestId }),
    });
    if (response.status === 401) window.dispatchEvent(new Event("taxora:unauthorized"));
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new ApiError(typeof data.detail === "string" ? data.detail : "service_unavailable");
    }
    if (!response.body) throw new ApiError("network_error");
    const reader = response.body.getReader(), decoder = new TextDecoder();
    let buffer = "";
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let end;
        while ((end = buffer.indexOf("\n\n")) >= 0) {
          const frame = buffer.slice(0, end); buffer = buffer.slice(end + 2);
          for (const line of frame.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            const event = JSON.parse(line.slice(6));
            if (event.type === "delta") delta(event.text);
            if (event.type === "reset") delta("", true);
            if (event.type === "activity") activity(event.item);
            if (event.type === "error") throw new ApiError(event.code);
            if (event.type === "done") return event.case as Case;
          }
        }
      }
      throw new ApiError("network_error");
    } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
  },
  list: () => request<Case[]>("/cases"),
  create: () => request<Case>("/cases", "POST"),
  get: (id: string) => request<Case>(`/cases/${id}`),
  run: (id: string, after: number) => request<RunState>(`/cases/${id}/run?after=${after}`),
  resumeRun: (id: string) => request(`/cases/${id}/run`, "POST"),
  stopRun: (id: string) => request(`/cases/${id}/run/stop`, "POST"),
  organize: (doc: Case, changes: { title?: string; archived?: boolean }) =>
    request<Case>(`/cases/${doc.id}/organization`, "PATCH",
      { revision: doc.revision, request_id: crypto.randomUUID(), ...changes }),
};
