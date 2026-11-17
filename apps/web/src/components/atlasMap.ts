import { geoNaturalEarth1, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { Topology, GeometryCollection } from "topojson-specification";
import type { FeatureCollection, Geometry } from "geojson";
import worldUrl from "world-atlas/countries-50m.json?url";

// The tax graph's world map (Natural Earth 1:50m, public domain, through world-atlas; the same file the search replay
// loads, so the browser fetches it once). Natural Earth projection of the whole world; the first view frames the
// library's jurisdictions and the user zooms out to the world.
export const W = 960, H = 500;
const projection = geoNaturalEarth1().fitExtent([[8, 8], [W - 8, H - 8]], { type: "Sphere" });
const path = geoPath(projection);
export const SPHERE = path({ type: "Sphere" }) ?? "";

// where a jurisdiction's marker stands: its capital (Hong Kong and Singapore: the city), longitude and latitude
const ANCHOR: Record<string, [number, number]> = {
  cn: [116.4, 39.9], hk: [114.17, 22.32], sg: [103.82, 1.35], jp: [139.69, 35.69], th: [100.5, 13.75], id: [106.85, -6.21],
  vn: [105.85, 21.03], my: [101.69, 3.14], ae: [54.37, 24.45], kr: [126.98, 37.57], in: [77.21, 28.61],
};

export function anchor(code: string): [number, number] | null {
  const a = ANCHOR[code];
  return a ? (projection(a) as [number, number]) : null;
}

export type Shape = { id: string; name: string; d: string };
let world: Promise<Shape[]> | null = null;

export function loadWorld(): Promise<Shape[]> {
  world ??= fetch(worldUrl).then((r) => r.json()).then((topo: Topology<{ countries: GeometryCollection }>) => {
    const fc = feature(topo, topo.objects.countries) as unknown as FeatureCollection<Geometry, { name?: string }>;
    return fc.features.filter((f) => String(f.id) !== "010")               // Antarctica
      .map((f) => ({ id: String(f.id ?? ""), name: f.properties?.name ?? "", d: path(f) ?? "" })).filter((c) => c.d);
  });
  return world;
}

export type View = { k: number; x: number; y: number };
export const WORLD: View = { k: 1, x: 0, y: 0 };
export const K_MIN = 0.8, K_MAX = 24;

/** The view that frames the library's jurisdictions with some room around them. */
export function regionView(): View {
  const pts = Object.keys(ANCHOR).map((c) => anchor(c)!).filter(Boolean);
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs) - 40, Math.max(...xs) + 40, Math.min(...ys) - 45, Math.max(...ys) + 45];
  const k = Math.min(W / (x1 - x0), H / (y1 - y0));
  return { k, x: W / 2 - k * (x0 + x1) / 2, y: H / 2 - k * (y0 + y1) / 2 };
}

export function zoomAt(v: View, px: number, py: number, factor: number): View {
  const k = Math.min(K_MAX, Math.max(K_MIN, v.k * factor)), r = k / v.k;
  return { k, x: px - (px - v.x) * r, y: py - (py - v.y) * r };
}

// rate -> colour on the frontend's green ramp (apps/web: mint #e6f1ea to brand ink #173f35)
const STOPS: [number, string][] = [[0, "#e4f0e8"], [5, "#b8dac6"], [10, "#80bea0"], [15, "#3f9a77"], [20, "#26725a"], [25, "#173f35"]];
function mix(a: string, b: string, t: number) {
  const p = (s: string, i: number) => parseInt(s.slice(1 + 2 * i, 3 + 2 * i), 16);
  return "#" + [0, 1, 2].map((i) => Math.round(p(a, i) + (p(b, i) - p(a, i)) * t).toString(16).padStart(2, "0")).join("");
}
export function rateColour(rate: number | null): string {
  if (rate === null) return "#d9dfd8";
  for (let i = 1; i < STOPS.length; i++) {
    if (rate <= STOPS[i][0]) return mix(STOPS[i - 1][1], STOPS[i][1], (rate - STOPS[i - 1][0]) / (STOPS[i][0] - STOPS[i - 1][0]));
  }
  return STOPS[STOPS.length - 1][1];
}
export const RAMP = STOPS;
