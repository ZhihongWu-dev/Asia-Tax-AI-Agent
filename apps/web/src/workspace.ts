export type Message = {
  id: string;
  role: "user" | "assistant";
  text?: string;
  delivery?: "sending" | "failed";
  at?: string;
  activity?: ActivityItem[];
  seconds?: number;
  panel?: string;           // the run whose report panel the front agent's completion note opens
};
export type ActivityItem = {
  kind: "thinking" | "text" | "tool";
  text?: string;
  name?: string;
  detail?: string;
  start?: boolean;
};
export type RunStep = {
  id: string;
  agent: string;
  state: "pending" | "running" | "done" | "failed" | "stopped";
  runs: number;
  seconds: number;
  model: string | null;
  started: string | null;
  reason: string;
};
export type RunBlock = {
  id: string;
  node: string;
  agent: string;
  started: string;
  ended: string | null;
  items: ActivityItem[];
};
export type RunState = {
  active: boolean;
  turning: boolean;
  status: string | null;
  round: number | null;
  revision: number;
  steps: RunStep[];
  stop: { stop: string; detail?: string; time?: string } | null;
  can_resume: boolean;
  report: string | null;
  panel?: boolean;          // a report panel exists for the current run
  chat_revision: number;
  blocks: Omit<RunBlock, "items">[];
  items: (ActivityItem & { block: string })[];
  cursor: number;
};
export type Case = {
  id: string;
  title: string;
  revision: number;
  messages: Message[];
  documents?: string[];
  archived?: boolean;
  created_at?: string;
  updated_at?: string;
};
export type Panel = "about" | null;
export function addItem(list: ActivityItem[], item: ActivityItem): ActivityItem[] {
  const last = list.at(-1);
  if (item.kind !== "tool" && last?.kind === item.kind)
    return [...list.slice(0, -1), { ...last, text: (last.text || "") + (item.start ? "\n\n" : "") + (item.text || "") }];
  return [...list, item];
}
export function caseTitle(current: Case, t: (text: string) => string): string {
  return current.title || t("New chat");
}

export type SearchCandidate = {
  cand_id: string;
  path: string[];
  moves: string[];
  restructure: string[];
  as_is: boolean;
  requested?: boolean;
};
export type SearchRow = { cand_id: string; branch_id: string; rank: number | null; dominated: number; per_100: number | null; amount: number | null };
/** The optimizer's label-setting search, replayed by the search view (GET /api/cases/{id}/search). */
export type SearchState = {
  ready: boolean;
  run_id?: string;
  approximate?: boolean;
  source?: string;
  destinations?: string[];
  nodes?: string[];
  edge_count?: number;
  edges?: Record<string, [string, string, string[]]>;
  events?: (string | number | null)[][];
  frontier?: string[];
  candidates?: SearchCandidate[];
  branches?: Record<string, number>;
  ranking?: SearchRow[];
  best?: string;
  currency?: string;
  amount?: number;
};

/** The client report shown block by block (GET /api/cases/{id}/panel, agent/tools/panel.py). */
export type ReportFlowStructure = {
  title: string;
  chain: { name: string }[];
  holds: string[];
  dividend_to?: number;
  dividend_label?: string;
  result?: string;
};
export type ReportFlow = { current?: ReportFlowStructure; target?: ReportFlowStructure; steps_title?: string; steps?: string[] };
export type ReportSource = { url?: string; title?: string; accessed?: string; cite?: string };
export type ReportStep = {
  title: string; when?: string; date?: string; deadline?: "legal" | "estimate" | "none";
  who?: string; where?: string; documents?: string[]; how?: string; reason?: string; sources?: ReportSource[];
};
export type ReportCard = {
  key: string; title: string; answer?: string; provision?: string; for?: string[]; against?: string[]; routes?: string[];
  reason?: string; confirm_by?: string; how?: string; if_denied?: string;
};
export type ReportFigures = { plan?: string; route?: string; saving?: string; one_off?: string; payback?: string; this_tax?: string };
export type ReportBlock = {
  id: string;
  kind: "program" | "agent";
  state: "final" | "writing" | "review" | "updating";
  title?: string;
  md?: string;
  tables?: string[];
  flow?: ReportFlow;
  steps?: ReportStep[];
  cards?: ReportCard[];
  notes?: { title: string; text: string }[];
  gaps?: string;
  figures?: ReportFigures;
};
export type ReportState = {
  title: string;
  date: string;
  built?: string;
  status: string | null;
  export_ready: boolean;
  export: string | null;
  progress: { final: number; total: number };
  blocks: ReportBlock[];
};
