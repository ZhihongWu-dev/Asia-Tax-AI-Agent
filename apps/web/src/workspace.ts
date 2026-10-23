import manifest from "../../../knowledge/hong_kong/fsie/source_manifest.json";
import expensesManifest from "../../../knowledge/hong_kong/profits_tax_deductions/source_manifest.json";

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
  domain?: string;
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
  claims: { text: string; evidence_ids: string[]; kind: "excerpt" | "grounded_summary" }[];
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
  reply_locale?: "zh" | "en";
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
  fsie_assessment?: Analysis | null;
  report_kind?: string; outcome?: DomainOutcome; markdown?: string;
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
  consultation?: {
    version: number; stage: 'collecting' | 'ready';
    facts: Record<string, { value: string | number | boolean | null; quote: string; status: string }>;
    analyzed_hash?: string; generation_consent?: string; report_job?: string;
  };
  reply_locale?: "zh" | "en";
  schema_version?: string;
  legacy_bindings?: Record<string, string>;
  domain_confirmation?: { facts_hash: string; revision: number } | null;
  domain_workflow?: { mode: string; status: string; pending_question_id: string | null };
  domain_case?: Record<string, unknown> | null;
  domain_answers?: { data: Record<string, unknown>; actions: Record<string, string> };
  domain_outcome?: DomainOutcome | null;
  domain_today?: string | null;
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
export type DomainQuestion = { id: string; key: string; kind: string; region: string[]; prompt: string;
  prompt_en?: string;
  review_reason?: string;
  review_reason_en?: string; context_zh?: string; context_en?: string;
  interview_status?: "ready" | "waiting" | "not_applicable" | "needs_policy_review";
  why: string[]; impact: number | null; source_hint: string; source_hint_en?: string; forms: string[];
  answer_schema?: { type: string; hint: string } };
export type DomainOutcome = { status: "needs_input" | "ready" | "blocked" | "unsupported"; release: string;
  mode: string; currency: string; facts_hash: string;
  input_hash: string; today: string; stale?: boolean; questions: DomainQuestion[]; question_count?: number;
  candidate_count: number; note?: string; candidate?: Record<string, unknown>;
  upper?: { value: number | null; status: string }; lower?: { value: number | null; status: string };
  structure?: { entities: [string, string, string][]; holds: [string, string, number, string][];
    flows: [string, string, string, string, number, string][] };
  regions?: { jurisdictions: string[]; actions: unknown[]; guaranteed: [string, string, string, string, number, string[], boolean][];
    best: unknown[]; deadlines: unknown[]; conditions: unknown[] }[];
  notes?: string[]; unmodelled?: unknown[] };
export type Panel = "facts" | "sources" | "structure" | "about" | null;
export function fieldLabel(field: FieldSpec, locale: string) {
  const clean: Record<string, string> = { holding_percentage_pct: "持股比例（%）", bank_or_account_path: "账户及资金路径",
    dividend_amount: "股息金额", dividend_currency: "股息币种", evidence_inventory: "已有及待补材料" };
  return locale === "en" ? field.label_en : clean[field.field_name] || field.description_zh.split(/[；，]/)[0];
}

export function uniquePassages(results: KnowledgeResult[]) {
  const seen = new Set<string>();
  return results.flatMap(result => result.passages).filter(p => {
    const key = JSON.stringify([p.source_id, p.unit_id, p.locator, p.text_sha256]);
    if (seen.has(key)) return false;
    seen.add(key); return true;
  });
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
    text: "请带我逐步整理这笔股息的事实，并指出还缺哪些信息。",
  },
  {
    id: "sources",
    entryHint: "reference_lookup" as EntryHint,
    title: "查阅依据",
    text: "我想查香港境外股息的法规或官方案例，请帮我找到依据。",
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
].concat([
  {
    id: "hk_hkel_iro_cap112_expenses",
    label: "企业费用扣除 · 第 16、17 条",
    tag: "香港电子法例 · 法例",
    description: "核对一般费用扣除条件及不得扣除的项目。",
  },
  {
    id: "hk_ird_profits_tax_deductions",
    label: "利得税费用扣除指引",
    tag: "税务局 · 指引",
    description: "了解税务局对普通经营费用和排除项目的说明。",
  },
  {
    id: "hk_ird_bir51_notes_deductions",
    label: "BIR51 公司报税说明",
    tag: "税务局 · 报税说明",
    description: "核对公司报税时的费用调整和所需资料。",
  },
]).map((info) => {
  const source = [...manifest.sources, ...expensesManifest.sources].find((s) => s.source_id === info.id)!;
  return {
    ...info,
    url: source.url,
    title: source.title,
    coverageCutoff: expensesManifest.sources.some((entry) => entry.source_id === info.id)
      ? expensesManifest.legal_coverage_cutoff : manifest.legal_coverage_cutoff,
    captured: "retrieved_at" in source && typeof source.retrieved_at === "string"
      ? source.retrieved_at.slice(0, 10) : "未记录",
  };
});
export const coverageCutoff = manifest.legal_coverage_cutoff;
