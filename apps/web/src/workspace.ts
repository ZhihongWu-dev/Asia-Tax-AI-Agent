import manifest from "../../../knowledge/hong_kong/fsie/source_manifest.json";

export type FactValue = string | number | string[];
export type FactRecord = {
  value: FactValue;
  origin: string;
  status: string;
  message_id: string | null;
  revision: number;
};
export type FieldSpec = {
  field_name: string;
  description_zh: string;
  label_en: string;
  data_type: string;
  enum_values?: string[];
};
export type WorkflowInfo = {
  version: string;
  trace_id: string;
  status: string;
  reason_code: string | null;
  trace: string[];
  timings_ms: Record<string, number>;
  retrieval_calls?: number;
  entry_hint?: EntryHint;
  effective_task?: string;
  task_results?: { kind: string; status: string; reason_code: string; query?: string }[];
  error_code?: string;
  retryable?: boolean;
  harness_version?: string;
  harness_stop?: string;
  tool_calls?: { tool: string; status: string; reason_code: string | null; query?: string; duration_ms?: number }[];
};
export type EntryHint = "auto" | "dividend_consultation" | "fact_intake" | "reference_lookup";
export type BusinessTask = { id: string; kind: "consultation" | "fact_intake" | "reference_lookup";
  status: string; pending_question_id?: string };
export type EvidenceAnswer = {
  summary: string;
  conditions: string[];
  claims: { text: string; evidence_ids: string[]; kind: "excerpt" }[];
  limitations: string[];
  review_status: "pending_final_review";
  text: string;
};
export type GuidedQuestion = {
  id: string; kind: "fact" | "choice" | "mode"; field: string | null;
  text: string; why: string; example: string; attempt: number; based_on_revision: number;
  task_id?: string;
};
export type Message = {
  research_results?: KnowledgeResult[];
  guided?: boolean;
  question?: GuidedQuestion | null;
  workflow?: WorkflowInfo;
  answer?: EvidenceAnswer;
  delivery?: "sending" | "failed";
  id: string;
  role: "user" | "assistant";
  text?: string;
  kind?: string;
  question_fields?: string[];
  state?: string;
  analysis_id?: string;
  research?: KnowledgeResult;
};
export type Passage = {
  is_synthetic?: boolean;
  model_use?: string;
  context?: Passage[];
  unit_id: string;
  source_id: string;
  locator: string | null;
  text: string;
  heading?: string;
  title?: string;
  url?: string;
  snapshot_sha256?: string;
  text_sha256?: string;
  retrieved_at?: string;
  drift?: boolean;
  coverage_cutoff?: string;
};
export type KnowledgeResult = {
  is_synthetic?: boolean;
  reason_code?: string;
  provider?: string;
  status: string;
  passages: Passage[];
  method: string;
  query?: string;
};
export type Analysis = {
  intake_gaps?: { field: string; reason: string; impact: string }[];
  partial_output_authorized?: boolean;
  is_synthetic?: boolean;
  report_hash?: string;
  evidence_gate?: string;
  review?: { status: string; history: { reviewer: string; decision: string; note: string; report_hash: string; at: string }[] };
  id: string;
  created_at: string;
  stale: boolean;
  rule_version: string;
  confirmed_revision: number;
  terminal_state: string;
  blockers: string[];
  missing_nodes: string[];
  coverage_cutoff: string;
  retrieval_status: string;
  missing_locators?: string[];
  related_rulings?: KnowledgeResult;
  review_tasks?: {
    node: string;
    status: string;
    fact_keys: string[];
    missing_facts: string[];
    passage_ids?: string[];
  }[];
  nodes: {
    node: string;
    rule_id: string;
    output: string;
    blockers: string[];
    escalation_blockers: string[];
    source_ids: string[];
    passage_ids?: string[];
  }[];
  sources: { source_id: string; title: string; url: string }[];
  passages: Passage[];
};
export type Case = {
  orchestration?: { schema_version: string; active_task: BusinessTask | null;
    suspended_task: BusinessTask | null; queued_tasks: { kind: string }[] };
  identification?: { status: string; scenario: string | null; missing_fields: string[] };
  fact_gaps?: { field: string; reason: string; impact: string }[];
  dialogue?: { policy_version?: string; status?: string; pending?: GuidedQuestion | null;
    partial_consent?: { facts_hash: string; revision: number }; deferred_query?: string };
  workflow?: WorkflowInfo;
  fact_conflicts?: Record<string, { previous: FactValue; candidate: FactValue }>;
  archived?: boolean;
  created_at?: string;
  updated_at?: string;
  id: string;
  title: string;
  revision: number;
  state: string;
  messages: Message[];
  facts: Record<string, FactRecord>;
  questions: string[];
  analyses: Analysis[];
  confirmed_revision: number | null;
  data_approved: boolean;
};
export type Panel = "facts" | "sources" | "about" | null;
export function fieldLabel(field: FieldSpec, locale: string) {
  return locale === "en" ? field.label_en : field.description_zh;
}
export const suggestions = [
  {
    id: "dividends",
    entryHint: "dividend_consultation" as EntryHint,
    title: "境外股息",
    text: "分析境外股息的 FSIE 处理，需要先确认哪些事实？",
  },
  {
    id: "facts",
    entryHint: "fact_intake" as EntryHint,
    title: "梳理事实",
    text: "帮我整理境外股息分析所需的案例事实和证据清单。",
  },
  {
    id: "sources",
    entryHint: "reference_lookup" as EntryHint,
    title: "查阅依据",
    text: "研究境外股息的 FSIE 处理，应当查阅哪些官方资料？",
  },
];
export function caseTitle(current: Case, t: (text: string) => string): string {
  return current.title || t("新对话");
}
export const sourceInfo = [
  {
    id: "hk_ird_fsie_landing",
    label: "FSIE 制度概览",
    tag: "税务局 · 制度指引",
    description: "香港税务局发布的制度介绍与相关资料。",
  },
  {
    id: "hk_hkel_iro_cap112",
    label: "《税务条例》第 112 章",
    tag: "香港电子法例 · 法例",
    description: "在官方法例中核对条文及适用版本。",
  },
  {
    id: "hk_ird_fsie_faq",
    label: "FSIE 常见问题",
    tag: "税务局 · 常见问题",
    description: "结合案例事实和所属期间阅读相关解答。",
  },
].map((info) => {
  const source = manifest.sources.find((s) => s.source_id === info.id)!;
  return {
    ...info,
    url: source.url,
    title: source.title,
    captured: source.retrieved_at?.slice(0, 10) || "未记录",
  };
});
export const coverageCutoff = manifest.legal_coverage_cutoff;
