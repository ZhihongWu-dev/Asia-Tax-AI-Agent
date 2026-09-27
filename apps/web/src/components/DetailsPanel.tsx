import { useState } from "react";
import {
  BookOpen,
  Check,
  CircleHelp,
  ExternalLink,
  FileText,
  X,
} from "lucide-react";
import {
  coverageCutoff,
  factLabels,
  receiptOptions,
  sourceInfo,
  type Case,
  type Facts,
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
}: {
  panel: Exclude<Panel, null>;
  current: Case;
  selectedSource: string;
  onClose: () => void;
  onSave: (facts: Facts) => void;
  onSelectSource: (id: string) => void;
}) {
  const { t } = useLocale();
  const [draft, setDraft] = useState({ ...current.facts });
  const title =
    panel === "facts"
      ? t("案例信息")
      : panel === "sources"
        ? t("法规与来源")
        : t("关于 AsiaTax");
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
        <button
          className="icon-button"
          aria-label={t("关闭详情")}
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </header>
      <div className="panel-body">
        {panel === "facts" && (
          <>
            <p className="panel-description">
              {t("记录已知事实，未知项可以留空。")}
            </p>
            <form
              className="facts-form"
              onSubmit={(e) => {
                e.preventDefault();
                onSave(
                  Object.fromEntries(
                    Object.entries(draft).map(([k, v]) => [k, v.trim()]),
                  ) as Facts,
                );
              }}
            >
              {(Object.keys(factLabels) as (keyof Facts)[]).map((key) => (
                <label key={key}>
                  {t(factLabels[key])}
                  {key === "receipt" ? (
                    <select
                      value={draft[key]}
                      onChange={(e) =>
                        setDraft({ ...draft, [key]: e.target.value })
                      }
                    >
                      <option value="">{t("待补充")}</option>
                      {receiptOptions.map((o) => (
                        <option key={o} value={o}>
                          {t(o)}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      value={draft[key]}
                      maxLength={120}
                      placeholder={t("待补充")}
                      onChange={(e) =>
                        setDraft({ ...draft, [key]: e.target.value })
                      }
                    />
                  )}
                </label>
              ))}
              <p className="panel-note">
                {t("仅保存在当前页面，刷新后清空。")}
              </p>
              <button className="primary-button save-facts" type="submit">
                <Check size={15} />
                {t("保存事实")}
              </button>
            </form>
          </>
        )}
        {panel === "sources" && (
          <>
            <p className="panel-description">
              {t("官方资料索引。请核对适用期间及最新版本。")}
            </p>
            <div className="source-selector">
              {sourceInfo.map((s, i) => (
                <button
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
                </button>
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
            <h3>AsiaTax</h3>
            <p>{t("税务研究与专业复核的工作空间。")}</p>
            <details open>
              <summary>{t("当前服务状态")}</summary>
              <p>{t("网页尚未接入分析服务，不会生成税务结论。")}</p>
            </details>
            <details>
              <summary>{t("数据与使用范围")}</summary>
              <p>
                {t(
                  "对话和事实仅在页面内存中保存，刷新后清空。当前仅用于内部研究，请勿输入真实客户或个人资料。",
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
