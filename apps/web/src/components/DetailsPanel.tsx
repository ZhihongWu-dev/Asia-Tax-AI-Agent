import { useLocale } from "../locale";
import { useState } from "react";
import {
  BookOpen,
  Check,
  CircleHelp,
  ExternalLink,
  FileText,
  Info,
  Landmark,
  Pencil,
  ShieldCheck,
  X,
} from "lucide-react";
import {
  coverageCutoff,
  factLabels,
  factValue,
  receiptOptions,
  sourceInfo,
  type Case,
  type Facts,
  type Panel,
} from "../demo";

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
  const [edited, setEdited] = useState<Set<keyof Facts>>(() => new Set());
  const title =
    panel === "facts"
      ? t("案例信息")
      : panel === "sources"
        ? t("法规与来源")
        : t("关于这个研究空间");
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
            <div className="panel-overline">CASE DETAILS</div>
            <h3>{t("每一个判断，从事实开始。")}</h3>
            <p className="panel-description">
              {t("核对并修改这个虚构案例的信息。未确定的字段可以留空。")}
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
                  {(key === "entity" || key === "income") && (
                    <span className="required"> *</span>
                  )}
                  {key === "jurisdiction" ? (
                    <>
                      <input value={t("中国香港")} readOnly />
                      <small>{t("当前研究范围为香港 FSIE")}</small>
                    </>
                  ) : key === "receipt" ? (
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
                      value={
                        edited.has(key)
                          ? draft[key]
                          : factValue({ ...current, facts: draft }, key, t)
                      }
                      maxLength={120}
                      required={key === "entity" || key === "income"}
                      placeholder={t("待补充")}
                      onChange={(e) => {
                        setEdited((fields) => new Set([...fields, key]));
                        setDraft({ ...draft, [key]: e.target.value });
                      }}
                    />
                  )}
                </label>
              ))}
              <div className="panel-notice">
                <Info size={16} />
                <span>{t("保存后需要重新确认事实，并重新生成研究清单。")}</span>
              </div>
              <button className="primary-button save-facts" type="submit">
                <Check size={16} />
                {t("保存事实")}
              </button>
            </form>
          </>
        )}
        {panel === "sources" && (
          <>
            <div className="panel-overline">OFFICIAL SOURCES</div>
            <h3>{t("回到依据，读懂上下文。")}</h3>
            <p className="panel-description">
              {t(
                "来自项目资料清单的官方来源入口。此预览未执行实时检索，也未核验当前法例版本。",
              )}
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
              <Landmark size={23} />
              <span className="source-type">{t("官方资料")}</span>
              <h4>{t(selected.label)}</h4>
              <p className="source-english">{selected.title}</p>
              <p>{t(selected.description)}</p>
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
                  <dd className="amber-text">{t("尚未验证")}</dd>
                </div>
              </dl>
              <a
                className="primary-button source-link"
                href={selected.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {t("在官方网站阅读")}
                <ExternalLink size={14} />
              </a>
            </article>
            <p className="source-footnote">
              {t(
                "日期来自仓库资料清单，不代表法例的生效日。请按案例所属期间核对适用版本。",
              )}
            </p>
          </>
        )}
        {panel === "about" && (
          <>
            <div className="about-emblem">
              <ShieldCheck size={32} strokeWidth={1.4} />
            </div>
            <div className="panel-overline">RESEARCH, WITH CONTEXT</div>
            <h3>{t("专业研究，从清晰开始。")}</h3>
            <p className="panel-description">
              {t("AsiaTax 面向税务研究与顾问复核，当前聚焦中国香港 FSIE。")}
            </p>
            <div className="about-item">
              <Pencil size={18} />
              <div>
                <strong>{t("这是交互预览")}</strong>
                <p>
                  {t(
                    "回答与清单来自固定示例，尚未接入模型、规则引擎或实时法规检索。",
                  )}
                </p>
              </div>
            </div>
            <div className="about-item">
              <ShieldCheck size={18} />
              <div>
                <strong>{t("只使用虚构案例")}</strong>
                <p>
                  {t(
                    "不要输入真实客户或个人资料。对话只在当前页面内存中保存，刷新后清空。",
                  )}
                </p>
              </div>
            </div>
            <div className="about-item">
              <BookOpen size={18} />
              <div>
                <strong>{t("保留专业复核")}</strong>
                <p>
                  {t(
                    "页面不提供正式税务意见。所有事实、适用规则和结论均须专业人员核验。",
                  )}
                </p>
              </div>
            </div>
            <div className="keyboard-help">
              <strong>{t("键盘操作")}</strong>
              <span>
                {t("发送消息")}
                <kbd>Enter</kbd>
              </span>
              <span>
                {t("输入换行")}
                <kbd>Shift + Enter</kbd>
              </span>
              <span>
                {t("关闭面板")}
                <kbd>Esc</kbd>
              </span>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
