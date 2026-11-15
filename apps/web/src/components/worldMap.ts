import { geoMercator, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { Topology, GeometryCollection } from "topojson-specification";
import type { FeatureCollection, Geometry } from "geojson";
import worldUrl from "world-atlas/countries-50m.json?url";

// The search replay drawn on a world map (Natural Earth 1:50m, public domain, through world-atlas). Everything the
// replay draws is in map units: icons, lines and labels scale with the map, so zooming never stacks them.
export const MAP_W = 760, MAP_H = 520;
export const ICON = 18;                      // icon size in map units (pixels at the first view)
const PERSON_DX = 18;                        // the individual stands beside the company of its jurisdiction
const CLUSTER_R = 25;                        // a jurisdiction's two icons and its label keep this far from another's

// ISO 3166-1 numeric ids of the library's jurisdictions as Natural Earth writes them
export const ISO: Record<string, string> = {
  cn: "156", hk: "344", sg: "702", jp: "392", th: "764", id: "360", vn: "704", my: "458", ae: "784", kr: "410", in: "356",
};
// where a jurisdiction's company stands: its capital (Hong Kong and Singapore: the city), longitude and latitude
const ANCHOR: Record<string, [number, number]> = {
  cn: [116.4, 39.9], hk: [114.17, 22.32], sg: [103.82, 1.35], jp: [139.69, 35.69], th: [100.5, 13.75], id: [106.85, -6.21],
  vn: [105.85, 21.03], my: [101.69, 3.14], ae: [54.37, 24.45], kr: [126.98, 37.57], in: [77.21, 28.61],
};

// the first view frames the capitals of the library's jurisdictions
const projection = geoMercator().fitExtent([[80, 55], [MAP_W - 80, MAP_H - 70]],
  { type: "MultiPoint", coordinates: Object.values(ANCHOR) });
const path = geoPath(projection);

export type Country = { id: string; d: string };
let world: Promise<Country[]> | null = null;

export function loadCountries(): Promise<Country[]> {
  world ??= fetch(worldUrl).then((r) => r.json()).then((topo: Topology<{ countries: GeometryCollection }>) => {
    const fc = feature(topo, topo.objects.countries) as unknown as FeatureCollection<Geometry>;
    return fc.features.filter((f) => String(f.id) !== "010")          // Antarctica fills the bottom of a Mercator map
      .map((f) => ({ id: String(f.id ?? ""), d: path(f) ?? "" })).filter((c) => c.d);
  });
  return world;
}

export type Place = { anchor: [number, number]; company: [number, number]; person: [number, number]; moved: boolean };

// The two icons of each jurisdiction at its capital, pushed apart where two jurisdictions would overlap (Singapore and
// Kuala Lumpur); a pushed group keeps a leader line to its capital. A jurisdiction without a capital on file goes to the
// bottom row.
export function places(jurs: string[]): Record<string, Place> {
  const known = jurs.filter((j) => ANCHOR[j]);
  const anchor: Record<string, [number, number]> = {};
  for (const j of known) anchor[j] = projection(ANCHOR[j]) as [number, number];
  jurs.filter((j) => !ANCHOR[j]).forEach((j, i) => { anchor[j] = [60 + i * 70, MAP_H - 40]; });
  const centre: Record<string, [number, number]> = {};
  for (const j of jurs) centre[j] = [anchor[j][0] + PERSON_DX / 2, anchor[j][1]];
  for (let pass = 0; pass < 80; pass++) {
    let moved = false;
    for (let a = 0; a < jurs.length; a++) {
      for (let b = a + 1; b < jurs.length; b++) {
        const p = centre[jurs[a]], q = centre[jurs[b]];
        let dx = q[0] - p[0], dy = q[1] - p[1];
        const d = Math.hypot(dx, dy);
        if (d >= 2 * CLUSTER_R) continue;
        if (d < 0.01) { dx = 1; dy = 0; }
        const push = (2 * CLUSTER_R - d) / 2 / (d || 1);
        p[0] -= dx * push; p[1] -= dy * push; q[0] += dx * push; q[1] += dy * push;
        moved = true;
      }
    }
    if (!moved) break;
  }
  const out: Record<string, Place> = {};
  for (const j of jurs) {
    const [cx, cy] = centre[j];
    const company: [number, number] = [cx - PERSON_DX / 2, cy];
    out[j] = { anchor: anchor[j], company, person: [cx + PERSON_DX / 2, cy],
      moved: Math.hypot(company[0] - anchor[j][0], company[1] - anchor[j][1]) > 3 };
  }
  return out;
}
