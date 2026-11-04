import { useEffect, useState } from "react";
import { Activity, Check, CircleAlert, Download, Pause, Play, X } from "lucide-react";
import HintButton from "./HintButton";
import { useLocale } from "../locale";
import type { RunView } from "../hooks/useRun";
import type { RunStep } from "../workspace";

export const STEP_LABEL: Record<string, string> = {
  intake: "资料接收",
  review_intake: "资料复核",
  run: "优化计算",
  analysis: "撰写简报",
  review_draft: "简报复核",
  polish: "润色与出具 PDF",
  review_final: "终稿比对",
  review_legal: "法律理由复核",
  review_final_legal: "终稿法律理由复核",
  "front-relay": "向你汇报",
};
export const AGENT_LABEL: Record<string, string> = {
  front: "前台 Agent",
  review: "复核 Agent",
  analysis: "分析 Agent",
  polish: "润色 Agent",
  program: "优化程序",
};
const STOP_NOTE: Record<string, string> = {
  delivered: "报告已交付。",
  need_front: "需要你补充信息，请在对话中回复。",
  rate_limited: "模型额度已用尽。额度恢复后可继续，已完成的步骤不会重做。",
  agent_failed: "运行因系统错误停止，已完成的步骤不会重做。",
  revision_limit: "修订次数已达上限。",
  system_defect: "发现影响数字的系统缺陷，运行已停止。修复后可继续，已完成的步骤不会重做。",
  stopped: "运行已手动停止，已完成的步骤不会重做。",
};

export function duration(seconds: number) {
  const whole = Math.max(0, Math.round(seconds));
  if (whole < 60) return `${whole}s`;
  const minutes = Math.floor(whole / 60);
  if (minutes < 60) return `${minutes}m ${whole % 60}s`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

function spent(step: RunStep, clock: number) {
  const live = step.state === "running" && step.started ? (clock - Date.parse(step.started)) / 1000 : 0;
  return step.seconds + live;
}

function Marker({ state }: { state: RunStep["state"] }) {
  if (state === "done") return <span className="run-marker done"><Check size={13} strokeWidth={3} /></span>;
  if (state === "failed") return <span className="run-marker failed"><X size={13} strokeWidth={3} /></span>;
  if (state === "stopped") return <span className="run-marker stopped"><Pause size={11} fill="currentColor" /></span>;
  return <span className={`run-marker ${state}`} />;
}

export default function RunPanel({ run, onResume, onHalt, onClose }: {
  run: RunView;
  onResume: () => void;
  onHalt: () => void;
  onClose: () => void;
}) {
  const { t } = useLocale();
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    if (!run.active) return;
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [run.active]);
  const steps = run.steps.filter((step) => step.id !== "intake" || step.state !== "pending");
  const current = run.steps.find((step) => step.state === "running");
  const total = run.steps.reduce((sum, step) => sum + spent(step, clock), 0);
  const finished = run.status === "delivered";
  const live = [...run.blocks].reverse().find((block) => !block.ended);
  const lastTool = live?.items.filter((item) => item.kind === "tool").at(-1);
  const note = run.stop ? STOP_NOTE[run.stop.stop] : run.can_resume ? STOP_NOTE.stopped : "";
  const waiting = run.stop?.stop === "need_front";
  const headline = current ? t(STEP_LABEL[current.id]) : finished ? t("已交付") : run.active ? t("正在启动…")
    : waiting ? t("等待你的回复") : run.can_resume ? t("已暂停") : t("未在运行");
  const problem = run.stop && run.stop.stop !== "delivered" && run.stop.stop !== "need_front";
  return (
    <aside className="run-panel" aria-label={t("运行进度")}>
      <header className="run-head">
        <div>
          <Activity size={17} aria-hidden="true" />
          <h2>{t("运行进度")}</h2>
        </div>
        <HintButton className="icon-button" aria-label={t("关闭进度面板")} onClick={onClose}>
          <X size={18} />
        </HintButton>
      </header>
      <div className="run-summary">
        <strong aria-live="polite">{headline}</strong>
        <span>{duration(total)}</span>
      </div>
      <div className="run-track" aria-hidden="true">
        {run.steps.map((step) => <i key={step.id} className={step.state} />)}
      </div>
      <ol className="run-steps">
        {steps.map((step) => (
          <li key={step.id} className={step.state}>
            <Marker state={step.state} />
            <div className="run-step-body">
              <div className="run-step-title">
                <span>{t(STEP_LABEL[step.id])}</span>
                {step.runs > 1 && <em title={step.reason}>{t("第")} {step.runs} {t("次")}</em>}
                {(step.runs > 0 || step.state === "running") && <time>{duration(spent(step, clock))}</time>}
              </div>
              <small>{t(AGENT_LABEL[step.agent])}{step.model ? ` · ${step.model}` : ""}</small>
              {step.state === "running" && lastTool && (
                <p className="run-now" title={lastTool.detail}>{lastTool.name}</p>
              )}
            </div>
          </li>
        ))}
        <li className={finished ? "done" : "pending"}>
          <Marker state={finished ? "done" : "pending"} />
          <div className="run-step-body">
            <div className="run-step-title"><span>{t("交付")}</span></div>
          </div>
        </li>
      </ol>
      <footer className="run-foot">
        {note && (
          <div className={`run-note ${problem ? "is-problem" : ""}`} role="status">
            {problem && <CircleAlert size={15} aria-hidden="true" />}
            <p>{t(note)}{run.stop?.detail && run.stop.stop === "agent_failed" ? ` ${run.stop.detail}` : ""}</p>
          </div>
        )}
        {run.report && <a className="run-action primary" href={run.report} target="_blank" rel="noopener noreferrer"><Download size={15} />{t("下载报告")}</a>}
        {run.can_resume && <button type="button" className="run-action primary" onClick={onResume}><Play size={14} />{t("继续运行")}</button>}
        {run.active && <button type="button" className="run-action" onClick={onHalt}><Pause size={14} />{t("停止运行")}</button>}
      </footer>
    </aside>
  );
}
