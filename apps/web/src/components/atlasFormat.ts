import type { AtlasCell } from "../api";
import type { Locale } from "../locale";

export function num(n: number) {
  return Number.isInteger(n) ? String(n) : String(Number(n.toFixed(3)));
}

/** A rate cell as a figure: one value, or the favourable and unfavourable ends when an open point decides between them. */
export function rate(c: AtlasCell | undefined) {
  if (!c || c.floor === null || c.ceiling === null) return "—";
  return c.floor === c.ceiling ? `${num(c.floor)}%` : `${num(c.floor)}–${num(c.ceiling)}%`;
}

export function humanize(key: string) {
  const s = key.replace(/^\$?[a-z]{2}(-[a-z]{2})?\./, "").replace(/[._]+/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function jurName(j: { name: string; name_zh: string }, locale: Locale) {
  return locale === "zh" ? j.name_zh : j.name;
}

export function paramValue(value: string, unit: string) {
  if (unit === "bool") return value === "yes" || value === "true" ? "yes" : value === "no" || value === "false" ? "no" : value;
  if (unit === "%") return `${value}%`;
  return unit && unit !== "text" ? `${value} ${unit}` : value;
}
