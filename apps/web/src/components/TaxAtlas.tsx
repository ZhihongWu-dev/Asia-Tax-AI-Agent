import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { BookOpen, Earth, LocateFixed, Map as MapIcon, Minus, Plus } from "lucide-react";
import { api, ApiError, type AtlasJurisdiction, type AtlasMap } from "../api";
import { useLocale } from "../locale";
import HintButton from "./HintButton";
import BrandLoader from "./BrandLoader";
import ClauseDialog from "./ClauseDialog";
import CountryPage from "./CountryPage";
import Glossary from "./Glossary";
import { H, RAMP, SPHERE, W, WORLD, anchor, loadWorld, rateColour, regionView, zoomAt, type Shape, type View } from "./atlasMap";
import { jurName, num, rate } from "./atlasFormat";
import "../atlas.css";

export type Metric = "wht_company" | "wht_individual";
const METRIC_LABEL: Record<Metric, string> = { wht_company: "付给非居民公司", wht_individual: "付给非居民个人" };

/** Tax graph: dividend tax across the library's jurisdictions (apps/api/atlas.py: rule layer + library on Supabase). */
export default function TaxAtlas() {
  const { t } = useLocale();
  const [tab, setTab] = useState<"map" | "glossary">("map");
  const [country, setCountry] = useState<string | null>(null);
  const [clause, setClause] = useState<string | null>(null);
  const [metric, setMetric] = useState<Metric>("wht_company");
  const [data, setData] = useState<AtlasMap | null>(null);
  const [error, setError] = useState("");
  const top = useRef<HTMLDivElement>(null);
  const [attempt, setAttempt] = useState(0);
  const load = () => setAttempt(value => value + 1);
  useEffect(() => {
    let live = true;
    setError("");
    api.atlasMap().then(d => live && setData(d)).catch((e) => live && setError(e instanceof ApiError ? e.code : "network_error"));
    return () => { live = false; };
  }, [attempt]);
  const open = (code: string) => {
    setTab("map");
    setCountry(code);
    top.current?.scrollTo({ top: 0 });
  };
  return (
    <div className="atlas" ref={top}>
      <div className="atlas-inner">
        <header className="atlas-head">
          <div>
            <h1>{t("税务地图")}</h1>
            <p>{t("各辖区的股息税：法定税率、协定税率及其法律依据。")}</p>
          </div>
          <div className="atlas-tabs" role="tablist" aria-label={t("税务地图")}>
            <button role="tab" aria-selected={tab === "map"} onClick={() => { setTab("map"); setCountry(null); }}>
              <MapIcon size={15} />{t("地图")}
            </button>
            <button role="tab" aria-selected={tab === "glossary"} onClick={() => setTab("glossary")}>
              <BookOpen size={15} />{t("税务词典")}
            </button>
          </div>
        </header>
        {tab === "glossary" ? <Glossary onOpen={open} onClause={setClause} /> :
          country ? <CountryPage code={country} onBack={() => setCountry(null)} onOpen={open} onClause={setClause} /> :
            error ? <div className="atlas-error" role="alert">{t(`error:${error}`)} <button onClick={load}>{t("重试")}</button></div> :
              !data ? <BrandLoader label={t("正在载入…")} /> :
                <MapHome data={data} metric={metric} setMetric={setMetric} onOpen={open} />}
      </div>
      {clause && <ClauseDialog citeId={clause} onClose={() => setClause(null)} />}
    </div>
  );
}

function MapHome({ data, metric, setMetric, onOpen }: {
  data: AtlasMap; metric: Metric; setMetric: (m: Metric) => void; onOpen: (code: string) => void;
}) {
  const { t, locale } = useLocale();
  const [focus, setFocus] = useState<string | null>(null);
  const rows = data.jurisdictions;
  const ranked = [...rows].sort((a, b) => (b[metric].ceiling ?? -1) - (a[metric].ceiling ?? -1) || a.name.localeCompare(b.name));
  const values = rows.map((r) => r[metric].ceiling).filter((v): v is number => v !== null);
  const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
  const zero = values.filter((v) => v === 0).length;
  const v = data.version;
  return (
    <>
      <section className="atlas-stats" aria-label={t("概览")}>
        <div><strong>{rows.length}</strong><span>{t("已收录辖区")}</span></div>
        <div><strong>{avg === null ? "—" : `${num(Number(avg.toFixed(2)))}%`}</strong><span>{t("平均股息预提税")} · {t(METRIC_LABEL[metric])} ({values.length}/{rows.length})</span></div>
        <div><strong>{zero}</strong><span>{t("该情形计算为零的辖区")}</span></div>
        <div><strong>{(v.clauses ?? 0).toLocaleString()}</strong><span>{t("法律条文")} · {v.docs} {t("份文件")} · {v.params} {t("个参数")}</span></div>
      </section>
      <section className="atlas-card atlas-map-card">
        <div className="atlas-card-head">
          <div>
            <h2>{t("股息预提税")}</h2>
            <p className="atlas-muted">{t("情形：非上市公司付款，收款方持股 100% 满 24 个月，不适用协定。区间为有利一端至不利一端。")}</p>
          </div>
          <div className="atlas-segment" role="radiogroup" aria-label={t("税种")}>
            {(Object.keys(METRIC_LABEL) as Metric[]).map((m) => (
              <button key={m} role="radio" aria-checked={metric === m} onClick={() => setMetric(m)}>{t(METRIC_LABEL[m])}</button>
            ))}
          </div>
        </div>
        <div className="atlas-map-layout">
          <WorldMap rows={rows} metric={metric} focus={focus} setFocus={setFocus} onOpen={onOpen} />
          <ol className="atlas-ranking" aria-label={t("排名")}>
            {ranked.map((r, i) => {
              const c = r[metric];
              return (
                <li key={r.code}>
                  <button className={focus === r.code ? "is-focus" : ""} onClick={() => onOpen(r.code)}
                    onMouseEnter={() => setFocus(r.code)} onMouseLeave={() => setFocus(null)}
                    onFocus={() => setFocus(r.code)} onBlur={() => setFocus(null)}>
                    <span className="atlas-rank">{i + 1}</span>
                    <span className="atlas-rank-name">{jurName(r, locale)}</span>
                    <span className="atlas-rank-bar"><i style={{ width: `${Math.min(100, ((c.ceiling ?? 0) / 25) * 100)}%`, background: rateColour(c.ceiling) }} /></span>
                    <span className="atlas-rank-value">{rate(c)}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
        <p className="atlas-source">
          {t("税率由规则层按今日计算；法律资料使用已加载的数据库版本")} ({v.source}, {v.library})
        </p>
      </section>
    </>
  );
}

function WorldMap({ rows, metric, focus, setFocus, onOpen }: {
  rows: AtlasJurisdiction[]; metric: Metric; focus: string | null; setFocus: (c: string | null) => void; onOpen: (code: string) => void;
}) {
  const { t, locale } = useLocale();
  const svg = useRef<SVGSVGElement>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const [shapes, setShapes] = useState<Shape[]>([]);
  const [view, setView] = useState<View>(regionView);
  const [tip, setTip] = useState<{ name: string; row?: AtlasJurisdiction; x: number; y: number } | null>(null);
  const drag = useRef<{ x: number; y: number; moved: number } | null>(null);
  const byIso = useMemo(() => new Map(rows.map((r) => [r.iso, r])), [rows]);
  useEffect(() => { void loadWorld().then(setShapes); }, []);
  const local = (cx: number, cy: number): [number, number] => {
    const r = svg.current?.getBoundingClientRect();
    return r ? [((cx - r.left) * W) / r.width, ((cy - r.top) * H) / r.height] : [0, 0];
  };
  useEffect(() => {
    const el = svg.current;
    if (!el) return;
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      const [px, py] = local(e.clientX, e.clientY);
      setView((v) => zoomAt(v, px, py, Math.exp(-e.deltaY * 0.0016)));
    };
    el.addEventListener("wheel", wheel, { passive: false });
    return () => el.removeEventListener("wheel", wheel);
  }, [shapes.length]);
  const down = (e: ReactPointerEvent<SVGSVGElement>) => {
    if (e.button !== 0) return;
    const start = local(e.clientX, e.clientY);
    drag.current = { x: start[0], y: start[1], moved: 0 };
    const move = (ev: PointerEvent) => {
      const d = drag.current;
      if (!d) return;
      const now = local(ev.clientX, ev.clientY);
      d.moved += Math.hypot(now[0] - d.x, now[1] - d.y);
      setView((v) => ({ ...v, x: v.x + now[0] - d.x, y: v.y + now[1] - d.y }));
      d.x = now[0]; d.y = now[1];
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      setTimeout(() => { drag.current = null; }, 0);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };
  const point = (e: ReactPointerEvent, name: string, row?: AtlasJurisdiction) => {
    if (drag.current && drag.current.moved > 2) { setTip(null); return; }
    const r = wrap.current?.getBoundingClientRect();
    if (r) setTip({ name, row, x: e.clientX - r.left, y: e.clientY - r.top });
    setFocus(row?.code ?? null);
  };
  const leave = () => { setTip(null); setFocus(null); };
  const click = (row?: AtlasJurisdiction) => {
    if (row && !(drag.current && drag.current.moved > 4)) onOpen(row.code);
  };
  const zoom = (f: number) => setView((v) => zoomAt(v, W / 2, H / 2, f));
  return (
    <div className="atlas-map" ref={wrap}>
      <svg ref={svg} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t("世界地图：各辖区股息预提税")} onPointerDown={down}
        className={drag.current ? "is-dragging" : ""}>
        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
          <path d={SPHERE} className="atlas-sphere" />
          {shapes.map((s) => {
            const row = byIso.get(s.id);
            const c = row?.[metric];
            return (
              <path key={s.id + s.d.length} d={s.d} vectorEffect="non-scaling-stroke"
                className={`atlas-country ${row ? "is-lib" : ""} ${row && focus === row.code ? "is-focus" : ""}`}
                style={row ? { fill: rateColour(c?.ceiling ?? null) } : undefined}
                onPointerMove={(e) => point(e, row ? jurName(row, locale) : s.name, row)} onPointerLeave={leave}
                onClick={() => click(row)} />
            );
          })}
          {rows.map((r) => {
            const a = anchor(r.code);
            if (!a) return null;
            const k = view.k;
            return (
              <g key={r.code} className={`atlas-marker ${focus === r.code ? "is-focus" : ""}`} onClick={() => click(r)}
                onPointerMove={(e) => point(e, jurName(r, locale), r)} onPointerLeave={leave}>
                <circle cx={a[0]} cy={a[1]} r={(focus === r.code ? 6.5 : 5) / k} fill={rateColour(r[metric].ceiling)} strokeWidth={1.6 / k} />
                {k > 1.6 && <text x={a[0] + 8 / k} y={a[1] + 3.5 / k} fontSize={11 / k} strokeWidth={3 / k}>{jurName(r, locale)} {rate(r[metric])}</text>}
              </g>
            );
          })}
        </g>
      </svg>
      {tip && (
        <div className="atlas-tip" style={{ left: tip.x + 14, top: tip.y + 14 }}>
          <strong>{tip.name}</strong>
          {tip.row ? <>
            <span className="atlas-tip-rate">{rate(tip.row[metric])}</span>
            <span>{t(METRIC_LABEL[metric])}</span>
            {tip.row[metric].absent?.map((a) => <span className="atlas-muted" key={a.id}>{a.statement}</span>)}
            {tip.row[metric].needs.length > 0 && <span className="atlas-muted">{t("取决于")}: {tip.row[metric].needs.join(", ")}</span>}
            <em>{t("点击查看详情")}</em>
          </> : <span className="atlas-muted">{t("尚未收录")}</span>}
        </div>
      )}
      <div className="atlas-map-controls">
        <HintButton aria-label={t("放大")} onClick={() => zoom(1.5)}><Plus size={16} /></HintButton>
        <HintButton aria-label={t("缩小")} onClick={() => zoom(1 / 1.5)}><Minus size={16} /></HintButton>
        <HintButton aria-label={t("亚洲视图")} onClick={() => setView(regionView())}><LocateFixed size={16} /></HintButton>
        <HintButton aria-label={t("世界视图")} onClick={() => setView(WORLD)}><Earth size={16} /></HintButton>
      </div>
      <div className="atlas-legend" aria-hidden="true">
        <span className="atlas-legend-ramp" style={{ background: `linear-gradient(90deg, ${RAMP.map(([v, c]) => `${c} ${(v / 25) * 100}%`).join(", ")})` }} />
        <span className="atlas-legend-ticks">{RAMP.map(([v]) => <i key={v}>{v}%{v === 25 ? "+" : ""}</i>)}</span>
        <span className="atlas-legend-na"><i />{t("未收录或税率未知")}</span>
      </div>
    </div>
  );
}
