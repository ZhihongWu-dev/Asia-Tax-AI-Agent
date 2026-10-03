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
export type Message = {
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
  status: string;
  passages: Passage[];
  method: string;
  query?: string;
};
export type Analysis = {
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
    title: "境外股息",
    text: "分析境外股息的 FSIE 处理，需要先确认哪些事实？",
  },
  {
    id: "facts",
    title: "梳理事实",
    text: "帮我整理境外股息分析所需的案例事实和证据清单。",
  },
  {
    id: "sources",
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
