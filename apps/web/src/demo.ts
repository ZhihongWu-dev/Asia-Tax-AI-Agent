import manifest from "../../../knowledge/hong_kong/fsie/source_manifest.json";
import { translate } from "./locale";

export type Facts = {
  entity: string;
  jurisdiction: string;
  income: string;
  amount: string;
  currency: string;
  period: string;
  receipt: string;
};
export type Message = { id: string; role: "user" | "assistant"; text: string };
export type Case = {
  id: string;
  title: string;
  messages: Message[];
  facts: Facts;
  stage: "empty" | "facts" | "receipt" | "review";
  confirmed: boolean;
  presetType?: string;
  presetFacts?: Facts;
};
export type Panel = "facts" | "sources" | "about" | null;

export const factLabels: Record<keyof Facts, string> = {
  entity: "纳税主体",
  jurisdiction: "地区",
  income: "收入类型",
  amount: "金额",
  currency: "币种",
  period: "所属期间",
  receipt: "收取情况",
};
export const emptyFacts: Facts = {
  entity: "",
  jurisdiction: "中国香港",
  income: "",
  amount: "",
  currency: "",
  period: "",
  receipt: "",
};
export const presets = [
  {
    title: "境外股息",
    caption: "从收入性质开始梳理",
    type: "dividend",
    text: "虚构案例：一家香港公司在 2025/26 年度收到境外子公司的股息，金额为 100 万港元。我想了解需要确认哪些 FSIE 条件。",
    facts: {
      ...emptyFacts,
      entity: "香港公司（虚构）",
      income: "境外股息",
      amount: "1,000,000",
      currency: "HKD",
      period: "2025/26",
    },
  },
  {
    title: "境外利息",
    caption: "整理资金与收取情况",
    type: "interest",
    text: "虚构案例：一家香港公司在 2025/26 年度取得 5 万美元境外利息。请帮我整理后续研究需要的信息。",
    facts: {
      ...emptyFacts,
      entity: "香港公司（虚构）",
      income: "境外利息",
      amount: "50,000",
      currency: "USD",
      period: "2025/26",
    },
  },
  {
    title: "处置收益",
    caption: "明确交易与资料缺口",
    type: "disposal",
    text: "虚构案例：一家香港公司在 2025/26 年度出售境外资产，产生处置收益，但金额和资金流向尚待确认。请帮我列出研究事项。",
    facts: {
      ...emptyFacts,
      entity: "香港公司（虚构）",
      income: "境外处置收益",
      period: "2025/26",
    },
  },
];

export function makeCase(): Case {
  return {
    id: crypto.randomUUID(),
    title: "新案例",
    messages: [],
    facts: { ...emptyFacts },
    stage: "empty",
    confirmed: false,
  };
}
export function message(role: Message["role"], text: string): Message {
  return { id: crypto.randomUUID(), role, text };
}
export function submitText(current: Case, text: string): Case {
  const preset = presets.find(
    (p) => p.text === text || translate(p.text, "en") === text,
  );
  const first = current.stage === "empty";
  const reply = first
    ? preset
      ? "我们先把这个虚构案例的基础信息整理清楚。下方是预设事实，请核对后确认；之后我们会继续补充收取情况。"
      : "已记下你的描述。当前是交互预览，不会自动解析自由文本或执行税务判断。请在「编辑事实」中填写这个虚构案例的信息，再继续体验研究流程。"
    : "已记录这条补充。交互预览不会自动将文字更新为事实，请通过「编辑事实」修改对应字段；修改后需要重新确认。";
  return {
    ...current,
    title: first
      ? preset
        ? `${preset.title} · 香港`
        : text.slice(0, 22)
      : current.title,
    facts: preset && first ? { ...preset.facts } : current.facts,
    presetType: first ? preset?.type : current.presetType,
    presetFacts: first ? preset?.facts : current.presetFacts,
    messages: [
      ...current.messages,
      message("user", text),
      message("assistant", reply),
    ],
    stage: "facts",
    confirmed: false,
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
    description: "查看香港税务局发布的制度介绍及相关官方资料入口。",
  },
  {
    id: "hk_hkel_iro_cap112",
    label: "《税务条例》第 112 章",
    tag: "香港电子法例 · 法例",
    description: "前往官方法例核对条文和版本。本面板不提供未经核对的原文摘录。",
  },
  {
    id: "hk_ird_fsie_faq",
    label: "FSIE 常见问题",
    tag: "税务局 · 常见问题",
    description: "作为研究问题的辅助导航；需结合具体事实及适用期间阅读。",
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

export function caseTitle(current: Case, t: (text: string) => string): string {
  const preset = presets.find((p) => p.type === current.presetType);
  if (preset) return t(preset.title) + t(" · 香港");
  return current.title === "新案例" && !current.messages.length
    ? t("新案例")
    : current.title;
}

export function factValue(
  current: Case,
  key: keyof Facts,
  t: (text: string) => string,
): string {
  const value = current.facts[key];
  // Only UI-controlled or unchanged fixture values are translated.
  if (
    key === "jurisdiction" ||
    key === "receipt" ||
    current.presetFacts?.[key] === value
  )
    return t(value);
  return value;
}
