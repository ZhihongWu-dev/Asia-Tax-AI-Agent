import manifest from "../../../knowledge/hong_kong/fsie/source_manifest.json";

export type Facts = {
  entity: string;
  income: string;
  amount: string;
  currency: string;
  period: string;
  receipt: string;
};
export type Message = { id: string; text: string };
export type Case = {
  id: string;
  title: string;
  messages: Message[];
  facts: Facts;
};
export type Panel = "facts" | "sources" | "about" | null;
export const factLabels: Record<keyof Facts, string> = {
  entity: "纳税主体",
  income: "收入类型",
  amount: "金额",
  currency: "币种",
  period: "所属期间",
  receipt: "收取情况",
};
export const emptyFacts: Facts = {
  entity: "",
  income: "",
  amount: "",
  currency: "",
  period: "",
  receipt: "",
};
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
export function makeCase(): Case {
  return {
    id: crypto.randomUUID(),
    title: "",
    messages: [],
    facts: { ...emptyFacts },
  };
}
export function caseTitle(current: Case, t: (text: string) => string): string {
  return current.title || t("新对话");
}
export function submitText(current: Case, text: string): Case {
  // No chat endpoint exists yet. Keep the message locally, without fabricating a response.
  return {
    ...current,
    title: current.title || text.slice(0, 28),
    messages: [...current.messages, { id: crypto.randomUUID(), text }],
  };
}
export const receiptOptions = [
  "已汇入香港",
  "尚未汇入香港",
  "用于抵销或清偿债务",
  "不确定",
];
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
