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
  cn: "Mainland China", hk: "Hong Kong", sg: "Singapore", jp: "Japan", th: "Thailand", ae: "UAE", id: "Indonesia", in: "India", kr: "Korea", my: "Malaysia", vn: "Vietnam",
};
const SUBJECT: Record<string, string> = { company: "company", individual: "individual" };
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
  if (m[1] === "remit" && m[2] === "false") return t("not remitted");
  if (m[1] === "wait_months") return t("hold {n} months before paying").replace("{n}", m[2]);
  if (m[1] === "holding_pct") return t("hold {n}%").replace("{n}", m[2]);
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
  const { t } = useLocale();
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
  const name = (n: string) => { const [j, s] = n.split(":"); return t("{jurisdiction} {subject}").replace("{jurisdiction}", t(JUR[j] ?? j.toUpperCase())).replace("{subject}", t(SUBJECT[s] ?? s)); };

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
    <p className="sv-wait">{failed === "Not Found" ? t("This server is an older version without the search endpoint: restart it, then open this again.") : failed ? t("Could not load the search record.") : t("Loading the search record…")}</p>
  ) : !data.ready ? (
    <p className="sv-wait">{running ? t("The optimizer is searching; the replay appears here when it finishes.") : t("This round has no search yet.")}</p>
  ) : (
    <div className="sv-body">
      <div className="sv-mapbox">
        <svg ref={svgRef} className={`sv-map ${panning ? "panning" : ""}`} viewBox={`0 0 ${MAP_W} ${MAP_H}`} role="img" aria-label={t("Search map")}
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
              const role = [mine.includes(data.source ?? "") && "payer", mine.some((n) => data.destinations?.includes(n)) && "destination"].filter(Boolean) as string[];
              const cx = (p.company[0] + p.person[0]) / 2;
              return (
                <g key={`l-${j}`}>
                  <text className="sv-name" x={cx} y={p.company[1] + ICON * 0.95} textAnchor="middle">{t(JUR[j] ?? j.toUpperCase())}</text>
                  {role.length > 0 && (                     /* under the name: a tag above would sit on the label of a group above */
                    <text className={`sv-tag ${role[0] === "payer" ? "source" : ""}`} x={cx} y={p.company[1] + ICON * 1.4} textAnchor="middle">
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
          <button type="button" onClick={() => zoomBy(1.6)} aria-label={t("Zoom in")} title={t("Zoom in")}><Plus size={15} /></button>
          <button type="button" onClick={() => zoomBy(1 / 1.6)} aria-label={t("Zoom out")} title={t("Zoom out")}><Minus size={15} /></button>
          <button type="button" onClick={() => setView(HOME)} aria-label={t("Reset view")} title={t("Reset view")}><Maximize2 size={14} /></button>
        </div>
        <div className="sv-legend">
          <span><Building2 size={13} />{t("company")}</span>
          <span><User size={13} />{t("individual")}</span>
          <span><i className="src" />{t("payer")}</span>
          <span><i className="dst" />{t("destination")}</span>
          <small>{t("Scroll or pinch to zoom, drag to pan")}</small>
        </div>
      </div>

      <aside className="sv-side">
        <ol className="sv-phases">
          {(["search", "candidates", "ranking"] as const).map((p, i) => (
            <li key={p} className={p === phase ? "on" : ["search", "candidates", "ranking"].indexOf(phase) > i ? "done" : ""}>
              <span>{i + 1}</span>{t(p === "search" ? "Label search" : p === "candidates" ? "Candidates" : "Tax & rank")}
            </li>
          ))}
        </ol>
        <div className="sv-stats">
          <div><strong>{(data.edge_count ?? 0).toLocaleString("en-US")}</strong><span>{t("search space (edges)")}</span></div>
          <div><strong>{expanded}/{search.length}</strong><span>{t("expanded")}</span></div>
          <div><strong>{alive.size}</strong><span>{t("routes kept")}</span></div>
          <div><strong>{pruned.toLocaleString("en-US")}</strong><span>{t("pruned as dominated")}</span></div>
        </div>
        {phase === "search" && frame && (
          <div className="sv-now">
            <p><b>{t("Expanding")}</b> {name(frame.node)}<em>{t("tax so far")} {frame.tax.toFixed(2)}%</em></p>
            <p>
              {t("kept")} {frame.kept.length} · {t("pruned")} {[...frame.pruned.values()].reduce((a, b) => a + b, 0)} · {t("replaced")} {frame.replaced.length}
              {frame.cut.length > 0 && <> · {t("cut")} {frame.cut.length}</>}
            </p>
            <small>{t("Each step takes the open route with the lowest tax so far and follows every edge out of it; where two routes reach the same node, one that is no worse on tax, open judgments, hops and restructuring prunes the other. Nodes that can still reach an underlying-credit edge are the exception: a route that paid more earlier gets more credit there and may end lower, so only identical routes are pruned.")}</small>
          </div>
        )}
        {phase !== "search" && (
          <div className={`sv-cands-box ${listOpen ? "open" : ""}`}>
            <div className="sv-cands-head">
              <span>{phase === "candidates" ? `${t("Candidates")} ${tracedCands.length}/${cands.length}` : `${t("Tax & rank")} · ${cands.length}`}</span>
              {picked
                ? <button type="button" onClick={() => setPicked(null)}>{t("Clear highlight")}</button>
                : <small>{t("Click one to highlight its route on the map")}</small>}
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
                      {c.as_is && <code>{t("as is")}</code>}
                      {c.restructure.map((m) => <code key={m}>{t(m === "transfer" ? "share transfer" : m)}</code>)}
                      {c.moves.map((m) => <code key={m}>{moveText(m, t)}</code>)}
                      <code>{t("branches")} ×{data.branches?.[c.cand_id] ?? 0}</code>
                    </div>
                    {phase === "ranking" && (
                      <div className="sv-tax">
                        {r?.rank != null ? <><b>{t("Rank")} {r.rank}</b> {r.per_100?.toFixed(2)}% · {money(r.amount)}</> : <span>{t("not ranked (route stops short or facts incomplete)")}</span>}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
            <button type="button" className="sv-cands-toggle" onClick={() => setListOpen(!listOpen)} aria-expanded={listOpen}
              aria-label={t(listOpen ? "Collapse" : "Show all")} title={t(listOpen ? "Collapse" : "Show all")}>
              {listOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>
        )}
        {phase === "candidates" && (
          <small className="sv-note">
            {data.frontier
              ? t("{x} routes reach the destination; filtered once more by plain dominance, {y} remain. Each becomes a candidate structure; every open judgment forks into favourable and unfavourable branches, taxed hop by hop.")
                  .replace("{x}", String(atDest)).replace("{y}", String(data.frontier.length))
              : t("Each route left at the destination becomes a candidate structure; every open judgment forks into favourable and unfavourable branches, taxed hop by hop.")}
          </small>
        )}
        {phase === "ranking" && <small className="sv-note">{t("Ranked by the tax on each dividend, then by payback; shown is each structure's best branch under the favourable answers.")}</small>}
        {cut > 0 && (
          <small className="sv-note sv-cut">
            {t("{nodes}: over the limit of {cap} routes per node, so the {n} with the highest tax so far were cut; the frontier may be incomplete.")
              .replace("{nodes}", [...cutAt].map(name).join(t(", ")))
              .replace("{cap}", String(replay.cap)).replace("{n}", String(cut))}
          </small>
        )}
        {data.approximate && <small className="sv-note">{t("This round predates the search record: only the routes kept are replayed, not the pruned ones.")}</small>}
      </aside>
    </div>
  );

  return createPortal(
    <div className="sv-backdrop" onClick={onClose}>
      <div className="sv-dialog" ref={ref} role="dialog" aria-modal="true" aria-label={t("Optimizer search")} onClick={(e) => e.stopPropagation()}>
        <header className="sv-head">
          <div>
            <h2>{t("Optimizer search")}</h2>
            <p>{t("Multi-criteria label-setting search (Pareto): from the paying company, every holding route is expanded hop by hop and dominated routes are pruned")}</p>
          </div>
          <button type="button" className="icon-button" aria-label={t("Close")} onClick={onClose}><X size={18} /></button>
        </header>
        {body}
        {data?.ready && (
          <footer className="sv-controls">
            <button type="button" onClick={() => { if (step >= total - 1) setStep(0); setPlaying(!playing); }} aria-label={t(playing ? "Pause" : "Play")}>
              {playing ? <Pause size={15} /> : <Play size={15} />}
            </button>
            <button type="button" onClick={() => { setStep(0); setPlaying(true); }} aria-label={t("Replay")}><RotateCcw size={15} /></button>
            <input type="range" min={0} max={total - 1} value={step} aria-label={t("Progress")}
              onChange={(e) => { setStep(Number(e.target.value)); setPlaying(false); }} />
            <div className="sv-speed" role="group" aria-label={t("Speed")}>
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
