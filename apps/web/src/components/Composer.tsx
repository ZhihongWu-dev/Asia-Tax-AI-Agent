import HintButton from "./HintButton";
import { useRef } from "react";
import { ArrowUp, Square } from "lucide-react";
import { useLocale } from "../locale";

export default function Composer({
  text,
  onChange,
  onSend,
  busy = false,
  onStop,
}: {
  text: string;
  onChange: (text: string) => void;
  onSend: (text: string) => void;
  busy?: boolean;
  onStop?: () => void;
}) {
  const { t } = useLocale();
  const composing = useRef(false);
  function send() {
    if (busy || !text.trim() || text.length > 4000) return;
    onSend(text.trim());
  }
  return (
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault();
        send();
      }}
    >
      <textarea
        aria-label={t("输入你的税务问题")}
        placeholder={t("有什么税务问题？")}
        value={text}
        rows={2}
        maxLength={4000}
        onChange={(e) => onChange(e.target.value)}
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
        <span className="key-hint">
          {t("Enter 发送")} · Shift + Enter {t("换行")}
        </span>
        {onStop ? <HintButton type="button" className="send-button" aria-label={t("停止生成")} onClick={onStop}><Square size={16} fill="currentColor" /></HintButton> : <HintButton
          type="submit"
          className="send-button"
          aria-label={t("发送消息")}
          disabled={busy || !text.trim()}
        >
          <ArrowUp size={19} />
        </HintButton>}
      </div>
    </form>
  );
}
