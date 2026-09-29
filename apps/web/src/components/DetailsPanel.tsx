import HintButton from "./HintButton";
import FactEditor from "./FactEditor";
import KnowledgeSearch from "./KnowledgeSearch";
import type { FactPatch } from "../api";
import { isRetryable } from "../api";
import { BookOpen, CircleHelp, ExternalLink, FileText, X } from "lucide-react";
import {
  coverageCutoff,
  sourceInfo,
  type Case,
  type FieldSpec,
  type Panel,
} from "../workspace";
import { useLocale } from "../locale";

export default function DetailsPanel({
  panel,
  current,
  selectedSource,
  onClose,
  onSave,
  onSelectSource,
  fields,
  busy,
  onConfirm,
  error,
  onRetry,
}: {
  panel: Exclude<Panel, null>;
  current: Case;
  selectedSource: string;
  onClose: () => void;
  onSave: (facts: FactPatch) => void;
  fields: FieldSpec[];
  busy: boolean;
  onConfirm: () => void;
  error: string;
  onRetry: () => void;
  onSelectSource: (id: string) => void;
}) {
  const { t } = useLocale();
  const title =
    panel === "facts"
      ? t("案例信息")
      : panel === "sources"
        ? t("法规与来源")
        : t("关于 Taxora");
  const selected =
    sourceInfo.find((s) => s.id === selectedSource) || sourceInfo[0];
  return (
    <section className="details-panel" aria-labelledby="panel-title">
      <header className="panel-header">
        <div>
          {panel === "sources" ? (
            <BookOpen size={18} />
          ) : panel === "facts" ? (
            <FileText size={18} />
          ) : (
            <CircleHelp size={18} />
          )}
          <h2 id="panel-title">{title}</h2>
        </div>
        <HintButton
          className="icon-button"
          aria-label={t("关闭详情")}
          onClick={onClose}
        >
          <X size={18} />
        </HintButton>
      </header>
      <div className="panel-body">
        {error && (
          <div className="request-error" role="alert">
            {t(`error:${error}`)}{" "}
            {isRetryable(error) && (
              <HintButton onClick={onRetry}>{t("重试")}</HintButton>
            )}
          </div>
        )}
        {panel === "facts" && (
          <FactEditor
            key={`${current.id}-${current.revision}`}
            current={current}
            fields={fields}
            busy={busy}
            onSave={onSave}
            onConfirm={onConfirm}
          />
        )}
        {panel === "sources" && (
          <>
            <KnowledgeSearch />
            <p className="panel-description">
              {t("官方资料索引。请核对适用期间及最新版本。")}
            </p>
            <div className="source-selector">
              {sourceInfo.map((s, i) => (
                <HintButton
                  key={s.id}
                  aria-pressed={selected.id === s.id}
                  className={selected.id === s.id ? "selected" : ""}
                  onClick={() => onSelectSource(s.id)}
                >
                  <span>{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <strong>{t(s.label)}</strong>
                    <small>{t(s.tag)}</small>
                  </div>
                </HintButton>
              ))}
            </div>
            <article className="source-detail">
              <h3>{t(selected.label)}</h3>
              <p>{t(selected.description)}</p>
              <a
                className="primary-button source-link"
                href={selected.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {t("在官方网站阅读")}
                <ExternalLink size={14} />
              </a>
              <details className="source-metadata">
                <summary>{t("来源与版本")}</summary>
                <p>{selected.title}</p>
                <dl>
                  <div>
                    <dt>{t("资料清单记录日")}</dt>
                    <dd>{t(selected.captured)}</dd>
                  </div>
                  <div>
                    <dt>{t("知识覆盖截止")}</dt>
                    <dd>{coverageCutoff}</dd>
                  </div>
                  <div>
                    <dt>{t("专业验证状态")}</dt>
                    <dd>{t("尚未验证")}</dd>
                  </div>
                </dl>
              </details>
            </article>
          </>
        )}
        {panel === "about" && (
          <div className="about-content">
            <h3>Taxora</h3>
            <p>{t("税务研究与专业复核的工作空间。")}</p>
            <details open>
              <summary>{t("当前服务状态")}</summary>
              <p>
                {t(
                  "确认事实后运行研究规则。模型连接失败时可重试，不生成替代答案。",
                )}
              </p>
            </details>
            <details>
              <summary>{t("数据与使用范围")}</summary>
              <p>
                {t(
                  "对话和事实保存在后端，可刷新恢复。当前仅用于内部研究，请勿输入真实客户或个人资料。",
                )}
              </p>
            </details>
            <details>
              <summary>{t("专业复核")}</summary>
              <p>
                {t("规则尚待香港税务专家验证，研究资料不构成正式税务意见。")}
              </p>
            </details>
            <details>
              <summary>{t("键盘操作")}</summary>
              <p>
                Enter · {t("发送消息")}
                <br />
                Shift + Enter · {t("换行")}
                <br />
                Esc · {t("关闭面板")}
              </p>
            </details>
          </div>
        )}
      </div>
    </section>
  );
}
