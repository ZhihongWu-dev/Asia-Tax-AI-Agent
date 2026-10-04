import HintButton from "./HintButton";
import { useEffect, useRef } from "react";
import { FileText, Scale, ArrowDown } from "lucide-react";
import { useState } from "react";
import AnswerText from "./AnswerText";
import {
  fieldLabel,
  type Case,
  type FieldSpec,
  type Analysis,
} from "../workspace";
import { useLocale } from "../locale";
import Passages from "./Passages";
import BrandLoader from "./BrandLoader";

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
            : result.review?.status === "changes_requested"
              ? "内部稿已退回修改"
              : result.review?.status === "unable_to_conclude"
                ? "最终复核：暂不能形成结论"
                : result.review?.status === "approved"
                  ? "内部稿已完成最终复核"
                  : "研究结果 · 待专业复核",
        )}
      </strong>
      {result.is_synthetic && <p role="status">{t("模拟联调资料，不是真实税务依据。")}</p>}
      <p>{t("以下为现有规则的研究结果，不是免税或应税结论。")}</p>
      {!!result.intake_gaps?.length && (
        <details open>
          <summary>{t("当前任务的信息缺口")}</summary>
          <p>{t("已按现有信息生成部分研究稿，以下缺口仍未解决。")}</p>
          <ul>
            {result.intake_gaps.map((gap) => (
              <li key={gap.field}>{label(gap.field)}：{gap.impact}</li>
            ))}
          </ul>
        </details>
      )}
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
      {!!result.review_tasks?.length && (
        <details>
          <summary>{t("进一步复核清单")}</summary>
          <p>{t("以下事项尚未自动判断，请结合事实和证据逐项复核。")}</p>
          {result.review_tasks.map((task) => (
            <div key={task.node}>
              <strong>{t(`node:${task.node}`)}</strong>
              <ul>
                {task.fact_keys.map((key) => (
                  <li key={key}>
                    {label(key)}
                    {task.missing_facts.includes(key)
                      ? ` · ${t("待补充")}`
                      : ` · ${t("已记录，待核实")}`}
                  </li>
                ))}
              </ul>
              <Passages
                passages={result.passages.filter((p) =>
                  task.passage_ids?.includes(p.unit_id),
                )}
              />
            </div>
          ))}
        </details>
      )}
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
        {!!result.missing_locators?.length && (
          <p>
            {t("部分条文未检索到")}：{result.missing_locators.join(", ")}
          </p>
        )}
        {result.nodes.some((node) => node.passage_ids?.length) ? (
          result.nodes
            .filter((node) => node.passage_ids?.length)
            .map((node) => (
              <details key={node.node}>
                <summary>{t(`node:${node.node}`)}</summary>
                <Passages
                  passages={result.passages.filter((p) =>
                    node.passage_ids?.includes(p.unit_id),
                  )}
                />
              </details>
            ))
        ) : (
          <Passages passages={result.passages} />
        )}
      </details>
      {result.related_rulings &&
        result.related_rulings.status !== "not_applicable" && (
          <details>
            <summary>{t("相关官方案例")}</summary>
            <p>
              {t(
                "按关键词匹配的参考案例，不能直接套用其裁定结论。请同时核对背景、适用期间及假设。",
              )}
            </p>
            {result.related_rulings.status === "unavailable" && (
              <p>{t("error:knowledge_unavailable")}</p>
            )}
            {result.related_rulings.status === "no_matching_units" && (
              <p>
                {t("未找到匹配资料，请换用具体条文、案例编号或税务关键词。")}
              </p>
            )}
            <Passages passages={result.related_rulings.passages} />
          </details>
        )}
    </article>
  );
}

export default function Conversation({
  current,
  fields,
  busy,
  onFacts,
  onAnalyze,
  partial = "",
}: {
  current: Case;
  fields: FieldSpec[];
  busy: boolean;
  onFacts: () => void;
  onAnalyze: () => void;
  partial?: string;
}) {
  const { t, locale } = useLocale();
  const bottom = useRef<HTMLDivElement>(null);
  const latest = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  const [away, setAway] = useState(false);
  useEffect(() => {
    const area = bottom.current?.closest(".workspace-scroll");
    if (!area) return;
    following.current = true;
    area.scrollTop = area.scrollHeight;
    const track = () => {
      const isAway = area.scrollHeight - area.scrollTop - area.clientHeight > 100;
      following.current = !isAway; setAway(isAway);
    };
    area.addEventListener("scroll", track, { passive: true });
    track();
    return () => area.removeEventListener("scroll", track);
  }, [current.id]);
  useEffect(() => {
    const area = bottom.current?.closest(".workspace-scroll");
    if (area && following.current) area.scrollTop = area.scrollHeight;
  }, [current.id, current.messages.length, busy, partial]);
  return (
    <section className="conversation" aria-label={t("案例对话")}>
      {current.messages.map((message, index) => (
        <div
          key={message.id}
          ref={index === current.messages.length - 1 ? latest : undefined}
          className={`message ${message.role}`}
        >
          {message.role === "user" ? (
            <div className="user-message-content">
              <p>{message.text}</p>
              {message.delivery === "failed" && (
                <small className="delivery-failed">
                  {t("发送未完成，可重试")}
                </small>
              )}
            </div>
          ) : message.kind === "chat" ? (
            <AnswerText text={message.text || ""} />
          ) : message.kind === "research" && message.research ? (
            <div className="research-response">
              {message.text && <AnswerText text={message.text} />}
              <p>
                {t(
                  message.research.is_synthetic
                    ? "模拟联调资料，不是真实税务依据。"
                    : message.research.reason_code === "evidence_restricted"
                      ? "仅展示已获许可的参考原文；未用于模型分析。"
                      : message.research.passages.length
                        ? "以下为来源原文片段，适用性待核对。"
                        : "未取得可展示的匹配资料。",
                )}
              </p>
              {(message.research_results || [message.research]).map((result, i) => (
                <Passages key={`${result.query}-${i}`} passages={result.passages} />
              ))}
            </div>
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
                {message.text && <AnswerText text={message.text} />}
                {!message.guided && <p>
                  {t(
                    message.state === "needs_resolution"
                      ? "这些事实存在冲突，请在案例信息中修订。"
                      : message.question_fields?.length
                        ? "为了继续梳理，请补充以下信息；不清楚的可以说明。"
                        : "已整理本次信息。请核对事实后开始分析。",
                  )}
                </p>}
                {!message.guided && !!message.question_fields?.length && (
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
          {message.role === "assistant" && message.workflow?.error_code && (
            <p role="alert">{t(`error:${message.workflow.error_code}`)}</p>
          )}
        </div>
      ))}
      {busy && (
        <div className="assistant-pending">
          <BrandLoader label={t("正在思考…")} />
        </div>
      )}
      {partial && <div className="message assistant streaming-answer"><AnswerText text={partial} streaming /></div>}
      {away && <HintButton className="jump-bottom" aria-label={t("回到底部")} onClick={() => {
        const area = bottom.current?.closest(".workspace-scroll");
        following.current = true;
        if (area) area.scrollTop = area.scrollHeight;
        setAway(false);
      }}><ArrowDown size={16} /></HintButton>}
      {Object.keys(current.facts).length > 0 && (
        <div className="conversation-actions">
          <HintButton className="text-button" onClick={onFacts}>
            <FileText size={15} />
            {t("核对案例事实")}
          </HintButton>
          {current.state === "confirmed" && (
            <HintButton
              disabled={busy}
              className="primary-button"
              onClick={onAnalyze}
            >
              {t("开始分析")}
            </HintButton>
          )}
        </div>
      )}
      <div ref={bottom} />
    </section>
  );
}
