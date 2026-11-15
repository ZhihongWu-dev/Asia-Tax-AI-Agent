import { useState } from "react";
import { Bot, Cog, Route } from "lucide-react";
import { useLocale } from "../locale";
import type { RunStep } from "../workspace";
import { AGENT_LABEL, STEP_LABEL, duration, whoRuns } from "./RunPanel";

// The orchestration graph of agent/tools/orchestrate.py (LEGAL), drawn by hand so the layout stays readable at panel width.
const ROLE: Record<string, string> = {
  intake: "与客户对话，收集事实和文件，整理成资料包",
  review_intake: "检查资料包是否完整、足以计算；不够就退回前台向客户补充",
  run: "穷举所有持股结构，按规则层逐跳计税，按每笔股息的税额排序",
  analysis: "依据计算产物和法条撰写客户报告",
  review_draft: "逐条核对报告的数字、条件和引用；有问题就退回重写",
  render: "应用复核的替换，排版生成 PDF",
};
const TOOLS: Record<string, string[]> = {
  front: ["tax-case", "tax-opt", "tax-rule", "tax-read"],
  analysis: ["tax-read", "tax-opt", "tax-rule", "tax-case"],
  review: ["tax-read", "tax-opt", "tax-rule", "tax-case"],
  run: ["规则层", "法律库"],
  render: ["XeLaTeX"],
};
const STATE_LABEL: Record<RunStep["state"], string> = {
  pending: "未开始", running: "进行中", done: "已完成", failed: "失败", stopped: "已暂停",
};

const NX = 44, NW = 180, NH = 42, TOP = 48, PITCH = 62, IN = 240, OUT = 300;
const EDGE = NX + NW;
const ORDER = ["intake", "review_intake", "run", "analysis", "review_draft", "render"];
const y = (i: number) => TOP + i * PITCH;
const mid = (i: number) => y(i) + NH / 2;
const END_Y = y(ORDER.length);
const HEIGHT = END_Y + 30;

const arrow = (on?: boolean) => `url(#g-arrow${on ? "-lit" : ""})`;

function loop(from: number, to: number, x: number) {
  const a = mid(from), b = mid(to);
  return `M${EDGE} ${a} H${x - 8} Q${x} ${a} ${x} ${a - 8} V${b + 8} Q${x} ${b} ${x - 8} ${b} H${EDGE + 3}`;
}

export default function RunGraph({ steps, spent, finished, tool, onSearch }: {
  steps: RunStep[];
  spent: (step: RunStep) => number;
  finished: boolean;
  tool?: { name?: string; detail?: string };
  onSearch?: () => void;
}) {
  const { t } = useLocale();
  const byId = Object.fromEntries(steps.map((step) => [step.id, step]));
  const nodes = ORDER.map((id) => byId[id]).filter(Boolean) as RunStep[];
  const current = nodes.find((step) => step.state === "running");
  const fallback = current ?? [...nodes].reverse().find((step) => step.runs > 0) ?? nodes[0];
  const [picked, setPicked] = useState<string | null>(null);
  const shown = (picked && byId[picked]) || fallback;
  const returns = Math.max(0, (byId.analysis?.runs ?? 0) - 1);
  const asked = Math.max(0, (byId.intake?.runs ?? 0) - 1);
  const lit = (step?: RunStep) => step && (step.state === "done" || step.runs > 0);
  const program = (step: RunStep) => step.agent === "program";

  return (
    <div className="run-graph">
      <svg viewBox={`0 0 324 ${HEIGHT}`} role="img" aria-label={t("编排流程图")}>
        <defs>
          {["", "-lit"].map((kind) => (
            <marker key={kind} id={`g-arrow${kind}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0 0 L8 4 L0 8 z" className={`g-head${kind}`} />
            </marker>
          ))}
        </defs>

        <g className={`g-terminal ${nodes.length ? "lit" : ""}`}>
          <rect x={NX + 40} y={4} width={NW - 80} height={24} rx={12} />
          <text x={NX + NW / 2} y={20} textAnchor="middle">{t("客户")}</text>
        </g>
        <line className={`g-edge ${lit(nodes[0]) ? "lit" : ""}`} x1={NX + NW / 2} y1={28} x2={NX + NW / 2} y2={TOP - 2} markerEnd={arrow(lit(nodes[0]))} />

        {nodes.map((step, i) => i < nodes.length - 1 && (
          <line key={step.id} className={`g-edge ${lit(nodes[i + 1]) ? "lit" : ""} ${nodes[i + 1].state === "running" ? "flow" : ""}`}
            x1={NX + NW / 2} y1={y(i) + NH} x2={NX + NW / 2} y2={y(i + 1) - 2} markerEnd={arrow(lit(nodes[i + 1]))} />
        ))}
        <line className={`g-edge ${finished ? "lit" : ""}`} x1={NX + NW / 2} y1={y(ORDER.length - 1) + NH} x2={NX + NW / 2} y2={END_Y - 2} markerEnd={arrow(finished)} />

        <path className={`g-loop ${asked ? "lit" : ""}`} d={loop(1, 0, IN)} markerEnd={arrow(asked > 0)} />
        <text className="g-loop-label" x={IN + 7} y={(mid(0) + mid(1)) / 2 + 4}>{t("补充")}{asked ? ` ×${asked}` : ""}</text>
        <path className={`g-loop ${returns ? "lit" : ""}`} d={loop(4, 3, IN)} markerEnd={arrow(returns > 0)} />
        <text className="g-loop-label" x={IN + 7} y={(mid(3) + mid(4)) / 2 + 4}>{t("退回")}{returns ? ` ×${returns}` : ""}</text>
        <path className="g-loop faint" d={loop(5, 3, OUT)} markerEnd={arrow(false)} />
        <text className="g-loop-label faint" x={IN + 7} y={(mid(4) + mid(5)) / 2 + 4}>{t("未通过")}</text>

        {nodes.map((step, i) => {
          const Icon = program(step) ? Cog : Bot;
          const time = step.runs > 0 || step.state === "running" ? duration(spent(step)) : "";
          return (
            <g key={step.id} className={`g-node ${step.state} ${program(step) ? "program" : "agent"} ${shown?.id === step.id ? "picked" : ""}`}
              onClick={() => setPicked(step.id)} role="button" tabIndex={0} aria-label={t(STEP_LABEL[step.id])}
              onKeyDown={(event) => (event.key === "Enter" || event.key === " ") && setPicked(step.id)}>
              <rect x={NX} y={y(i)} width={NW} height={NH} rx={program(step) ? 5 : 12} />
              <Icon className="g-icon" x={NX + 11} y={y(i) + 13} size={16} />
              <text className="g-title" x={NX + 36} y={y(i) + 18}>{t(STEP_LABEL[step.id])}</text>
              <text className="g-sub" x={NX + 36} y={y(i) + 33}>{program(step) ? t("确定性程序") : step.model || t(AGENT_LABEL[step.agent])}</text>
              {time && <text className="g-time" x={NX + NW - 10} y={y(i) + 18} textAnchor="end">{time}</text>}
              {step.runs > 1 && <text className="g-runs" x={NX + NW - 10} y={y(i) + 33} textAnchor="end">{t("第")} {step.runs} {t("次")}</text>}
            </g>
          );
        })}

        <g className={`g-terminal ${finished ? "lit" : ""}`}>
          <rect x={NX + 40} y={END_Y} width={NW - 80} height={26} rx={13} />
          <text x={NX + NW / 2} y={END_Y + 17} textAnchor="middle">{t("交付报告")}</text>
        </g>
      </svg>

      <div className="g-legend">
        <span><i className="agent" />{t("Agent（大模型）")}</span>
        <span><i className="program" />{t("程序（确定性）")}</span>
        <span className="g-engine">LangGraph StateGraph</span>
      </div>

      {shown && (
        <section className={`g-card ${shown.state}`} aria-live="polite">
          <header>
            <strong>{t(STEP_LABEL[shown.id])}</strong>
            <em>{t(STATE_LABEL[shown.state])}</em>
          </header>
          <p className="g-who">
            {t(whoRuns(shown))}
            {shown.model ? ` · ${shown.model}` : program(shown) ? ` · ${t("确定性程序")}` : ""}
          </p>
          <p>{t(ROLE[shown.id])}</p>
          <div className="g-tools">
            {(TOOLS[program(shown) ? shown.id : shown.agent] ?? []).map((name) => <code key={name}>{t(name)}</code>)}
          </div>
          {(shown.runs > 0 || shown.state === "running") && (
            <p className="g-stats">
              {t("用时")} {duration(spent(shown))}
              {shown.runs > 1 ? ` · ${t("第")} ${shown.runs} ${t("次")}` : ""}
            </p>
          )}
          {shown.runs > 1 && shown.reason && <p className="g-reason" title={shown.reason}>{shown.reason}</p>}
          {shown.state === "running" && tool && <p className="run-now" title={tool.detail}>{tool.name}</p>}
          {shown.id === "run" && onSearch && (shown.runs > 0 || shown.state === "running") && (
            <button type="button" className="g-search" onClick={onSearch}><Route size={14} />{t("查看搜索过程")}</button>
          )}
        </section>
      )}
    </div>
  );
}
