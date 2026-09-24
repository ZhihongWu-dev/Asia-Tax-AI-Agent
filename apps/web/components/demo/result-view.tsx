"use client";

import { Component, type ReactNode } from "react";
import { ArrowUpRight, ShieldCheck } from "lucide-react";
import {
  type AnalysisResult,
  type ChainRow,
  type FactRow,
  type NodeOutput,
  type TerminalState,
  NODE_INFO,
  OUTPUT_LABELS,
  REFERENCED_NOT_EVALUATED,
  STOPPED_AT,
  TERMINAL_COPY,
  fieldLabel,
  formatValue,
  stoppingStep,
} from "@/lib/fsie";

function SectionHeader({ eyebrow, title, note }: { eyebrow: string; title: string; note?: string }) {
  return (
    <div className="mb-6">
      <span className="inline-flex items-center gap-3 text-xs font-mono text-muted-foreground mb-3">
        <span className="w-6 h-px bg-foreground/30" />
        {eyebrow}
      </span>
      <h3 className="text-3xl font-display tracking-tight">{title}</h3>
      {note && <p className="mt-2 text-sm text-muted-foreground">{note}</p>}
    </div>
  );
}

const OUTPUT_STYLE: Record<NodeOutput, string> = {
  satisfied: "bg-foreground text-background border-foreground",
  not_satisfied: "border-foreground/40 text-foreground",
  unknown: "border-dashed border-foreground/40 text-muted-foreground",
  conflict: "border-destructive text-destructive",
  condition_not_demonstrated: "border-foreground/40 text-foreground",
  human_review_required: "bg-foreground/10 border-foreground/30 text-foreground",
};

function OutputPill({ row }: { row: ChainRow }) {
  if (!row.implemented || !row.output) {
    return (
      <span className="px-2.5 py-1 text-xs font-mono border border-dashed border-foreground/25 text-muted-foreground">
        Not implemented in L0
      </span>
    );
  }
  return (
    <span className={`px-2.5 py-1 text-xs font-mono border whitespace-nowrap ${OUTPUT_STYLE[row.output]}`}>
      {OUTPUT_LABELS[row.output]}
    </span>
  );
}

function FieldList({ fields }: { fields: string[] }) {
  return (
    <ul className="grid gap-2">
      {fields.map((field) => (
        <li key={field} className="flex items-baseline gap-3 text-sm">
          <span className="w-1.5 h-1.5 shrink-0 translate-y-[-2px] bg-foreground" />
          <span>{fieldLabel(field)}</span>
          <span className="font-mono text-xs text-muted-foreground break-all">{field}</span>
        </li>
      ))}
    </ul>
  );
}

function OutcomeCard({ result, expected }: { result: AnalysisResult; expected: TerminalState | null }) {
  const copy = TERMINAL_COPY[result.terminal_state];
  const stopped = result.terminal_state === "research_only_output" ? stoppingStep(result.chain) : undefined;
  const stoppedCopy = stopped ? STOPPED_AT[stopped.node] : undefined;
  const items = result.terminal_state === "stop_and_escalate" ? result.conflict_fields : result.blockers;
  const accent = result.terminal_state === "stop_and_escalate" ? "border-destructive" : "border-foreground";
  return (
    <div className={`relative border ${accent} p-8 lg:p-10`}>
      <span className="text-xs font-mono text-muted-foreground">Outcome · {result.terminal_state}</span>
      <h2 className="mt-3 text-5xl lg:text-6xl font-display tracking-tight leading-[0.95]">{copy.title}</h2>

      {stopped && stoppedCopy ? (
        <div className="mt-6">
          <div className="text-sm font-mono text-muted-foreground">
            Stopped at step {stopped.ordinal} · {NODE_INFO[stopped.node]?.label} ·{" "}
            {stopped.output ? OUTPUT_LABELS[stopped.output] : ""}
          </div>
          <p className="mt-3 text-lg text-muted-foreground leading-relaxed max-w-2xl">
            {stoppedCopy.reason} No tax conclusion is issued.
          </p>
        </div>
      ) : (
        <p className="mt-5 text-lg text-muted-foreground leading-relaxed max-w-2xl">{copy.summary}</p>
      )}

      {items.length > 0 && (
        <div className="mt-8">
          <div className="text-sm font-medium mb-3">{stoppedCopy ? stoppedCopy.listTitle : copy.listTitle}</div>
          <FieldList fields={items} />
        </div>
      )}

      {expected && (
        <p className="mt-8 text-xs font-mono text-muted-foreground">
          {expected === result.terminal_state
            ? `Matches the expected state for this preset (${expected}).`
            : `Expected ${expected} for this preset; the model extracted different facts this time. Check the fact card below.`}
        </p>
      )}
    </div>
  );
}

function FactsTable({ facts, model }: { facts: FactRow[]; model: string }) {
  return (
    <div>
      <SectionHeader
        eyebrow="Fact card"
        title="Candidate facts"
        note={`Proposed by ${model} and checked against the 43-field dictionary. Not yet confirmed by an adviser.`}
      />
      {facts.length === 0 ? (
        <p className="text-sm text-muted-foreground">The model found no facts it could map to the dictionary.</p>
      ) : (
        <div className="border border-foreground/10 divide-y divide-foreground/10">
          {facts.map((fact) => (
            <div key={fact.field} className="grid grid-cols-[1fr_auto] sm:grid-cols-[1.3fr_1fr_auto] gap-x-6 gap-y-1 px-5 py-4">
              <div className="min-w-0">
                <div className="text-sm font-medium">{fieldLabel(fact.field)}</div>
                <div className="text-xs font-mono text-muted-foreground break-all">
                  {fact.field}
                  {fact.statute_locator ? ` · ${fact.statute_locator}` : ""}
                </div>
              </div>
              <div className="text-sm sm:self-center order-3 sm:order-none col-span-2 sm:col-span-1 break-words min-w-0">
                {fact.status === "ai_candidate" ? (
                  formatValue(fact.value, fact.field)
                ) : (
                  <span className={fact.status === "conflict" ? "text-destructive" : "text-muted-foreground italic"}>
                    {fact.status === "conflict" ? "Contradictory statements" : "Stated as unknown"}
                  </span>
                )}
              </div>
              <div className="self-center justify-self-end">
                <span
                  className={`px-2 py-0.5 text-[11px] font-mono border ${
                    fact.status === "conflict"
                      ? "border-destructive text-destructive"
                      : fact.status === "unknown"
                        ? "border-dashed border-foreground/40 text-muted-foreground"
                        : "border-foreground/20 text-muted-foreground"
                  }`}
                >
                  {fact.status === "ai_candidate" ? "AI candidate" : fact.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ChainStep({ row, last }: { row: ChainRow; last: boolean }) {
  const info = NODE_INFO[row.node] ?? { label: row.node, statute: "" };
  const isGate = row.node === "human_gate";
  return (
    <div className="relative grid grid-cols-[2.5rem_1fr] gap-4">
      <div className="flex flex-col items-center">
        <span
          className={`w-10 h-10 flex items-center justify-center border font-mono text-sm ${
            !row.implemented
              ? "border-dashed border-foreground/25 text-muted-foreground"
              : row.output === "satisfied"
                ? "bg-foreground text-background border-foreground"
                : "border-foreground/20"
          }`}
        >
          {isGate ? <ShieldCheck className="w-4 h-4" aria-label="Validation gate" /> : row.ordinal}
        </span>
        {!last && <span className="flex-1 w-px bg-foreground/10 my-1" />}
      </div>
      <div className="pb-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className={row.implemented ? "font-medium" : "text-muted-foreground"}>{info.label}</div>
            <div className="text-xs font-mono text-muted-foreground">
              {info.statute}
              {row.rule_id ? ` · ${row.rule_id}` : ""}
            </div>
          </div>
          <OutputPill row={row} />
        </div>
        {row.blockers.length > 0 && (
          <p className="mt-2 text-sm text-muted-foreground">
            <span className="text-foreground">Missing or unresolved:</span>{" "}
            {row.blockers.map(fieldLabel).join(" · ")}
          </p>
        )}
        {row.escalation_blockers.length > 0 && (
          <p className="mt-2 text-sm text-muted-foreground">
            <span className="text-foreground">For a human to decide:</span>{" "}
            {row.escalation_blockers.map(fieldLabel).join(" · ")}
          </p>
        )}
        {isGate && (
          <p className="mt-2 text-sm text-muted-foreground">
            Recorded on every run and never overridden: at L0 no Hong Kong tax expert has signed off, so no
            result can be treated as professionally validated.
          </p>
        )}
        {row.note && !isGate && <p className="mt-2 text-xs font-mono text-muted-foreground">{row.note}</p>}
      </div>
    </div>
  );
}

function ChainTimeline({ chain, ruleSet, status }: { chain: ChainRow[]; ruleSet: string; status: string }) {
  const steps = chain.filter((r) => r.node !== "human_gate");
  const implemented = steps.filter((r) => r.implemented).length;
  return (
    <div>
      <SectionHeader
        eyebrow="Judgement chain"
        title="Every step, in order"
        note={`Deterministic code, rule set v${ruleSet} (${status}). ${implemented} of ${steps.length} steps implemented; the rest are shown so the gaps stay visible.`}
      />
      <div>
        {chain.map((row, index) => (
          <ChainStep key={row.node} row={row} last={index === chain.length - 1} />
        ))}
      </div>
    </div>
  );
}

function LawSection({ result }: { result: AnalysisResult }) {
  return (
    <div>
      <SectionHeader
        eyebrow="Statutory basis"
        title="The law behind the thresholds"
        note="Quoted from the local snapshot of Cap. 112: the subsections the rule package's numeric thresholds point to. Sources are the candidate mapping of the rules, not yet confirmed as complete by an expert."
      />
      <div className="grid gap-4">
        {result.statute_units.map((unit) => (
          <blockquote key={unit.locator} className="border-l-2 border-foreground pl-5 py-1">
            <div className="text-xs font-mono text-muted-foreground mb-2">
              Inland Revenue Ordinance (Cap. 112) {unit.locator}
            </div>
            <p className="font-display text-xl leading-snug">{unit.text}</p>
            {REFERENCED_NOT_EVALUATED[unit.locator] && (
              <p className="mt-2 text-xs font-mono text-muted-foreground">{REFERENCED_NOT_EVALUATED[unit.locator]}</p>
            )}
          </blockquote>
        ))}
      </div>
      {result.sources.length > 0 && (
        <ul className="mt-8 border border-foreground/10 divide-y divide-foreground/10">
          {result.sources.map((source) => (
            <li key={source.source_id}>
              <a
                href={source.url ?? "#"}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between gap-4 px-5 py-3 text-sm hover:bg-foreground/[0.02] group"
              >
                <span>{source.title ?? source.source_id}</span>
                <ArrowUpRight className="w-4 h-4 shrink-0 text-muted-foreground group-hover:text-foreground" />
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RunDetails({ result }: { result: AnalysisResult }) {
  const rows: [string, string][] = [
    ["Case", result.case_id],
    ["Execution batch", result.execution_batch],
    ["Model", result.model],
    ["Prompt version", `${result.prompt_version} · ${result.repair_rounds} repair round(s)`],
    ["Rule package", `v${result.rule_set_version} · ${result.rule_set_status}`],
    ["Engine commit", result.engine_commit ? result.engine_commit.slice(0, 12) : "unknown"],
    ["Time", `${(result.timing_ms.total / 1000).toFixed(1)} s total · ${(result.timing_ms.extraction / 1000).toFixed(1)} s in the model`],
  ];
  return (
    <div>
      <SectionHeader
        eyebrow="Provenance"
        title="Run details"
        note="Node outputs, the fact snapshot, the model, prompt version and engine commit are stored in the local database for audit."
      />
      <dl className="border border-foreground/10 divide-y divide-foreground/10 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[10rem_1fr] gap-4 px-5 py-3">
            <dt className="text-muted-foreground">{label}</dt>
            <dd className="font-mono text-xs break-all self-center">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

// One malformed value must not blank the whole page.
class ResultBoundary extends Component<{ children: ReactNode; resetKey: string }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidUpdate(prev: { resetKey: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.failed) this.setState({ failed: false });
  }

  render() {
    if (this.state.failed) {
      return (
        <p role="alert" className="border border-destructive px-5 py-4 text-sm text-destructive">
          The result could not be displayed. The run itself is stored; see the API terminal for details.
        </p>
      );
    }
    return this.props.children;
  }
}

export function ResultView({ result, expected }: { result: AnalysisResult; expected: TerminalState | null }) {
  return (
    <ResultBoundary resetKey={result.execution_batch}>
      <div className="grid gap-16">
        <OutcomeCard result={result} expected={expected} />
        <FactsTable facts={result.facts} model={result.model} />
        <ChainTimeline chain={result.chain} ruleSet={result.rule_set_version} status={result.rule_set_status} />
        <LawSection result={result} />
        <RunDetails result={result} />
      </div>
    </ResultBoundary>
  );
}
