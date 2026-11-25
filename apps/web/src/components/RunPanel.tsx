import { useEffect, useState } from "react";
import { Activity, Check, CircleAlert, Download, FileText, List, Pause, Play, Route, Workflow, X } from "lucide-react";
import HintButton from "./HintButton";
import RunGraph from "./RunGraph";
import SearchView from "./SearchView";
import { useLocale } from "../locale";
import type { RunView } from "../hooks/useRun";
import type { RunStep } from "../workspace";

export const STEP_LABEL: Record<string, string> = {
  intake: "Intake",
  review_intake: "Intake review",
  run: "Optimizer run",
  analysis: "Briefing draft",
  review_draft: "Draft review",
  render: "Typeset PDF",
  polish: "Polish and PDF",
  review_final: "Final check",
  review_legal: "Legal-reasoning review",
  review_final_legal: "Final legal-reasoning check",
  "front-relay": "Reporting back",
};
export const AGENT_LABEL: Record<string, string> = {
  front: "Front agent",
  review: "Review agent",
  analysis: "Analysis agent",
  polish: "Polish agent",
  program: "Optimizer",
};
export const PROGRAM_LABEL: Record<string, string> = { run: "Optimizer", render: "Typesetter" };
export const whoRuns = (step: RunStep) => step.agent === "program" ? PROGRAM_LABEL[step.id] ?? AGENT_LABEL.program : AGENT_LABEL[step.agent];
const STOP_NOTE: Record<string, string> = {
  delivered: "The report has been delivered.",
  need_front: "More information is needed. Please reply in the chat.",
  rate_limited: "The model usage limit was reached. Resume once it resets; finished steps are kept.",
  agent_failed: "The run stopped on a system error. Finished steps are kept.",
  revision_limit: "The revision limit was reached.",
  system_defect: "The run stopped on a system defect that affects the figures. It can continue after the fix; finished steps are not redone.",
  stopped: "The run was stopped. Finished steps are kept.",
};

export function duration(seconds: number) {
  const whole = Math.max(0, Math.round(seconds));
  if (whole < 60) return `${whole}s`;
  const minutes = Math.floor(whole / 60);
  if (minutes < 60) return `${minutes}m ${whole % 60}s`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

type View = "graph" | "list";

function savedView(): View {
  try {
    return localStorage.getItem("run-view") === "list" ? "list" : "graph";
  } catch {
    return "graph";
  }
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

export default function RunPanel({ caseId, run, onResume, onHalt, onClose, onReport }: {
  caseId?: string;
  run: RunView;
  onReport?: () => void;
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
  const [view, setView] = useState<View>(savedView);
  const [searching, setSearching] = useState(false);
  const pick = (next: View) => {
    setView(next);
    try {
      localStorage.setItem("run-view", next);
    } catch {
      // the choice is a convenience only
    }
  };
  const steps = run.steps.filter((step) => step.id !== "intake" || step.state !== "pending");
  const current = run.steps.find((step) => step.state === "running");
  const total = run.steps.reduce((sum, step) => sum + spent(step, clock), 0);
  const finished = run.status === "delivered";
  const live = [...run.blocks].reverse().find((block) => !block.ended);
  const lastTool = live?.items.filter((item) => item.kind === "tool").at(-1);
  const note = run.stop ? STOP_NOTE[run.stop.stop] : run.can_resume ? STOP_NOTE.stopped : "";
  const waiting = run.stop?.stop === "need_front";
  const headline = current ? t(STEP_LABEL[current.id]) : finished ? t("Delivered") : run.active ? t("Starting…")
    : waiting ? t("Waiting for you") : run.can_resume ? t("Paused") : t("Not running");
  const problem = run.stop && run.stop.stop !== "delivered" && run.stop.stop !== "need_front";
  return (
    <aside className="run-panel" aria-label={t("Progress", "run panel")}>
      <header className="run-head">
        <div>
          <Activity size={17} aria-hidden="true" />
          <h2>{t("Progress", "run panel")}</h2>
        </div>
        <HintButton className="icon-button" aria-label={t("Close the progress panel")} onClick={onClose}>
          <X size={18} />
        </HintButton>
      </header>
      <div className="run-summary">
        <strong aria-live="polite">{headline}</strong>
        <span>{duration(total)}</span>
      </div>
      <div className="run-views" role="tablist" aria-label={t("View")}>
        <button type="button" role="tab" aria-selected={view === "graph"} className={view === "graph" ? "active" : ""} onClick={() => pick("graph")}>
          <Workflow size={14} />{t("Graph")}
        </button>
        <button type="button" role="tab" aria-selected={view === "list"} className={view === "list" ? "active" : ""} onClick={() => pick("list")}>
          <List size={14} />{t("Steps")}
        </button>
      </div>
      {view === "graph" ? (
        <RunGraph steps={run.steps} spent={(step) => spent(step, clock)} finished={finished} tool={lastTool}
          onSearch={caseId ? () => setSearching(true) : undefined} />
      ) : (<>
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
                {step.runs > 1 && <em title={step.reason}>{t("Run {n}").replace("{n}", String(step.runs))}</em>}
                {(step.runs > 0 || step.state === "running") && <time>{duration(spent(step, clock))}</time>}
              </div>
              <small>{t(whoRuns(step))}{step.model ? ` · ${step.model}` : ""}</small>
              {step.state === "running" && lastTool && (
                <p className="run-now" title={lastTool.detail}>{lastTool.name}</p>
              )}
              {step.id === "run" && caseId && (step.runs > 0 || step.state === "running") && (
                <button type="button" className="g-search" onClick={() => setSearching(true)}><Route size={14} />{t("View the search")}</button>
              )}
            </div>
          </li>
        ))}
        <li className={finished ? "done" : "pending"}>
          <Marker state={finished ? "done" : "pending"} />
          <div className="run-step-body">
            <div className="run-step-title"><span>{t("Delivered", "step")}</span></div>
          </div>
        </li>
      </ol>
      </>)}
      <footer className="run-foot">
        {note && (
          <div className={`run-note ${problem ? "is-problem" : ""}`} role="status">
            {problem && <CircleAlert size={15} aria-hidden="true" />}
            <p>{t(note)}{run.stop?.detail && run.stop.stop === "agent_failed" ? ` ${run.stop.detail}` : ""}</p>
          </div>
        )}
        {run.panel && onReport ? (
          <button type="button" className="run-action primary" onClick={onReport} aria-label={t("Open report")}><FileText size={15} />{t("Open report")}</button>
        ) : run.report && <a className="run-action primary" href={run.report} target="_blank" rel="noopener noreferrer"><Download size={15} />{t("Download report")}</a>}
        {run.can_resume && <button type="button" className="run-action primary" onClick={onResume}><Play size={14} />{t("Resume")}</button>}
        {run.active && <button type="button" className="run-action" onClick={onHalt}><Pause size={14} />{t("Stop run")}</button>}
      </footer>
      {searching && caseId && (
        <SearchView caseId={caseId} running={run.steps.some((s) => s.id === "run" && s.state === "running")} onClose={() => setSearching(false)} />
      )}
    </aside>
  );
}
