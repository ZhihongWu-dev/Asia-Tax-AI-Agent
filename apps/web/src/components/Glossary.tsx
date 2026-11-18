import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { api, ApiError, type AtlasGlossary, type AtlasTerm } from "../api";
import { useLocale } from "../locale";
import BrandLoader from "./BrandLoader";
import { CiteChip } from "./ClauseDialog";
import { humanize, jurName } from "./atlasFormat";

const KINDS: [string, string][] = [["", "全部"], ["client_fact", "客户事实"], ["structure", "结构事实"], ["derived", "推导事实"], ["judgment", "法律判断"]];

/** The tax glossary: the tax areas, and every field and judgment point the rule layer reads, with where and why. */
export default function Glossary({ snapshot, onOpen, onClause }: { snapshot: string; onOpen: (code: string) => void; onClause: (id: string) => void }) {
  const { t, locale } = useLocale();
  const [data, setData] = useState<AtlasGlossary | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("");
  const [jur, setJur] = useState("");
  useEffect(() => {
    let live = true;
    api.atlasGlossary(snapshot).then(d => live && setData(d)).catch((e) => live && setError(e instanceof ApiError ? e.code : "network_error"));
    return () => { live = false; };
  }, [snapshot]);
  const jurs = useMemo(() => Object.fromEntries((data?.jurisdictions ?? []).map((j) => [j.code, j])), [data]);
  const terms = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data?.terms ?? []).filter((x) => (!kind || x.kind === kind) && (!jur || x.jurisdictions.includes(jur))
      && (!q || [x.key, humanize(x.key), x.meaning, x.question].some((s) => s.toLowerCase().includes(q))))
      .sort((a, b) => humanize(a.key).localeCompare(humanize(b.key)));
  }, [data, query, kind, jur]);
  if (error) return <div className="atlas-error" role="alert">{t(`error:${error}`)}</div>;
  if (!data) return <BrandLoader label={t("正在载入…")} />;
  return (
    <div className="atlas-glossary">
      <section className="atlas-card">
        <h2>{t("税务领域")}</h2>
        <p className="atlas-muted">{t("法律库按这些领域收录各辖区的规则；每个辖区页按同样的顺序列出全部参数。")}</p>
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
            <h2>{t("术语")}</h2>
            <p className="atlas-muted">{t("规则层读取的每个事实和法律判断：含义、需要确认什么、在哪些辖区起作用，以及对应的法律条文。")}</p>
          </div>
          <label className="atlas-search">
            <Search size={15} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("搜索术语")} aria-label={t("搜索术语")} />
          </label>
        </div>
        <div className="atlas-filters">
          <div className="atlas-segment" role="radiogroup" aria-label={t("类型")}>
            {KINDS.map(([k, label]) => <button key={k} role="radio" aria-checked={kind === k} onClick={() => setKind(k)}>{t(label)}</button>)}
          </div>
          <select value={jur} onChange={(e) => setJur(e.target.value)} aria-label={t("辖区")}>
            <option value="">{t("全部辖区")}</option>
            {data.jurisdictions.map((j) => <option key={j.code} value={j.code}>{jurName(j, locale)}</option>)}
          </select>
          <span className="atlas-muted">{terms.length} / {data.terms.length}</span>
        </div>
        <div className="atlas-terms">
          {terms.length ? terms.map((x) => <TermCard key={x.key} term={x} jurs={jurs} onOpen={onOpen} onClause={onClause} />)
            : <p className="atlas-muted">{t("没有匹配的术语")}</p>}
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
      {term.question && <p className="atlas-question"><strong>{t("需要确认")}</strong> {term.question}</p>}
      {term.allowed && <p className="atlas-muted">{t("取值")}: {term.allowed.replace(/;/g, ", ")}</p>}
      {term.jurisdictions.length > 0 && (
        <div className="atlas-term-row">
          <span>{t("涉及辖区")}</span>
          {term.jurisdictions.map((c) => {
            const j = jurs[c] ?? (self?.code === c ? self : undefined);
            return <button key={c} className="atlas-chip is-button" onClick={() => onOpen(c)}>{j ? jurName(j, locale) : c.toUpperCase()}</button>;
          })}
        </div>
      )}
      {term.cite_ids.length > 0 && (
        <div className="atlas-term-row">
          <span>{t("法律依据")}</span>
          {term.cite_ids.map((id) => <CiteChip key={id} id={id} onOpen={onClause} />)}
        </div>
      )}
    </article>
  );
}
