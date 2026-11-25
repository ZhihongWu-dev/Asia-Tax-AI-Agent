import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowDown, ExternalLink, FileText, X } from "lucide-react";
import { api, ApiError } from "../api";
import { useLocale } from "../locale";
import { useOverlayFocus } from "../hooks/useOverlayFocus";
import ClauseDialog from "./ClauseDialog";
import type { ReportBlock, ReportCard, ReportFlowStructure, ReportFigures, ReportSource, ReportState, ReportStep } from "../workspace";
import "../report-panel.css";

// Browse only: the client report block by block, as GET /api/cases/{id}/panel gives it. A block being written or updated
// arrives without content and shows a neutral placeholder.
const STATE_LABEL: Record<ReportBlock["state"], string> = { final: "Final", review: "Being reviewed", writing: "Being written", updating: "Updating" };
const blockTitle = (block: ReportBlock, t: (s: string) => string) => block.title || (block.id === "summary" ? t("Summary") : block.id);

function Md({ text }: { text: string }) {
  return (
    <div className="markdown-answer rp-md">
      <Markdown remarkPlugins={[remarkGfm]} skipHtml disallowedElements={["img"]} components={{
        a: ({ children, href }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>,
        table: ({ children }) => <div className="answer-table"><table>{children}</table></div>,
      }}>{text}</Markdown>
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return <div className="rp-row"><dt>{label}</dt><dd>{children}</dd></div>;
}

function List({ items }: { items: string[] }) {
  return items.length === 1 ? <>{items[0]}</> : <ul>{items.map((x, i) => <li key={i}>{x}</li>)}</ul>;
}

function Figures({ figures }: { figures: ReportFigures }) {
  const { t } = useLocale();
  const rows: [string, string | undefined][] = [
    ["Recommended plan", figures.plan], ["Tax on this dividend", figures.this_tax], ["Saving per payment", figures.saving],
    ["One-off cost", figures.one_off], ["Payback", figures.payback && t("{n} payments").replace("{n}", figures.payback)],
  ];
  return (
    <div className="rp-figures">
      {figures.route && <p className="rp-route">{figures.route}</p>}
      <dl>
        {rows.filter(([, v]) => v).map(([k, v]) => <div key={k}><dt>{t(k)}</dt><dd>{v}</dd></div>)}
      </dl>
    </div>
  );
}

function Structure({ s }: { s: ReportFlowStructure }) {
  return (
    <figure className="rp-structure">
      <figcaption>{s.title}</figcaption>
      <ol className="rp-chain">
        {s.chain.map((node, i) => (
          <li key={i}>
            <div className={`rp-node ${i === s.dividend_to ? "receives" : ""}`}>{node.name}</div>
            {i < s.chain.length - 1 && (
              <div className="rp-link"><ArrowDown size={14} aria-hidden="true" /><span>{s.holds[i] ?? ""}</span></div>
            )}
          </li>
        ))}
      </ol>
      {s.dividend_label && <p className="rp-dividend">{s.dividend_label}</p>}
      {s.result && <p className="rp-result">{s.result}</p>}
    </figure>
  );
}

function Flow({ flow }: { flow: NonNullable<ReportBlock["flow"]> }) {
  return (
    <div className="rp-flow">
      <div className="rp-structures">
        {flow.current && <Structure s={flow.current} />}
        {flow.target && <Structure s={flow.target} />}
      </div>
      {Boolean(flow.steps?.length) && (
        <div className="rp-flow-steps">
          {flow.steps_title && <h4>{flow.steps_title}</h4>}
          <ol>{flow.steps!.map((step, i) => <li key={i}>{step}</li>)}</ol>
        </div>
      )}
    </div>
  );
}

function Source({ source, onCite }: { source: ReportSource; onCite: (id: string) => void }) {
  const { t } = useLocale();
  if (source.url) return (
    <span>
      <a href={source.url} target="_blank" rel="noopener noreferrer">{source.title || source.url}<ExternalLink size={12} aria-hidden="true" /></a>
      {source.accessed && <small> ({t("accessed {date}").replace("{date}", source.accessed)})</small>}
    </span>
  );
  if (source.cite) return (
    <button type="button" className="rp-cite" onClick={() => onCite(source.cite!)} aria-label={`${t("Provision")} ${source.cite}`}>
      {t("Provision")}
    </button>
  );
  return null;
}

function Steps({ steps, onCite }: { steps: ReportStep[]; onCite: (id: string) => void }) {
  const { t } = useLocale();
  return (
    <ol className="rp-steps">
      {steps.map((step, i) => (
        <li key={i}>
          <span className="rp-step-n" aria-hidden="true">{i + 1}</span>
          <div>
            <h4>{step.title}</h4>
            {step.when && (
              <p className="rp-when">
                {step.date ? <time dateTime={step.date}>{step.when}</time> : step.when}
                {step.deadline === "legal" && <span className="rp-tag legal">{t("set by law")}</span>}
                {step.deadline === "estimate" && <span className="rp-tag">{t("estimate")}</span>}
              </p>
            )}
            <dl className="rp-rows">
              {step.who && <Row label={t("Who")}>{step.who}</Row>}
              {step.where && <Row label={t("Where")}>{step.where}</Row>}
              {step.how && <Row label={t("How")}>{step.how}</Row>}
              {Boolean(step.documents?.length) && <Row label={t("Documents")}><List items={step.documents!} /></Row>}
            </dl>
            {step.reason && <p className="rp-reason">{step.reason}</p>}
            {Boolean(step.sources?.length) && (
              <p className="rp-sources">
                <b>{t("Source")}</b>
                {step.sources!.map((s, k) => <Source key={k} source={s} onCite={onCite} />)}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function Card({ card, n }: { card: ReportCard; n: number }) {
  const { t } = useLocale();
  const denied = card.if_denied && /^[A-Z]{3} [\d,.]+$/.test(card.if_denied)
    ? t("{x} more on this dividend").replace("{x}", card.if_denied) : card.if_denied;
  return (
    <article className="rp-card">
      <header>
        <span className="rp-step-n" aria-hidden="true">{n}</span>
        <div>
          <h4>{card.title}</h4>
          {card.answer && <p>{card.answer}</p>}
        </div>
      </header>
      <dl className="rp-rows">
        {card.provision && <Row label={t("Provision", "card")}>{card.provision}</Row>}
        {Boolean(card.for?.length) && <Row label={t("For")}><List items={card.for!} /></Row>}
        {Boolean(card.against?.length) && <Row label={t("Against")}><List items={card.against!} /></Row>}
        {Boolean(card.routes?.length) && <Row label={t("Routes")}><List items={card.routes!} /></Row>}
        {card.reason && <Row label={t("Reason")}>{card.reason}</Row>}
        {card.confirm_by && <Row label={t("Confirmed by")}>{card.confirm_by}{card.how ? `; ${card.how}` : ""}</Row>}
        {denied && <Row label={t("If denied")}>{denied}</Row>}
      </dl>
    </article>
  );
}

function BlockBody({ block, onCite }: { block: ReportBlock; onCite: (id: string) => void }) {
  const { t } = useLocale();
  if (block.state === "writing" || block.state === "updating") return (
    <div className="rp-placeholder" aria-busy="true">
      <i /><i /><i />
      <span>{t(STATE_LABEL[block.state])}</span>
    </div>
  );
  // steps and cards carry what the markdown says, item by item; the markdown is the fallback without them
  const structured = Boolean(block.steps?.length || block.cards?.length);
  return (
    <>
      {block.figures && <Figures figures={block.figures} />}
      {block.md && !structured && <Md text={block.md} />}
      {block.flow && <Flow flow={block.flow} />}
      {Boolean(block.steps?.length) && <Steps steps={block.steps!} onCite={onCite} />}
      {Boolean(block.cards?.length) && <div className="rp-cards">{block.cards!.map((c, i) => <Card key={c.key} card={c} n={i + 1} />)}</div>}
      {Boolean(block.notes?.length) && (
        <div className="rp-notes">
          <h4>{t("Further notes")}</h4>
          {block.notes!.map((note, i) => <p key={i}><b>{note.title}.</b> {note.text}</p>)}
        </div>
      )}
      {block.tables?.map((table, i) => <Md key={i} text={table} />)}
      {block.gaps && (
        <div className="rp-gaps">
          <h4>{t("Information still needed")}</h4>
          <Md text={block.gaps} />
        </div>
      )}
    </>
  );
}

export default function ReportPanel({ caseId, onClose }: { caseId: string; onClose: () => void }) {
  const { t } = useLocale();
  const ref = useRef<HTMLDivElement>(null);
  const [cite, setCite] = useState<string | null>(null);
  useOverlayFocus(ref, true, true, () => (cite ? setCite(null) : onClose()));   // Escape closes the provision first
  const [data, setData] = useState<ReportState | null>(null);
  const [failed, setFailed] = useState("");
  useEffect(() => {
    let stop = false, timer = 0;
    const load = () => api.panel(caseId).then((next) => {
      if (stop) return;
      setData(next);
      setFailed("");
      if (next.status !== "delivered") timer = window.setTimeout(load, 5000);
    }).catch((error) => {
      if (stop) return;
      setFailed(error instanceof ApiError ? error.code : "network_error");
      timer = window.setTimeout(load, 5000);
    });
    load();
    return () => { stop = true; clearTimeout(timer); };
  }, [caseId]);

  const jump = (id: string) => document.getElementById(`rp-block-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  const progress = data?.progress;
  const body = !data ? (
    <p className="sv-wait">{failed === "panel_not_ready" ? t("The report is not ready yet.") : failed ? t("Could not load the report. Retrying shortly.") : t("Loading the report…")}</p>
  ) : (
    <div className="rp-body">
      <nav className="rp-outline" aria-label={t("Report outline")}>
        <ol>
          {data.blocks.map((block) => (
            <li key={block.id}>
              <button type="button" onClick={() => jump(block.id)} aria-label={`${blockTitle(block, t)} · ${t(STATE_LABEL[block.state])}`}>
                <i className={`rp-dot ${block.state}`} aria-hidden="true" />
                <span>{blockTitle(block, t)}</span>
              </button>
            </li>
          ))}
        </ol>
      </nav>
      <div className="rp-main">
        {data.blocks.map((block) => (
          <section key={block.id} id={`rp-block-${block.id}`} className={`rp-block ${block.state}`} aria-labelledby={`rp-title-${block.id}`}>
            <header>
              <h3 id={`rp-title-${block.id}`}>{blockTitle(block, t)}</h3>
              <span className={`rp-chip ${block.state}`}>{t(STATE_LABEL[block.state])}</span>
            </header>
            <BlockBody block={block} onCite={setCite} />
          </section>
        ))}
      </div>
    </div>
  );

  // the provision dialog is a sibling portal: inside the backdrop, a click on its own backdrop would close the report too
  return <>{createPortal(
    <div className="sv-backdrop rp-backdrop" onClick={onClose}>
      <div className="sv-dialog rp-dialog" ref={ref} role="dialog" aria-modal="true" aria-labelledby="rp-heading" onClick={(e) => e.stopPropagation()}>
        <header className="rp-head">
          <div className="rp-head-text">
            <h2 id="rp-heading"><FileText size={17} aria-hidden="true" />{data?.title || t("Client report")}</h2>
            <p>
              {data?.date}
              {data && progress && progress.total > 0 && (
                <span aria-live="polite">
                  {data.date ? " · " : ""}
                  {t("{final} of {total} written parts reviewed").replace("{final}", String(progress.final)).replace("{total}", String(progress.total))}
                </span>
              )}
            </p>
          </div>
          <div className="rp-head-actions">
            {data?.export_ready && data.export ? (
              <a className="run-action primary" href={data.export} target="_blank" rel="noopener noreferrer">
                <ExternalLink size={15} />{t("Export report")}
              </a>
            ) : (
              <div className="rp-export-wait">
                <button type="button" className="run-action" disabled aria-describedby="rp-export-note">{t("Export report")}</button>
                <small id="rp-export-note">{t("Available once every part is reviewed")}</small>
              </div>
            )}
            <button type="button" className="icon-button" aria-label={t("Close")} onClick={onClose}><X size={18} /></button>
          </div>
        </header>
        {body}
      </div>
    </div>,
    document.body,
  )}{cite && <ClauseDialog citeId={cite} onClose={() => setCite(null)} />}</>;
}
