import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { createPortal } from "react-dom";
import { Building2, ChevronDown, ChevronUp, Crown, Maximize2, Minus, Pause, Play, Plus, RotateCcw, User, X } from "lucide-react";
import { api, ApiError } from "../api";
import { useLocale } from "../locale";
import { useOverlayFocus } from "../hooks/useOverlayFocus";
import type { SearchCandidate, SearchState } from "../workspace";
import { ICON, ISO, MAP_H, MAP_W, loadCountries, places, type Country } from "./worldMap";

// Replays optimization/tools/optimize.py labels() (§4.3): a Pareto label-setting search from the paying company. Each
// expansion takes the cheapest open label and tries every edge out of its node; a new label is kept unless a label
// already at that node is at least as good on every criterion, and a kept label removes the ones it beats. Where a
// prior-dependent edge is still within reach only equal labels prune, a node over the cap cuts its costliest labels,
// and the destinations' labels are filtered once more by plain dominance into the frontier (§4.2).
const JUR: Record<string, string> = {
  cn: "中国内地", hk: "香港", sg: "新加坡", jp: "日本", th: "泰国", ae: "阿联酋", id: "印度尼西亚", in: "印度", kr: "韩国", my: "马来西亚", vn: "越南",
};
const SUBJECT: Record<string, string> = { company: "公司", individual: "个人" };
const ROUTE_COLORS = ["#2f7d64", "#c27c2c", "#5161a8", "#9a4f8b", "#3d8fa6"];
const K_MIN = 0.3, K_MAX = 6;                // zoom range around the first view (the capitals of the library)
type View = { k: number; x: number; y: number };
const HOME: View = { k: 1, x: 0, y: 0 };

function zoomAt(v: View, px: number, py: number, factor: number): View {
  const k = Math.min(K_MAX, Math.max(K_MIN, v.k * factor)), r = k / v.k;
  return { k, x: px - (px - v.x) * r, y: py - (py - v.y) * r };
}

type Frame = {
  label: string; node: string; tax: number; kept: [string, string, string, number][]; pruned: Map<string, number>; replaced: string[]; cut: [string, string][];
};

function moveText(move: string, t: (s: string) => string) {
  const m = move.match(/^(\w+)\((.*)\)$/);
  if (!m) return t(move);
  if (m[1] === "remit" && m[2] === "false") return t("不汇入收款地");
  if (m[1] === "wait_months") return `${t("持满")} ${m[2]} ${t("个月再分红")}`;
  if (m[1] === "holding_pct") return `${t("持股")} ${m[2]}%`;
  return move;
}

// a hop between two icons on the map: bowed to one side, so a->b and b->a do not lie on each other, and stopped short of
// the target's icon so the arrow head stays visible
function curve(a: [number, number], b: [number, number], bend = 0.2) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const qx = (a[0] + b[0]) / 2 - dy * bend, qy = (a[1] + b[1]) / 2 + dx * bend;
  const len = Math.hypot(b[0] - qx, b[1] - qy) || 1;
  const cut = Math.min(ICON * 0.62, len * 0.45);
  return `M${a[0]} ${a[1]} Q${qx} ${qy} ${b[0] - ((b[0] - qx) / len) * cut} ${b[1] - ((b[1] - qy) / len) * cut}`;
}

function frames(data: SearchState) {
  const node: Record<string, string> = { L0: data.source ?? "" };
  const tax: Record<string, number> = { L0: 0 };
  const held: Record<string, number> = { [data.source ?? ""]: 1 };   // labels per node: right after a cut the node is back at the cap
  let cap = 0;
  const out: Frame[] = [];
  const blank = (label: string, at: string, w: number): Frame => ({ label, node: at, tax: w, kept: [], pruned: new Map(), replaced: [], cut: [] });
  for (const e of data.events ?? []) {
    const [kind, label] = e as [string, string];
    if (kind === "pop") {
      out.push(blank(label, node[label] ?? "", tax[label] ?? 0));
      continue;
    }
    const f = out.at(-1) ?? (out.push(blank("L0", data.source ?? "", 0)), out[0]);
    if (kind === "label") {
      const [, , from, , head, w] = e as [string, string, string, string, string, number];
      node[label] = head;
      tax[label] = w;
      held[head] = (held[head] ?? 0) + 1;
      f.kept.push([label, node[from] ?? "", head, w]);
    } else if (kind === "dominated") {
      const key = `${node[e[2] as string] ?? ""}>${e[4]}`;
      f.pruned.set(key, (f.pruned.get(key) ?? 0) + 1);
    } else if (kind === "replaced") {
      held[node[label]] = (held[node[label]] ?? 0) - 1;
      f.replaced.push(label);
    } else if (kind === "cut") {
      held[node[label]] = (held[node[label]] ?? 0) - 1;
      cap = held[node[label]];
      f.cut.push([label, node[label] ?? ""]);
    }
  }
  return { steps: out, cap };
}

export default function SearchView({ caseId, running, onClose }: { caseId: string; running: boolean; onClose: () => void }) {
  const { t, locale } = useLocale();
  const ref = useRef<HTMLDivElement>(null);
  useOverlayFocus(ref, true, true, onClose);
  const [data, setData] = useState<SearchState | null>(null);
  const [failed, setFailed] = useState("");
  useEffect(() => {
    let stop = false, timer = 0;
    const load = () => api.search(caseId).then((next) => {
      if (stop) return;
      setData(next);
      if (!next.ready) timer = window.setTimeout(load, 3000);
    }).catch((error) => !stop && setFailed(error instanceof ApiError ? error.code : "network_error"));
    load();
    return () => { stop = true; clearTimeout(timer); };
  }, [caseId]);

  const replay = useMemo(() => (data?.ready ? frames(data) : { steps: [], cap: 0 }), [data]);
  const search = replay.steps;
  const cands = useMemo(() => {
    const all = data?.candidates ?? [];
    const same = (a: SearchCandidate, b: SearchCandidate) => a.path.join() === b.path.join() && a.moves.join() === b.moves.join();
    return all.filter((c) => !c.requested || !all.some((o) => !o.requested && same(o, c)));   // a requested structure the search found too
  }, [data]);
  const total = search.length + cands.length + 1;
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  useEffect(() => {
    if (!playing || !data?.ready || step >= total - 1) return;
    const wait = (step < search.length ? 700 : 1500) / speed;
    const timer = window.setTimeout(() => setStep((s) => Math.min(total - 1, s + 1)), wait);
    return () => clearTimeout(timer);
  }, [playing, step, speed, total, search.length, data?.ready]);

  const nodes = useMemo(() => data?.nodes ?? [], [data]);
  const jurs = useMemo(() => [...new Set(nodes.map((n) => n.split(":")[0]))], [nodes]);
  const place = useMemo(() => places(jurs), [jurs]);
  const pos = (n: string): [number, number] => {
    const [j, s] = n.split(":");
    const p = place[j];
    return !p ? [0, 0] : s === "company" ? p.company : p.person;
  };
  const name = (n: string) => { const [j, s] = n.split(":"); return `${t(JUR[j] ?? j.toUpperCase())}${locale === "en" ? " " : ""}${t(SUBJECT[s] ?? s)}`; };

  // the world map: loaded once, drawn once; zoom and pan move one group, so everything on it stays where it belongs
  const [countries, setCountries] = useState<Country[]>([]);
  useEffect(() => {
    let stop = false;
    loadCountries().then((c) => !stop && setCountries(c)).catch(() => undefined);   // without the map the icons still show
    return () => { stop = true; };
  }, []);
  const svgRef = useRef<SVGSVGElement>(null);
  const [view, setView] = useState<View>(HOME);
  const pointers = useRef(new Map<number, [number, number]>());
  const [panning, setPanning] = useState(false);
  const local = (clientX: number, clientY: number): [number, number] => {
    const r = svgRef.current?.getBoundingClientRect();
    return r ? [((clientX - r.left) * MAP_W) / r.width, ((clientY - r.top) * MAP_H) / r.height] : [0, 0];
  };
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const wheel = (e: WheelEvent) => {             // not passive, so the dialog does not scroll while the map zooms
      e.preventDefault();
      const r = svg.getBoundingClientRect();
      const px = ((e.clientX - r.left) * MAP_W) / r.width, py = ((e.clientY - r.top) * MAP_H) / r.height;
      setView((v) => zoomAt(v, px, py, Math.exp(-e.deltaY * 0.0015)));
    };
    svg.addEventListener("wheel", wheel, { passive: false });
    return () => svg.removeEventListener("wheel", wheel);
  }, [data?.ready]);
  const down = (e: ReactPointerEvent<SVGSVGElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    pointers.current.set(e.pointerId, local(e.clientX, e.clientY));
    setPanning(true);
  };
  const move = (e: ReactPointerEvent<SVGSVGElement>) => {
    const was = pointers.current.get(e.pointerId);
    if (!was) return;
    const now = local(e.clientX, e.clientY);
    const other = [...pointers.current.entries()].find(([id]) => id !== e.pointerId)?.[1];
    if (other) {                                    // two fingers: the change in their distance zooms about their middle
      const before = Math.hypot(was[0] - other[0], was[1] - other[1]) || 1;
      const after = Math.hypot(now[0] - other[0], now[1] - other[1]) || 1;
      setView((v) => zoomAt(v, (now[0] + other[0]) / 2, (now[1] + other[1]) / 2, after / before));
    } else {
      setView((v) => ({ ...v, x: v.x + now[0] - was[0], y: v.y + now[1] - was[1] }));
    }
    pointers.current.set(e.pointerId, now);
  };
  const up = (e: ReactPointerEvent<SVGSVGElement>) => {
    pointers.current.delete(e.pointerId);
    if (!pointers.current.size) setPanning(false);
  };
  const zoomBy = (factor: number) => setView((v) => zoomAt(v, MAP_W / 2, MAP_H / 2, factor));
  const libIds = useMemo(() => new Set(jurs.map((j) => ISO[j]).filter(Boolean)), [jurs]);
  const shapeOf = useMemo(() => new Map(countries.map((c) => [c.id, c.d])), [countries]);
  const land = useMemo(() => countries.map((c, i) => (
    <path key={i} d={c.d} className={`sv-land ${libIds.has(c.id) ? "lib" : ""}`} />
  )), [countries, libIds]);

  // the state after `step`: labels alive per node, the edges they use, the totals
  const shown = Math.min(step + 1, search.length);
  const alive = new Map<string, [string, string, number]>();
  let pruned = 0, replaced = 0, cut = 0;
  const cutAt = new Set<string>();
  for (const f of search.slice(0, shown)) {
    for (const [label, tail, head, w] of f.kept) alive.set(label, [tail, head, w]);
    for (const label of f.replaced) { alive.delete(label); replaced += 1; }
    for (const [label, at] of f.cut) { alive.delete(label); cutAt.add(at); cut += 1; }
    for (const n of f.pruned.values()) pruned += n;
  }
  const atDest = [...alive.values()].filter(([, head]) => (data?.destinations ?? []).includes(head)).length;
  const liveEdges = new Map<string, number>();
  const perNode = new Map<string, number>();
  for (const [tail, head] of alive.values()) {
    liveEdges.set(`${tail}>${head}`, (liveEdges.get(`${tail}>${head}`) ?? 0) + 1);
    perNode.set(head, (perNode.get(head) ?? 0) + 1);
  }
  const frame = step < search.length ? search[step] : null;
  const candStep = step - search.length;                    // 0.. while candidates are traced, cands.length at the ranking
  const phase = frame ? "search" : candStep < cands.length ? "candidates" : "ranking";
  // the countries the search has expanded from so far (they stay tinted), and those this step touches (they light up once)
  const jurOf = (n: string) => n.split(":")[0];
  const visited = new Set<string>(data?.source ? [jurOf(data.source)] : []);
  for (const f of search.slice(0, shown)) visited.add(jurOf(f.node));
  const touched = new Set<string>();
  if (frame) {
    touched.add(jurOf(frame.node));
    for (const [, , head] of frame.kept) touched.add(jurOf(head));
  } else if (phase === "candidates") {
    for (const n of cands[candStep]?.path ?? []) touched.add(jurOf(n));
  }

  // the candidate list: a small scrolling window unless opened; a candidate clicked is highlighted on the map
  const [listOpen, setListOpen] = useState(false);
  const [picked, setPicked] = useState<string | null>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const pickedCand = picked ? cands.find((c) => c.cand_id === picked) : undefined;
  if (pickedCand) {
    touched.clear();
    for (const n of pickedCand.path) touched.add(jurOf(n));
  }
  const pick = (id: string) => { setPicked((p) => (p === id ? null : id)); setPlaying(false); };
  useEffect(() => { if (phase === "search") setPicked(null); }, [phase]);
  useEffect(() => {                                 // follow the newest candidate, then the first of the ranking
    const el = listRef.current;
    if (!el || listOpen || picked) return;
    el.scrollTo({ top: phase === "ranking" ? 0 : el.scrollHeight, behavior: "smooth" });
  }, [phase, candStep, listOpen, picked]);

  const best = new Map<string, { rank: number | null; per_100: number | null; amount: number | null }>();
  for (const r of data?.ranking ?? []) {
    const had = best.get(r.cand_id);
    if (r.rank != null && (!had || had.rank == null || r.rank < had.rank)) best.set(r.cand_id, r);
    else if (!had) best.set(r.cand_id, r);
  }
  const color = (c: SearchCandidate) => ROUTE_COLORS[cands.indexOf(c) % ROUTE_COLORS.length];
  const tracedCands = cands.slice(0, phase === "candidates" ? candStep + 1 : phase === "ranking" ? cands.length : 0);
  // the route in focus: the one clicked, else at the ranking the first; drawn last so it lies on top
  const focus = picked ?? (phase === "ranking" ? data?.best ?? null : null);
  const drawn = pickedCand && !tracedCands.includes(pickedCand) ? [...tracedCands, pickedCand] : tracedCands;
  const routes = [...drawn.filter((c) => c.cand_id !== focus), ...drawn.filter((c) => c.cand_id === focus)];
  const money = (v: number | null | undefined) => (v == null ? "—" : `${data?.currency ?? ""} ${Math.round(v).toLocaleString("en-US")}`);
  const expanded = Math.min(shown, search.length);

  const body = !data ? (
    <p className="sv-wait">{failed === "Not Found" ? t("这个服务还是旧版本，没有搜索记录的接口：重启服务后再打开。") : failed ? t("读取搜索记录失败。") : t("正在读取搜索记录…")}</p>
  ) : !data.ready ? (
    <p className="sv-wait">{running ? t("优化程序正在搜索，完成后在这里回放。") : t("这一轮还没有搜索结果。")}</p>
  ) : (
    <div className="sv-body">
      <div className="sv-mapbox">
        <svg ref={svgRef} className={`sv-map ${panning ? "panning" : ""}`} viewBox={`0 0 ${MAP_W} ${MAP_H}`} role="img" aria-label={t("搜索路线图")}
          onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}
          onDoubleClick={(e) => { const [px, py] = local(e.clientX, e.clientY); setView((v) => zoomAt(v, px, py, 2)); }}>
          <defs>
            <marker id="sv-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto">
              <path d="M0 0 L8 4 L0 8 z" fill="#2f7d64" />
            </marker>
          </defs>
          <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
            {land}
            {jurs.map((j) => shapeOf.get(ISO[j]) && visited.has(j) && <path key={`v-${j}`} d={shapeOf.get(ISO[j])} className="sv-land visited" />)}
            {jurs.map((j) => touched.has(j) && shapeOf.get(ISO[j]) && (
              <path key={`f-${step}-${picked}-${j}`} d={shapeOf.get(ISO[j])} className="sv-flashland" />
            ))}
            {jurs.map((j) => touched.has(j) && place[j] && (
              <circle key={`h-${step}-${picked}-${j}`} className="sv-halo" cx={place[j].anchor[0]} cy={place[j].anchor[1]} r={8} />
            ))}
            {jurs.map((j) => place[j]?.moved && (
              <g key={`a-${j}`}>
                <line className="sv-leader" x1={place[j].anchor[0]} y1={place[j].anchor[1]} x2={place[j].company[0]} y2={place[j].company[1]} />
                <circle className="sv-anchor" cx={place[j].anchor[0]} cy={place[j].anchor[1]} r={1.4} />
              </g>
            ))}
            {[...liveEdges.keys()].map((key) => {
              const [a, b] = key.split(">");
              return (
                <path key={key} className={`sv-edge ${tracedCands.length > 0 ? "quiet" : ""}`} d={curve(pos(a), pos(b))} markerEnd="url(#sv-arrow)" />
              );
            })}
            {frame && [...frame.pruned.entries()].map(([key, n]) => {
              const [a, b] = key.split(">");
              return <path key={`${step}-${key}`} className="sv-pruned" d={curve(pos(a), pos(b), 0.12)} data-n={n} />;
            })}
            {frame && frame.kept.map(([label, a, b]) => (
              <path key={`${step}-${label}`} className="sv-new" d={curve(pos(a), pos(b))} pathLength={1} />
            ))}
            {routes.map((c) => {
              const i = cands.indexOf(c), on = c.cand_id === focus;
              return c.path.slice(1).map((n, k) => (           // bends cycle through five sizes, so many routes stay apart without loops
                <path key={`${c.cand_id}-${k}${on && picked ? "-picked" : ""}`} d={curve(pos(c.path[k]), pos(n), 0.08 + (i % 5) * 0.05)} pathLength={1}
                  className={`sv-route ${on ? (picked ? "picked" : "best") : focus ? "dim" : ""}`} style={{ stroke: color(c) }} />
              ));
            })}
            {jurs.map((j) => {
              const p = place[j];
              if (!p) return null;
              const mine = nodes.filter((n) => jurOf(n) === j);
              const role = [mine.includes(data.source ?? "") && "付款方", mine.some((n) => data.destinations?.includes(n)) && "目的地"].filter(Boolean) as string[];
              const cx = (p.company[0] + p.person[0]) / 2;
              return (
                <g key={`l-${j}`}>
                  <text className="sv-name" x={cx} y={p.company[1] + ICON * 0.95} textAnchor="middle">{t(JUR[j] ?? j.toUpperCase())}</text>
                  {role.length > 0 && (                     /* under the name: a tag above would sit on the label of a group above */
                    <text className={`sv-tag ${role[0] === "付款方" ? "source" : ""}`} x={cx} y={p.company[1] + ICON * 1.4} textAnchor="middle">
                      {role.map((r) => t(r)).join(" · ")}
                    </text>
                  )}
                </g>
              );
            })}
            {nodes.map((n) => {
              const [x, y] = pos(n);
              const person = !n.endsWith(":company");
              const Icon = person ? User : Building2;
              const kind = n === data.source ? "source" : data.destinations?.includes(n) ? "dest" : "";
              const count = perNode.get(n) ?? 0;
              const r = ICON / 2;
              return (
                <g key={n} transform={`translate(${x} ${y})`}
                  className={`sv-node ${kind} ${frame?.node === n ? "active" : ""} ${count ? "reached" : ""} ${cutAt.has(n) ? "cut" : ""}`}>
                  <title>{name(n)}</title>
                  {frame?.node === n && <circle key={step} className="sv-pulse" r={r} />}
                  <circle className="sv-shape" r={r} />
                  <Icon className="sv-icon" x={-r * 0.62} y={-r * 0.62} width={r * 1.24} height={r * 1.24} strokeWidth={2.2} aria-hidden />
                  {count > 0 && (
                    <g className="sv-badge">
                      <circle cx={r * 0.85} cy={-r * 0.85} r={4.6} />
                      <text x={r * 0.85} y={-r * 0.85 + 2.1} textAnchor="middle">{count}</text>
                    </g>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
        <div className="sv-zoom">
          <button type="button" onClick={() => zoomBy(1.6)} aria-label={t("放大")} title={t("放大")}><Plus size={15} /></button>
          <button type="button" onClick={() => zoomBy(1 / 1.6)} aria-label={t("缩小")} title={t("缩小")}><Minus size={15} /></button>
          <button type="button" onClick={() => setView(HOME)} aria-label={t("复位视图")} title={t("复位视图")}><Maximize2 size={14} /></button>
        </div>
        <div className="sv-legend">
          <span><Building2 size={13} />{t("公司")}</span>
          <span><User size={13} />{t("个人")}</span>
          <span><i className="src" />{t("付款方")}</span>
          <span><i className="dst" />{t("目的地")}</span>
          <small>{t("滚轮或双指缩放，拖动平移")}</small>
        </div>
      </div>

      <aside className="sv-side">
        <ol className="sv-phases">
          {(["search", "candidates", "ranking"] as const).map((p, i) => (
            <li key={p} className={p === phase ? "on" : ["search", "candidates", "ranking"].indexOf(phase) > i ? "done" : ""}>
              <span>{i + 1}</span>{t(p === "search" ? "标签搜索" : p === "candidates" ? "候选结构" : "计税排序")}
            </li>
          ))}
        </ol>
        <div className="sv-stats">
          <div><strong>{(data.edge_count ?? 0).toLocaleString("en-US")}</strong><span>{t("搜索空间（边）")}</span></div>
          <div><strong>{expanded}/{search.length}</strong><span>{t("已展开")}</span></div>
          <div><strong>{alive.size}</strong><span>{t("保留的路径")}</span></div>
          <div><strong>{pruned.toLocaleString("en-US")}</strong><span>{t("被占优剪除")}</span></div>
        </div>
        {phase === "search" && frame && (
          <div className="sv-now">
            <p><b>{t("展开")}</b> {name(frame.node)}<em>{t("累计税负")} {frame.tax.toFixed(2)}%</em></p>
            <p>
              {t("新增")} {frame.kept.length} · {t("剪除")} {[...frame.pruned.values()].reduce((a, b) => a + b, 0)} · {t("替换")} {frame.replaced.length}
              {frame.cut.length > 0 && <> · {t("截断")} {frame.cut.length}</>}
            </p>
            <small>{t("每一步取累计税负最低的未展开路径，沿所有出边各走一跳；到达同一节点时，税负、未决判断、跳数和重组都不更差的路径把另一条剪掉。后面还可能经过间接抵免边的节点例外：前面缴税多的路径在那里抵免也多，总税负可能反而更低，所以只剪完全相同的路径。")}</small>
          </div>
        )}
        {phase !== "search" && (
          <div className={`sv-cands-box ${listOpen ? "open" : ""}`}>
            <div className="sv-cands-head">
              <span>{phase === "candidates" ? `${t("候选结构")} ${tracedCands.length}/${cands.length}` : `${t("计税排序")} · ${cands.length}`}</span>
              {picked
                ? <button type="button" onClick={() => setPicked(null)}>{t("取消高亮")}</button>
                : <small>{t("点选一条，在地图上高亮它的路线")}</small>}
            </div>
            <ul ref={listRef} className="sv-cands">
              {(phase === "ranking" ? [...tracedCands].sort((a, b) => (best.get(a.cand_id)?.rank ?? 99) - (best.get(b.cand_id)?.rank ?? 99)) : tracedCands).map((c) => {
                const r = best.get(c.cand_id);
                const win = phase === "ranking" && c.cand_id === data.best;
                return (
                  <li key={c.cand_id} className={`${win ? "win" : ""} ${picked === c.cand_id ? "picked" : ""}`} style={{ borderLeftColor: color(c) }}
                    role="button" tabIndex={0} aria-pressed={picked === c.cand_id} onClick={() => pick(c.cand_id)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(c.cand_id); } }}>
                    <div className="sv-route-line">{win && <Crown size={14} />}{c.path.map(name).join(" → ")}</div>
                    <div className="sv-chips">
                      {c.as_is && <code>{t("现状")}</code>}
                      {c.restructure.map((m) => <code key={m}>{t(m === "transfer" ? "股权转让" : m)}</code>)}
                      {c.moves.map((m) => <code key={m}>{moveText(m, t)}</code>)}
                      <code>{t("分支")} ×{data.branches?.[c.cand_id] ?? 0}</code>
                    </div>
                    {phase === "ranking" && (
                      <div className="sv-tax">
                        {r?.rank != null ? <><b>{t("排名")} {r.rank}</b> {r.per_100?.toFixed(2)}% · {money(r.amount)}</> : <span>{t("未排名（路径未到目的地或事实不全）")}</span>}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
            <button type="button" className="sv-cands-toggle" onClick={() => setListOpen(!listOpen)} aria-expanded={listOpen}
              aria-label={t(listOpen ? "收起" : "展开全部")} title={t(listOpen ? "收起" : "展开全部")}>
              {listOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>
        )}
        {phase === "candidates" && (
          <small className="sv-note">
            {data.frontier
              ? t("目的地上有 {x} 条路径，按普通占优再筛一次，留下 {y} 条；每条还原成一个候选结构，每个未决判断点按有利、不利分叉，逐跳计税。")
                  .replace("{x}", String(atDest)).replace("{y}", String(data.frontier.length))
              : t("目的地上留下的每条路径还原成一个候选结构；每个未决判断点按有利、不利分叉，逐跳计税。")}
          </small>
        )}
        {phase === "ranking" && <small className="sv-note">{t("按每笔股息的税额排序，税额相同时比回本次数；下面是各结构在有利假设下的最好分支。")}</small>}
        {cut > 0 && (
          <small className="sv-note sv-cut">
            {t("{nodes} 超过每个节点 {cap} 条的上限，砍掉了累计税负最高的 {n} 条路径，前沿可能不全。")
              .replace("{nodes}", [...cutAt].map(name).join(locale === "en" ? ", " : "、"))
              .replace("{cap}", String(replay.cap)).replace("{n}", String(cut))}
          </small>
        )}
        {data.approximate && <small className="sv-note">{t("这一轮早于搜索记录：只回放保留下来的路径，不含被剪除的。")}</small>}
      </aside>
    </div>
  );

  return createPortal(
    <div className="sv-backdrop" onClick={onClose}>
      <div className="sv-dialog" ref={ref} role="dialog" aria-modal="true" aria-label={t("优化搜索过程")} onClick={(e) => e.stopPropagation()}>
        <header className="sv-head">
          <div>
            <h2>{t("优化搜索过程")}</h2>
            <p>{t("多目标标签搜索（Pareto）：从付款公司出发逐跳展开所有持股路径，被占优的路径剪掉")}</p>
          </div>
          <button type="button" className="icon-button" aria-label={t("关闭")} onClick={onClose}><X size={18} /></button>
        </header>
        {body}
        {data?.ready && (
          <footer className="sv-controls">
            <button type="button" onClick={() => { if (step >= total - 1) setStep(0); setPlaying(!playing); }} aria-label={t(playing ? "暂停" : "播放")}>
              {playing ? <Pause size={15} /> : <Play size={15} />}
            </button>
            <button type="button" onClick={() => { setStep(0); setPlaying(true); }} aria-label={t("重新播放")}><RotateCcw size={15} /></button>
            <input type="range" min={0} max={total - 1} value={step} aria-label={t("进度")}
              onChange={(e) => { setStep(Number(e.target.value)); setPlaying(false); }} />
            <div className="sv-speed" role="group" aria-label={t("速度")}>
              {[1, 2, 4].map((s) => (
                <button key={s} type="button" className={speed === s ? "on" : ""} onClick={() => setSpeed(s)}>{s}×</button>
              ))}
            </div>
          </footer>
        )}
      </div>
    </div>,
    document.body,
  );
}
