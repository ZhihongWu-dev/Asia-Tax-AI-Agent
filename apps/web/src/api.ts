import type { ActivityItem, Case, RunState, SearchState } from "./workspace";

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
  deleteCase: (doc: Case) => request(`/cases/${doc.id}?revision=${doc.revision}`, "DELETE"),
  get: (id: string) => request<Case>(`/cases/${id}`),
  run: (id: string, after: number) => request<RunState>(`/cases/${id}/run?after=${after}`),
  resumeRun: (id: string) => request(`/cases/${id}/run`, "POST"),
  search: (id: string) => request<SearchState>(`/cases/${id}/search`),
  stopRun: (id: string) => request(`/cases/${id}/run/stop`, "POST"),
  removeDocument: (id: string, name: string) => request<Case>(`/cases/${id}/documents/${encodeURIComponent(name)}`, "DELETE"),
  organize: (doc: Case, changes: { title?: string; archived?: boolean }) =>
    request<Case>(`/cases/${doc.id}/organization`, "PATCH",
      { revision: doc.revision, request_id: crypto.randomUUID(), ...changes }),
  atlasMap: () => request<AtlasMap>("/atlas/map"),
  atlasCountry: (code: string) => request<AtlasCountry>(`/atlas/country/${code}`),
  atlasGlossary: () => request<AtlasGlossary>("/atlas/glossary"),
  atlasClause: (citeId: string) => request<AtlasClause>(`/atlas/clause?cite_id=${encodeURIComponent(citeId)}`),
};

// ---------------------------------------------------------------- tax graph (apps/api/atlas.py)
export type AtlasAbsent = { id: string; statement: string; cite_id: string; quote: string; subject: string };
export type AtlasCell = {
  floor: number | null; ceiling: number | null; status: string; value_kind: string;
  needs: string[]; rules: string[]; cite_ids: string[]; absent?: AtlasAbsent[];
};
export type AtlasVersion = { library: string; source: string; rules: number; docs?: number; clauses?: number; params?: number };
export type AtlasJurisdiction = {
  code: string; iso: string; name: string; name_zh: string; currency: string;
  wht_company: AtlasCell; wht_individual: AtlasCell;
};
export type AtlasMap = { date: string; version: AtlasVersion; metrics: string[]; facts: Record<string, unknown>; jurisdictions: AtlasJurisdiction[] };
export type AtlasTreaty = { pair: string; doc_id: string; in_force_from: string; title: string; mli: boolean; url: string };
export type AtlasPartner = {
  code: string; name: string; name_zh: string; treaty: AtlasTreaty[];
  qualifying: AtlasCell; portfolio: AtlasCell; individual: AtlasCell;
  conditions: Record<string, { value: string; unit: string; cite_id: string; quote: string }>;
};
export type AtlasParam = {
  param_id: string; scope: string; subject: string; slot: string; name: string; value: string; unit: string;
  cite_id: string; quote: string; effective_from: string; effective_to: string; note: string; superseded_by: string;
};
export type AtlasTerm = {
  key: string; kind: string; type: string; allowed: string; question: string; meaning: string;
  jurisdictions: string[]; cite_ids: string[];
};
export type AtlasDoc = { id: string; title: string; type: string; url: string; lang: string; effective_from: string; effective_to: string };
export type AtlasCountry = {
  date: string; version: AtlasVersion; code: string; iso: string; name: string; name_zh: string; currency: string;
  headline: { wht_company: AtlasCell; wht_individual: AtlasCell };
  cit: { value: string; unit: string; cite_id: string } | null;
  partners: AtlasPartner[]; slots: { slot: string; title: string; title_zh: string }[];
  params: AtlasParam[]; absent: AtlasAbsent[]; docs: AtlasDoc[]; terms: AtlasTerm[];
};
export type AtlasGlossary = {
  version: AtlasVersion;
  slots: { slot: string; title: string; title_zh: string; text: string; text_zh: string }[];
  terms: AtlasTerm[]; jurisdictions: { code: string; name: string; name_zh: string }[];
};
export type AtlasClause = {
  cite_id: string; doc_id: string; label: string; text: string; total: number;
  title: string; url: string; lang: string; jur: string;
};
