import { useEffect, useRef } from "react";
import { FileText, Scale } from "lucide-react";
import {
  fieldLabel,
  type Case,
  type FieldSpec,
  type Analysis,
} from "../workspace";
import { useLocale } from "../locale";

function Result({ result, fields }: { result: Analysis; fields: FieldSpec[] }) {
  const { t, locale } = useLocale();
  const label = (key: string) => {
    const f = fields.find((f) => f.field_name === key);
    return f ? fieldLabel(f, locale) : key;
  };
  return (
    <article className={`analysis-result ${result.stale ? "is-stale" : ""}`}>
      <strong>
        {t(
          result.stale
            ? "此分析已过期，请重新确认事实。"
            : "研究结果 · 待专业复核",
        )}
      </strong>
      <p>{t("以下为现有规则的研究结果，不是免税或应税结论。")}</p>
      <div className="result-nodes">
        {result.nodes
          .filter((n) => n.node !== "human_gate")
          .map((n) => (
            <div key={n.node}>
              <span>{t(`node:${n.node}`)}</span>
              <span>{t(`output:${n.output}`)}</span>
            </div>
          ))}
      </div>
      {!!result.blockers.length && (
        <details open>
          <summary>{t("待补充与复核")}</summary>
          <ul>
            {result.blockers.map((key) => (
              <li key={key}>{label(key)}</li>
            ))}
          </ul>
        </details>
      )}
      <details>
        <summary>{t("规则与分析版本")}</summary>
        <p>
          {t("事实版本")} {result.confirmed_revision} · {t("规则版本")}{" "}
          {result.rule_version}
        </p>
        <p>{t("尚未实现的判断节点")}</p>
        <ul>
          {result.missing_nodes.map((n) => (
            <li key={n}>{t(`node:${n}`)}</li>
          ))}
        </ul>
        <p>
          {t("知识覆盖截止")} {result.coverage_cutoff}
        </p>
      </details>
      <details>
        <summary>{t("本次分析的来源")}</summary>
        <p>
          {t(
            result.retrieval_status === "available"
              ? "已取得条文片段，适用期间仍需核对。"
              : "未取得法规原文；以下是规则关联的官方资料链接。",
          )}
        </p>
        {result.sources.map((source) => (
          <a
            key={source.source_id}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {source.title}
          </a>
        ))}
        {result.passages.map((p) => (
          <blockquote key={`${p.source_id}-${p.unit_id}`}>
            <strong>{p.locator}</strong>
            <p>{p.text}</p>
          </blockquote>
        ))}
      </details>
    </article>
  );
}

export default function Conversation({
  current,
  fields,
  busy,
  onFacts,
  onAnalyze,
}: {
  current: Case;
  fields: FieldSpec[];
  busy: boolean;
  onFacts: () => void;
  onAnalyze: () => void;
}) {
  const { t, locale } = useLocale();
  const bottom = useRef<HTMLDivElement>(null);
  const latest = useRef<HTMLDivElement>(null);
  useEffect(() => {
    (busy ? bottom.current : latest.current)?.scrollIntoView({
      block: busy ? "end" : "start",
      behavior: "instant",
    });
  }, [current.id, current.messages.length, busy]);
  return (
    <section className="conversation" aria-label={t("案例对话")}>
      {current.messages.map((message, index) => (
        <div
          key={message.id}
          ref={index === current.messages.length - 1 ? latest : undefined}
          className={`message ${message.role}`}
        >
          {message.role === "user" ? (
            <p>{message.text}</p>
          ) : message.kind === "analysis" ? (
            (() => {
              const result = current.analyses.find(
                (a) => a.id === message.analysis_id,
              );
              return result ? <Result result={result} fields={fields} /> : null;
            })()
          ) : (
            <div className="intake-response">
              <Scale size={20} />
              <div>
                <p>
                  {t(
                    message.state === "needs_resolution"
                      ? "这些事实存在冲突，请在案例信息中修订。"
                      : message.question_fields?.length
                        ? "为了继续梳理，请补充以下信息；不清楚的可以说明。"
                        : "已整理本次信息。请核对事实后开始分析。",
                  )}
                </p>
                {!!message.question_fields?.length && (
                  <ul>
                    {message.question_fields.map((key) => {
                      const field = fields.find((f) => f.field_name === key);
                      return (
                        <li key={key}>
                          {field ? fieldLabel(field, locale) : key}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
      <div className="conversation-actions">
        <button className="text-button" onClick={onFacts}>
          <FileText size={15} />
          {t("核对案例事实")}
        </button>
        {current.state === "confirmed" && (
          <button
            disabled={busy}
            className="primary-button"
            onClick={onAnalyze}
          >
            {t("开始分析")}
          </button>
        )}
      </div>
      {busy && (
        <p className="working-status" role="status">
          {t("正在处理，请稍候…")}
        </p>
      )}
      <div ref={bottom} />
    </section>
  );
}
