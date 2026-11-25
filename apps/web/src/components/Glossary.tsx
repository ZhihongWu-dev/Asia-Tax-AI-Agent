import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { api, ApiError, type AtlasGlossary, type AtlasTerm } from "../api";
import { useLocale } from "../locale";
import BrandLoader from "./BrandLoader";
import { CiteChip } from "./ClauseDialog";
import { humanize, jurName } from "./atlasFormat";

const KINDS: [string, string][] = [["", "All"], ["client_fact", "Client facts"], ["structure", "Structure"], ["derived", "Derived"], ["judgment", "Judgments"]];

/** The tax glossary: the tax areas, and every field and judgment point the rule layer reads, with where and why. */
export default function Glossary({ onOpen, onClause }: { onOpen: (code: string) => void; onClause: (id: string) => void }) {
  const { t, locale } = useLocale();
  const [data, setData] = useState<AtlasGlossary | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("");
  const [jur, setJur] = useState("");
  useEffect(() => {
    api.atlasGlossary().then(setData).catch((e) => setError(e instanceof ApiError ? e.code : "network_error"));
  }, []);
  const jurs = useMemo(() => Object.fromEntries((data?.jurisdictions ?? []).map((j) => [j.code, j])), [data]);
  const terms = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data?.terms ?? []).filter((x) => (!kind || x.kind === kind) && (!jur || x.jurisdictions.includes(jur))
      && (!q || [x.key, humanize(x.key), x.meaning, x.question].some((s) => s.toLowerCase().includes(q))))
      .sort((a, b) => humanize(a.key).localeCompare(humanize(b.key)));
  }, [data, query, kind, jur]);
  if (error) return <div className="atlas-error" role="alert">{t(`error:${error}`)}</div>;
  if (!data) return <BrandLoader label={t("Loading…")} />;
  return (
    <div className="atlas-glossary">
      <section className="atlas-card">
        <h2>{t("Tax areas")}</h2>
        <p className="atlas-muted">{t("The library records each jurisdiction's rules in these areas; every jurisdiction page lists its parameters in the same order.")}</p>
        <div className="atlas-areas">
          {data.slots.map((s) => (
            <article key={s.slot}>
              <h3>{locale === "zh" ? s.title_zh : s.title}</h3>
              <p>{locale === "zh" ? s.text_zh : s.text}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="atlas-card">
        <div className="atlas-card-head">
          <div>
            <h2>{t("Terms")}</h2>
            <p className="atlas-muted">{t("Every fact and legal judgment the rule layer reads: what it means, what has to be established, where it matters and the provisions behind it.")}</p>
          </div>
          <label className="atlas-search">
            <Search size={15} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("Search terms")} aria-label={t("Search terms")} />
          </label>
        </div>
        <div className="atlas-filters">
          <div className="atlas-segment" role="radiogroup" aria-label={t("Type")}>
            {KINDS.map(([k, label]) => <button key={k} role="radio" aria-checked={kind === k} onClick={() => setKind(k)}>{t(label)}</button>)}
          </div>
          <select value={jur} onChange={(e) => setJur(e.target.value)} aria-label={t("Jurisdiction")}>
            <option value="">{t("All jurisdictions")}</option>
            {data.jurisdictions.map((j) => <option key={j.code} value={j.code}>{jurName(j, locale)}</option>)}
          </select>
          <span className="atlas-muted">{terms.length} / {data.terms.length}</span>
        </div>
        <div className="atlas-terms">
          {terms.length ? terms.map((x) => <TermCard key={x.key} term={x} jurs={jurs} onOpen={onOpen} onClause={onClause} />)
            : <p className="atlas-muted">{t("No matching terms")}</p>}
        </div>
      </section>
    </div>
  );
}

export function TermCard({ term, jurs, self, onOpen, onClause }: {
  term: AtlasTerm; jurs: Record<string, { name: string; name_zh: string }>; self?: { code: string; name: string; name_zh: string };
  onOpen: (code: string) => void; onClause: (id: string) => void;
}) {
  const { t, locale } = useLocale();
  const label = KINDS.find(([k]) => k === term.kind)?.[1];
  return (
    <article className="atlas-term">
      <header>
        <h3>{humanize(term.key)}</h3>
        <code>{term.key}</code>
        {label && <span className={`atlas-kind is-${term.kind}`}>{t(label)}</span>}
      </header>
      <p>{term.meaning}</p>
      {term.question && <p className="atlas-question"><strong>{t("To establish")}</strong> {term.question}</p>}
      {term.allowed && <p className="atlas-muted">{t("Values")}: {term.allowed.replace(/;/g, ", ")}</p>}
      {term.jurisdictions.length > 0 && (
        <div className="atlas-term-row">
          <span>{t("Where it matters")}</span>
          {term.jurisdictions.map((c) => {
            const j = jurs[c] ?? (self?.code === c ? self : undefined);
            return <button key={c} className="atlas-chip is-button" onClick={() => onOpen(c)}>{j ? jurName(j, locale) : c.toUpperCase()}</button>;
          })}
        </div>
      )}
      {term.cite_ids.length > 0 && (
        <div className="atlas-term-row">
          <span>{t("Legal basis")}</span>
          {term.cite_ids.map((id) => <CiteChip key={id} id={id} onOpen={onClause} />)}
        </div>
      )}
    </article>
  );
}
