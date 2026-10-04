import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError } from "../api";
import type { KnowledgeResult } from "../workspace";
import { useLocale } from "../locale";
import Passages from "./Passages";

export default function KnowledgeSearch() {
  const { t } = useLocale();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<KnowledgeResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const generation = useRef(0);
  useEffect(
    () => () => {
      generation.current++;
    },
    [],
  );
  async function search(event: FormEvent) {
    event.preventDefault();
    const request = ++generation.current;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const data = await api.search(query.trim());
      if (request === generation.current) setResult(data);
    } catch (e) {
      if (request === generation.current)
        setError(e instanceof ApiError ? e.code : "network_error");
    } finally {
      if (request === generation.current) setBusy(false);
    }
  }
  return (
    <section className="knowledge-search">
      <form onSubmit={search}>
        <label htmlFor="knowledge-query">{t("检索法条与案例")}</label>
        <div className="knowledge-search-row">
          <input
            id="knowledge-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            minLength={2}
            maxLength={500}
            required
            placeholder={t("关键词、条文编号或案例编号")}
          />
          <button
            className="primary-button"
            disabled={busy || query.trim().length < 2}
          >
            {t("检索")}
          </button>
        </div>
      </form>
      {busy && <p role="status">{t("正在处理，请稍候…")}</p>}
      {error && <p role="alert">{t(`error:${error}`)}</p>}
      {result && (
        <div aria-live="polite">
          <p>
            {t(
              result.is_synthetic
                ? "模拟联调资料，不是真实税务依据。"
                : result.passages.length
                ? "以下为来源原文片段，适用性待核对。"
                : "未找到匹配资料，请换用具体条文、案例编号或税务关键词。",
            )}
          </p>
          <Passages passages={result.passages} />
        </div>
      )}
    </section>
  );
}
