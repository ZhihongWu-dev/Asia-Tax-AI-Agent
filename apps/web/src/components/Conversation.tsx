import { useEffect, useRef } from "react";
import {
  ArrowRight,
  BookOpen,
  Check,
  CheckCheck,
  CircleHelp,
  ClipboardList,
  FileCheck2,
  Landmark,
  Pencil,
  Scale,
  ShieldCheck,
} from "lucide-react";
import {
  factLabels,
  receiptOptions,
  sourceInfo,
  type Case,
  type Panel,
} from "../demo";

export default function Conversation({
  current,
  onPanel,
  onConfirm,
  onReceipt,
  onSource,
}: {
  current: Case;
  onPanel: (panel: Panel) => void;
  onConfirm: () => void;
  onReceipt: (value: string) => void;
  onSource: (id: string) => void;
}) {
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end", behavior: "instant" });
  }, [current.id, current.messages.length, current.stage]);
  const ready = Boolean(
    current.facts.entity.trim() && current.facts.income.trim(),
  );
  return (
    <section className="conversation" aria-label="案例对话">
      <div className="conversation-date">
        本次研究会话 <span>·</span> 虚构案例预览
      </div>
      {current.messages.map((m) => (
        <div key={m.id} className={`message ${m.role}`}>
          {m.role === "assistant" && (
            <span className="assistant-avatar">
              <Scale size={18} />
            </span>
          )}
          <div className="message-content">
            {m.role === "assistant" && (
              <div className="assistant-label">
                AsiaTax <span>研究助手 · 示例</span>
              </div>
            )}
            <p>{m.text}</p>
          </div>
        </div>
      ))}
      <div className="structured-response">
        <section className="fact-card" aria-label="案例事实卡">
          <div className="card-heading">
            <span className="heading-icon">
              <ClipboardList size={18} />
            </span>
            <strong>先把事实对齐</strong>
            <span
              className={`status-chip ${current.confirmed ? "confirmed" : ""}`}
            >
              {current.confirmed ? (
                <Check size={12} />
              ) : (
                <CircleHelp size={12} />
              )}
              {current.confirmed ? "已确认" : "待你确认"}
            </span>
          </div>
          <dl className="fact-grid">
            {(
              [
                "entity",
                "jurisdiction",
                "income",
                "period",
                "amount",
                "currency",
              ] as const
            ).map((key) => (
              <div key={key}>
                <dt>{factLabels[key]}</dt>
                <dd className={!current.facts[key] ? "missing" : ""}>
                  {current.facts[key] || "待补充"}
                </dd>
              </div>
            ))}
          </dl>
          <div className="fact-actions">
            <button className="text-button" onClick={() => onPanel("facts")}>
              <Pencil size={14} />
              编辑事实
            </button>
            {current.stage === "facts" ? (
              <button
                className="primary-button"
                disabled={!ready}
                onClick={onConfirm}
              >
                确认并继续
                <ArrowRight size={15} />
              </button>
            ) : (
              <span className="confirmed-label">
                <CheckCheck size={15} />
                已核对基础信息
              </span>
            )}
          </div>
          {!ready && (
            <p className="fact-help">
              请先填写纳税主体与收入类型，其余未知信息可保留为空。
            </p>
          )}
        </section>
        {current.stage === "receipt" && (
          <section className="clarification" aria-labelledby="receipt-question">
            <div className="section-eyebrow">
              <Landmark size={15} />
              补充一个关键信息
            </div>
            <h2 id="receipt-question">这笔收入目前是如何收取的？</h2>
            <p>
              选择最接近的情况。无法确定也没关系，我们会将它记为待确认事项。
            </p>
            <div className="choice-grid">
              {receiptOptions.map((option) => (
                <button key={option} onClick={() => onReceipt(option)}>
                  {option}
                  <ArrowRight size={14} />
                </button>
              ))}
            </div>
          </section>
        )}
        {current.stage === "review" && (
          <section className="review-card" aria-labelledby="review-title">
            <div className="section-eyebrow">
              <FileCheck2 size={16} />
              研究清单 · 示例
            </div>
            <h2 id="review-title">研究起点已整理好</h2>
            <p className="review-intro">
              以下是固定的研究流程示例，尚未运行规则引擎，也不代表豁免资格或应纳税额的判断。
            </p>
            <div className="review-step">
              <span>01</span>
              <div>
                <strong>核实适用范围</strong>
                <p>主体的集团关系、收入来源及所属期间仍需结合证据确认。</p>
              </div>
            </div>
            <div className="review-step">
              <span>02</span>
              <div>
                <strong>核对收取情况</strong>
                <p>
                  你选择了「{current.facts.receipt}
                  」。资金路径及相关安排应由研究人员进一步核实。
                </p>
              </div>
            </div>
            <div className="review-step">
              <span>03</span>
              <div>
                <strong>整理适用条件与证据</strong>
                <p>
                  根据收入类型查阅官方资料，再由合资格人员确认适用条件与所需文件。
                </p>
              </div>
            </div>
            <div className="review-notice">
              <ShieldCheck size={17} />
              <div>
                <strong>待人工复核</strong>
                <span>
                  事实缺口和适用法例尚未核验。金额或税率不会在此预览中计算。
                </span>
              </div>
            </div>
            <div className="sources-label">
              <BookOpen size={14} />
              继续查阅官方资料<span>资料索引，非本次检索结果</span>
            </div>
            <div className="source-chips">
              {sourceInfo.map((s, i) => (
                <button key={s.id} onClick={() => onSource(s.id)}>
                  <span>{i + 1}</span>
                  {s.label}
                  <ArrowRight size={12} />
                </button>
              ))}
            </div>
          </section>
        )}
      </div>
      <div ref={bottom} />
    </section>
  );
}
