import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ExternalLink, ScrollText, X } from "lucide-react";
import { api, ApiError, type AtlasClause } from "../api";
import { useLocale } from "../locale";
import HintButton from "./HintButton";

/** A provision verbatim, as the library on Supabase holds it. */
export default function ClauseDialog({ citeId, onClose }: { citeId: string; onClose: () => void }) {
  const { t } = useLocale();
  const [clause, setClause] = useState<AtlasClause | null>(null);
  const [error, setError] = useState("");
  const box = useRef<HTMLElement>(null);
  useEffect(() => {
    let live = true;
    setClause(null); setError("");
    api.atlasClause(citeId).then((c) => live && setClause(c)).catch((e) => live && setError(e instanceof ApiError ? e.code : "network_error"));
    return () => { live = false; };
  }, [citeId]);
  useEffect(() => {
    box.current?.focus();
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose]);
  return createPortal(
    <div className="atlas-dialog-backdrop" onClick={onClose}>
      <section ref={box} tabIndex={-1} className="atlas-dialog" role="dialog" aria-modal="true" aria-labelledby="clause-title" onClick={(e) => e.stopPropagation()}>
        <header>
          <div>
            <ScrollText size={17} />
            <div>
              <h2 id="clause-title">{clause?.title || t("条文原文")}</h2>
              <span className="atlas-cite-id">{citeId}{clause?.label ? ` · ${clause.label}` : ""}</span>
            </div>
          </div>
          <HintButton className="icon-button" aria-label={t("关闭")} onClick={onClose}>
            <X size={18} />
          </HintButton>
        </header>
        <div className="atlas-dialog-body">
          {error ? <p role="alert">{t(`error:${error}`)}</p> : !clause ? <p className="atlas-muted">{t("正在载入…")}</p> :
            <>
              <pre className="atlas-clause-text" lang={clause.lang || undefined}>{clause.text}</pre>
              {clause.total > clause.text.length && <p className="atlas-muted">{t("条文较长，仅显示开头部分。")}</p>}
            </>}
        </div>
        {clause?.url && (
          <footer>
            <a href={clause.url} target="_blank" rel="noreferrer"><ExternalLink size={14} />{t("打开官方来源")}</a>
            <span className="atlas-muted">{t("原文取自 Supabase 法律库")}</span>
          </footer>
        )}
      </section>
    </div>,
    document.body,
  );
}

export function CiteChip({ id, onOpen }: { id: string; onOpen: (id: string) => void }) {
  return <button type="button" className="atlas-cite" onClick={() => onOpen(id)} title={id}>{id}</button>;
}
