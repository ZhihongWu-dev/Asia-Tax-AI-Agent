import type { Passage } from "../workspace";
import { useLocale } from "../locale";

export default function Passages({ passages }: { passages: Passage[] }) {
  const { t } = useLocale();
  return (
    <div className="knowledge-passages">
      {passages.map((p) => (
        <details
          className="knowledge-passage"
          key={`${p.source_id}-${p.unit_id}`}
        >
          <summary>{p.locator || p.heading || p.unit_id}</summary>
          {p.is_synthetic && <p role="status">{t("模拟联调资料，不是真实税务依据。")}</p>}
          {p.title && <p className="passage-source">{p.title}</p>}
          {p.drift && (
            <p className="passage-warning">{t("来源内容已变化，待核对。")}</p>
          )}
          <blockquote>{p.text}</blockquote>
          {!!p.context?.length && <details><summary>{t("上下文原文")}</summary><Passages passages={p.context} /></details>}
          {p.url && (
            <a href={p.url} target="_blank" rel="noopener noreferrer">
              {t("在官方网站阅读")}
            </a>
          )}
          <details className="passage-metadata">
            <summary>{t("来源与版本")}</summary>
            <p>
              {t("原文抓取时间")}：{p.retrieved_at || t("未记录")}
            </p>
            <p>
              {t("知识覆盖截止")}：{p.coverage_cutoff || t("未记录")}
            </p>
            <p>
              {t("专业验证状态")}：{t("尚未验证")}
            </p>
            <p>
              {t("片段编号")}：{p.unit_id}
            </p>
            <p>SHA-256：{p.snapshot_sha256 || t("未记录")}</p>
            <p>
              {t("片段哈希")}：{p.text_sha256 || t("未记录")}
            </p>
          </details>
        </details>
      ))}
    </div>
  );
}
