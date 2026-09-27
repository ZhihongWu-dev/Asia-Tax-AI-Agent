import { useEffect, useRef } from "react";
import { CircleAlert, FileText } from "lucide-react";
import { type Case } from "../workspace";
import { useLocale } from "../locale";

export default function Conversation({
  current,
  onFacts,
}: {
  current: Case;
  onFacts: () => void;
}) {
  const { t } = useLocale();
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end", behavior: "instant" });
  }, [current.id, current.messages.length]);
  return (
    <section className="conversation" aria-label={t("案例对话")}>
      {current.messages.map((m) => (
        <div key={m.id} className="message user">
          <p>{m.text}</p>
        </div>
      ))}
      <div className="service-status" role="status">
        <CircleAlert size={17} />
        <div>
          <strong>{t("分析服务尚未连接")}</strong>
          <p>{t("消息尚未发送，也未生成分析。你可以先整理案例信息。")}</p>
          <button className="text-button" onClick={onFacts}>
            <FileText size={14} />
            {t("整理案例信息")}
          </button>
        </div>
      </div>
      <div ref={bottom} />
    </section>
  );
}
