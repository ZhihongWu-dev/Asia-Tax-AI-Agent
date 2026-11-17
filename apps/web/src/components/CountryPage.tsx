import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { api, ApiError, type AtlasCell, type AtlasCountry, type AtlasPartner } from "../api";
import { useLocale } from "../locale";
import BrandLoader from "./BrandLoader";
import { CiteChip } from "./ClauseDialog";
import { TermCard } from "./Glossary";
import { humanize, jurName, num, paramValue, rate } from "./atlasFormat";
import { rateColour } from "./atlasMap";

type Section = "dividend" | "provisions" | "glossary" | "sources";
const SECTIONS: [Section, string][] = [["dividend", "股息税"], ["provisions", "全部条款"], ["glossary", "该辖区术语"], ["sources", "来源文件"]];

/** One jurisdiction: its dividend withholding, treaty rates by recipient, every library parameter, terms and sources. */
export default function CountryPage({ code, onBack, onOpen, onClause }: {
  code: string; onBack: () => void; onOpen: (code: string) => void; onClause: (id: string) => void;
}) {
  const { t, locale } = useLocale();
  const [data, setData] = useState<AtlasCountry | null>(null);
  const [error, setError] = useState("");
  const [section, setSection] = useState<Section>("dividend");
  useEffect(() => {
    let live = true;
    setData(null); setError(""); setSection("dividend");
    api.atlasCountry(code).then((d) => live && setData(d)).catch((e) => live && setError(e instanceof ApiError ? e.code : "network_error"));
    return () => { live = false; };
  }, [code]);
  if (error) return <div className="atlas-error" role="alert">{t(`error:${error}`)} <button onClick={onBack}>{t("返回地图")}</button></div>;
  if (!data) return <BrandLoader label={t("正在载入…")} />;
  const treaties = data.partners.filter((p) => p.treaty.length).length;
  const jurs = Object.fromEntries(data.partners.map((p) => [p.code, p]));
  return (
    <div className="atlas-country">
      <button className="atlas-back" onClick={onBack}><ArrowLeft size={15} />{t("返回地图")}</button>
      <div className="atlas-country-head">
        <h2>{jurName(data, locale)}</h2>
        <span className="atlas-chip">{data.code.toUpperCase()}</span>
        <span className="atlas-chip">{data.currency}</span>
      </div>
      <section className="atlas-stats">
        <Stat label={t("付给非居民公司的股息预提税")} cell={data.headline.wht_company} onClause={onClause} />
        <Stat label={t("付给非居民个人的股息预提税")} cell={data.headline.wht_individual} onClause={onClause} />
        <div>
          <strong>{data.cit ? paramValue(data.cit.value, data.cit.unit) : "—"}</strong>
          <span>{t("企业所得税税率")}</span>
          {data.cit && <CiteChip id={data.cit.cite_id} onOpen={onClause} />}
        </div>
        <div><strong>{treaties}</strong><span>{t("与其他已收录辖区的协定")}</span></div>
      </section>
      <nav className="atlas-subtabs" aria-label={t("辖区详情")}>
        {SECTIONS.map(([s, label]) => (
          <button key={s} aria-pressed={section === s} onClick={() => setSection(s)}>{t(label)}</button>
        ))}
      </nav>
      {section === "dividend" && <Dividend data={data} onOpen={onOpen} onClause={onClause} />}
      {section === "provisions" && <Provisions data={data} onClause={onClause} />}
      {section === "glossary" && (
        <div className="atlas-terms">
          {data.terms.length ? data.terms.map((term) => <TermCard key={term.key} term={term} jurs={jurs} self={data} onOpen={onOpen} onClause={onClause} />)
            : <p className="atlas-muted">{t("没有匹配的术语")}</p>}
        </div>
      )}
      {section === "sources" && (
        <section className="atlas-card">
          <table className="atlas-table">
            <thead><tr><th>{t("文件")}</th><th>{t("类型")}</th><th>{t("语言")}</th><th>{t("生效")}</th><th /></tr></thead>
            <tbody>
              {data.docs.map((d) => (
                <tr key={d.id}>
                  <td><strong>{d.title || d.id}</strong><span className="atlas-cite-id">{d.id}</span></td>
                  <td>{d.type}</td><td>{d.lang}</td>
                  <td>{d.effective_from || "—"}{d.effective_to ? ` – ${d.effective_to}` : ""}</td>
                  <td>{d.url && <a href={d.url} target="_blank" rel="noreferrer" aria-label={t("打开官方来源")}><ExternalLink size={14} /></a>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

function Stat({ label, cell, onClause }: { label: string; cell: AtlasCell; onClause: (id: string) => void }) {
  const { t } = useLocale();
  const cite = cell.absent?.[0]?.cite_id ?? cell.cite_ids[0];
  return (
    <div>
      <strong>{rate(cell)}</strong>
      <span>{label}</span>
      {cell.absent?.length ? <em>{cell.absent.map((a) => a.statement).join(" ")}</em> : cell.needs.length ? <em>{t("取决于")}: {cell.needs.join(", ")}</em> : null}
      {cite && <CiteChip id={cite} onOpen={onClause} />}
    </div>
  );
}

function Dividend({ data, onOpen, onClause }: { data: AtlasCountry; onOpen: (c: string) => void; onClause: (id: string) => void }) {
  const { t, locale } = useLocale();
  const partners = [...data.partners].sort((a, b) => (a.qualifying.floor ?? 99) - (b.qualifying.floor ?? 99) || a.name.localeCompare(b.name));
  return (
    <>
      <section className="atlas-card">
        <div className="atlas-card-head">
          <div>
            <h3>{t("按收款方所在辖区的股息预提税")}</h3>
            <p className="atlas-muted">{t("条形为有利一端；浅色延伸至不利一端（取决于尚待确认的事实或判断）。虚线为不适用协定时的国内税率。")}</p>
          </div>
        </div>
        <TreatyChart partners={partners} domestic={data.headline.wht_company.ceiling} />
      </section>
      <section className="atlas-card">
        <h3>{t("国内规则")}</h3>
        <div className="atlas-rules">
          {(["wht_company", "wht_individual"] as const).map((m) => {
            const c = data.headline[m];
            return (
              <div key={m}>
                <h4>{t(m === "wht_company" ? "付给非居民公司" : "付给非居民个人")}: {rate(c)}</h4>
                {c.absent?.map((a) => <p key={a.id}>{a.statement} <CiteChip id={a.cite_id} onOpen={onClause} /></p>)}
                {c.rules.length > 0 && <p className="atlas-muted">{t("适用规则")}: {c.rules.join(", ")}</p>}
                <div className="atlas-cites">{c.cite_ids.map((id) => <CiteChip key={id} id={id} onOpen={onClause} />)}</div>
              </div>
            );
          })}
        </div>
      </section>
      <section className="atlas-card">
        <h3>{t("协定税率")}</h3>
        <div className="atlas-table-wrap">
          <table className="atlas-table">
            <thead>
              <tr>
                <th>{t("收款方辖区")}</th><th>{t("协定")}</th>
                <th>{t("合格公司")}<small>{t("持股 100%，满 24 个月")}</small></th>
                <th>{t("组合投资公司")}<small>{t("持股 5%")}</small></th>
                <th>{t("个人收款方")}</th><th>{t("条件")}</th>
              </tr>
            </thead>
            <tbody>
              {partners.map((p) => (
                <tr key={p.code}>
                  <td><button className="atlas-link" onClick={() => onOpen(p.code)}>{jurName(p, locale)}</button></td>
                  <td>{p.treaty.length ? p.treaty.map((x) => (
                    <span key={x.doc_id} className="atlas-treaty">{x.in_force_from?.slice(0, 4) || ""}{x.mli ? " · MLI" : ""}
                      <CiteChip id={x.doc_id} onOpen={() => x.url && window.open(x.url, "_blank", "noreferrer")} /></span>
                  )) : <span className="atlas-muted">{t("无协定")}</span>}</td>
                  <RateCell c={p.qualifying} onClause={onClause} />
                  <RateCell c={p.portfolio} onClause={onClause} />
                  <RateCell c={p.individual} onClause={onClause} />
                  <td>{Object.entries(p.conditions).map(([k, v]) => (
                    <span key={k} className="atlas-condition">{t(k === "holding_pct_min" ? "最低持股" : "最低持有期")} {paramValue(v.value, v.unit)} <CiteChip id={v.cite_id} onOpen={onClause} /></span>
                  ))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function RateCell({ c, onClause }: { c: AtlasCell; onClause: (id: string) => void }) {
  const treaty = c.cite_ids.find((id) => id.startsWith("treaty."));
  return (
    <td className="atlas-rate-cell">
      <span className="atlas-dot" style={{ background: rateColour(c.floor) }} />{rate(c)}
      {c.needs.length > 0 && <small title={c.needs.join(", ")}>{c.needs.join(", ")}</small>}
      {treaty && <CiteChip id={treaty} onOpen={onClause} />}
    </td>
  );
}

function TreatyChart({ partners, domestic }: { partners: AtlasPartner[]; domestic: number | null }) {
  const { t, locale } = useLocale();
  const rowH = 36, left = 150, right = 60, width = 760, top = 26;
  const max = Math.max(25, domestic ?? 0, ...partners.flatMap((p) => [p.qualifying.ceiling ?? 0, p.portfolio.ceiling ?? 0, p.individual.ceiling ?? 0]));
  const x = (v: number) => left + ((width - left - right) * v) / max;
  const series: [keyof Pick<AtlasPartner, "qualifying" | "portfolio" | "individual">, string, string][] = [
    ["qualifying", "#173f35", "合格公司"], ["portfolio", "#3f9a77", "组合投资公司"], ["individual", "#9dc5b2", "个人收款方"]];
  const height = top + partners.length * rowH + 30;
  return (
    <div className="atlas-chart">
      <div className="atlas-chart-legend">
        {series.map(([, c, label]) => <span key={label}><i style={{ background: c }} />{t(label)}</span>)}
        <span><i className="is-line" />{t("国内税率")}</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={t("按收款方所在辖区的股息预提税")}>
        {[0, 5, 10, 15, 20, 25].filter((v) => v <= max).map((v) => (
          <g key={v}>
            <line x1={x(v)} x2={x(v)} y1={top - 6} y2={height - 24} className="atlas-grid" />
            <text x={x(v)} y={height - 8} textAnchor="middle" className="atlas-axis">{v}%</text>
          </g>
        ))}
        {partners.map((p, i) => {
          const y = top + i * rowH;
          return (
            <g key={p.code}>
              <text x={left - 10} y={y + 17} textAnchor="end" className="atlas-label">{jurName(p, locale)}</text>
              {!p.treaty.length && <text x={left - 10} y={y + 29} textAnchor="end" className="atlas-axis">{t("无协定")}</text>}
              {series.map(([key, colour], j) => {
                const c = p[key];
                if (c.floor === null || c.ceiling === null) return null;
                const yy = y + 4 + j * 9;
                return (
                  <g key={key}>
                    {c.ceiling > c.floor && <rect x={x(c.floor)} y={yy} width={x(c.ceiling) - x(c.floor)} height={7} fill={colour} opacity={0.22} rx={1} />}
                    <rect x={left} y={yy} width={Math.max(1.5, x(c.floor) - left)} height={7} fill={colour} rx={1} />
                    <text x={x(c.ceiling) + 5} y={yy + 6.5} className="atlas-value">{rate(c)}</text>
                  </g>
                );
              })}
            </g>
          );
        })}
        {domestic !== null && (
          <g>
            <line x1={x(domestic)} x2={x(domestic)} y1={top - 10} y2={height - 24} className="atlas-domestic" />
            <text x={x(domestic)} y={top - 13} textAnchor="middle" className="atlas-domestic-label">{t("国内")} {num(domestic)}%</text>
          </g>
        )}
      </svg>
    </div>
  );
}

function Provisions({ data, onClause }: { data: AtlasCountry; onClause: (id: string) => void }) {
  const { t, locale } = useLocale();
  return (
    <>
      {data.slots.map((s) => {
        const params = data.params.filter((p) => p.slot === s.slot);
        const absent = data.absent.filter((a) => a.id.includes(`.${s.slot}`) || (s.slot === "penalty" && a.id.includes(".page_")));
        if (!params.length && !absent.length) return null;
        return (
          <details key={s.slot} className="atlas-card atlas-slot" open={s.slot === "outbound_wht"}>
            <summary><h3>{locale === "zh" ? s.title_zh : s.title}</h3><span className="atlas-muted">{params.length} {t("个参数")}{absent.length ? ` · ${absent.length} ${t("条不征税记录")}` : ""}</span></summary>
            {absent.map((a) => (
              <div key={a.id} className="atlas-absent"><strong>{t("不征税记录")}</strong> {a.statement} <CiteChip id={a.cite_id} onOpen={onClause} /></div>
            ))}
            {params.length > 0 && (
              <div className="atlas-table-wrap">
                <table className="atlas-table atlas-params">
                  <thead><tr><th>{t("参数")}</th><th>{t("数值")}</th><th>{t("适用")}</th><th>{t("生效")}</th><th>{t("原文")}</th></tr></thead>
                  <tbody>
                    {params.map((p) => (
                      <tr key={p.param_id} className={p.superseded_by || p.effective_to ? "is-old" : ""}>
                        <td><strong>{humanize(p.name)}</strong><span className="atlas-cite-id">{p.param_id}</span></td>
                        <td className="atlas-num">{paramValue(p.value, p.unit)}</td>
                        <td>{p.scope.includes("-") ? `${t("协定")} ${p.scope.toUpperCase()}` : t("国内")} · {p.subject}</td>
                        <td>{p.effective_from || "—"}{p.effective_to ? ` – ${p.effective_to}` : ""}</td>
                        <td><q>{p.quote}</q> <CiteChip id={p.cite_id} onOpen={onClause} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </details>
        );
      })}
    </>
  );
}
