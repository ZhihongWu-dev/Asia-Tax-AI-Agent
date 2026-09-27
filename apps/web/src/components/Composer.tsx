import { useLocale } from "../locale";
import { useRef, useState } from "react";
import { ArrowUp, CornerDownLeft, ShieldCheck } from "lucide-react";

export default function Composer({
  onSend,
  starter,
  onClearStarter,
}: {
  onSend: (text: string) => void;
  starter: string;
  onClearStarter: () => void;
}) {
  const { t } = useLocale();
  const [value, setValue] = useState("");
  const composing = useRef(false);
  const text = starter || value;
  function send() {
    if (!text.trim() || text.length > 4000) return;
    onSend(text.trim());
    setValue("");
    onClearStarter();
  }
  return (
    <div className="composer-wrap">
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <textarea
          aria-label={t("描述你的虚构税务案例")}
          placeholder={t("描述你的虚构税务案例，我们一起梳理…")}
          value={text}
          rows={2}
          maxLength={4000}
          onChange={(e) => {
            setValue(e.target.value);
            onClearStarter();
          }}
          onCompositionStart={() => {
            composing.current = true;
          }}
          onCompositionEnd={() => {
            composing.current = false;
          }}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing &&
              !composing.current &&
              e.keyCode !== 229
            ) {
              e.preventDefault();
              send();
            }
          }}
        />
        <div className="composer-bottom">
          <span className="composer-mode">
            <ShieldCheck size={15} />
            {t("仅限虚构案例")}
          </span>
          <div className="send-actions">
            <span className="key-hint">
              {t("Enter 发送")}
              <CornerDownLeft size={12} />
            </span>
            <button
              type="submit"
              className="send-button"
              aria-label={t("发送消息")}
              disabled={!text.trim()}
            >
              <ArrowUp size={19} />
            </button>
          </div>
        </div>
      </form>
      <div className="composer-footnote">
        {t("交互预览 · 未连接 AI 分析服务 · 对话仅保留至刷新页面")}
      </div>
    </div>
  );
}
