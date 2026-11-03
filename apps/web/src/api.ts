import type { Case, FieldSpec, FactValue, KnowledgeResult, EntryHint } from "./workspace";
let activeWorkflow = 'brief';

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
    "auth_unavailable",
    "knowledge_unavailable",
    "tool_failed",
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
  stream: async (doc: Case, text: string, approved: boolean, requestId: string, signal: AbortSignal, delta: (text: string, reset?: boolean) => void,
                 entryHint: EntryHint = "auto", replyToQuestionId: string | null = null, locale: "zh" | "en" = "zh"): Promise<Case> => {
    const response = await fetch(`/api/cases/${doc.id}/${activeWorkflow === 'brief' ? 'brief/messages' : 'messages'}`, {
      method: "POST", credentials: "same-origin", signal: AbortSignal.any([signal, AbortSignal.timeout(240000)]),
      headers: { "Content-Type": "application/json", "Accept": "text/event-stream", "X-AsiaTax-Request": "1" },
      body: JSON.stringify({ text, data_approved: approved, revision: doc.revision, request_id: requestId,
        entry_hint: entryHint, reply_to_question_id: replyToQuestionId, locale }),
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
            if (event.type === "status") delta(event.text, true);
            if (event.type === "delta") delta(event.text);
            if (event.type === "reset") delta("", true);
            if (event.type === "error") throw new ApiError(event.code);
            if (event.type === "done") return event.case as Case;
          }
        }
      }
      throw new ApiError("network_error");
    } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
  },
  search: (query: string) =>
    request<KnowledgeResult>(
      `/knowledge/search?q=${encodeURIComponent(query)}`,
    ),
  session: async () => {
    const session = await request<{ fields: FieldSpec[]; model_configured: boolean; can_review?: boolean; workflow?: string }>("/session");
    activeWorkflow = session.workflow || 'legacy';
    return session;
  },
  list: () => request<Case[]>("/cases"),
  create: () => request<Case>("/cases", "POST"),
  get: (id: string) => request<Case>(`/cases/${id}`),
  domainCapabilities: () => request<{ready: boolean; release: string; supported_templates: string[]}>("/domain/capabilities"),
  domainSetup: (doc: Case, caseInput: Record<string, unknown>, dataApproved: boolean, requestId: string,
                mode = "plan_structure", bindings: Record<string, string> = {}) =>
    request<Case>(`/cases/${doc.id}/domain-case`, "PUT", { revision: doc.revision, request_id: requestId,
      case_input: caseInput, data_approved: dataApproved, mode, bindings }),
  domainDraft: (doc: Case) => request<{case: Record<string, unknown> | null; bindings: Record<string, string>;
    gaps: string[]; unmapped: string[]}>(`/cases/${doc.id}/domain-draft`),
  domainControl: (doc: Case, action: string) => request<Case>(`/cases/${doc.id}/domain-control`, "POST",
    {revision: doc.revision, request_id: crypto.randomUUID(), action}),
  domainConfirm: (doc: Case) => request<Case>(`/cases/${doc.id}/domain-confirm`, "POST",
    {revision: doc.revision, request_id: crypto.randomUUID()}),
  domainReport: (doc: Case, allowPartial: boolean) => request<Case>(`/cases/${doc.id}/domain-report`, "POST",
    {revision: doc.revision, request_id: crypto.randomUUID(), allow_partial: allowPartial}),
  domainProfessional: (doc: Case, questionId: string, value: string | string[], reference: Record<string, string>) =>
    request<Case>(`/cases/${doc.id}/domain-professional`, "POST", {revision: doc.revision,
      request_id: crypto.randomUUID(), question_id: questionId, value, reference}),
  finalReview: (doc: Case, reportId: string, reportHash: string, decision: string, note: string) =>
    request<Case>(`/cases/${doc.id}/analyses/${reportId}/review`, "POST", { revision: doc.revision,
      request_id: crypto.randomUUID(), report_hash: reportHash, decision, note }),
  domainPlan: (doc: Case, requestId: string) =>
    request<Case>(`/cases/${doc.id}/domain-plan`, "POST", { revision: doc.revision, request_id: requestId }),
  domainAnswers: (doc: Case, answers: {key: string; kind: string; value: string; question_id: string}[], requestId: string, locale: string) =>
    request<Case>(`/cases/${doc.id}/domain-answers`, "POST", { revision: doc.revision, request_id: requestId, answers, locale }),
  domainAnswer: (doc: Case, key: string, kind: string, value: string, requestId: string, questionId?: string, disposition = "answer") =>
    request<Case>(`/cases/${doc.id}/domain-answer`, "POST", { revision: doc.revision, request_id: requestId,
      key, kind, value, question_id: questionId, disposition }),
  mutate: (
    current: Case,
    action: "messages" | "facts" | "confirm" | "analyze" | "organization",
    payload: Record<string, unknown> = {},
    requestId: string = crypto.randomUUID(),
  ) =>
    request<Case>(
      `/cases/${current.id}/${action}`,
      action === "facts" || action === "organization" ? "PATCH" : "POST",
      { revision: current.revision, request_id: requestId, ...payload },
    ),
};
export type FactPatch = Record<string, FactValue | null>;
