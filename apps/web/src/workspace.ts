export type Message = {
  id: string;
  role: "user" | "assistant";
  text?: string;
  delivery?: "sending" | "failed";
  at?: string;
  activity?: ActivityItem[];
  seconds?: number;
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
  return current.title || t("新对话");
}
