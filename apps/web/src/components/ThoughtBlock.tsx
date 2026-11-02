import { useEffect, useRef, useState } from "react";
import { ChevronDown, Sparkles, Wrench } from "lucide-react";
import type { ActivityItem } from "../workspace";
import { useLocale } from "../locale";
import { duration } from "./RunPanel";

/** One agent's process in the conversation: open while it works, folded once it is done. */
export default function ThoughtBlock({ title, items, live, seconds }: {
  title: string;
  items: ActivityItem[];
  live: boolean;
  seconds?: number;
}) {
  const { t } = useLocale();
  const [open, setOpen] = useState(live);
  const body = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  useEffect(() => setOpen(live), [live]);
  useEffect(() => {
    if (open && following.current && body.current) body.current.scrollTop = body.current.scrollHeight;
  }, [items, open]);
  const shown = items.filter((item) => item.kind === "tool" || item.text?.trim());
  const thought = shown.some((item) => item.kind === "thinking");
  return (
    <div className={`thought ${live ? "is-live" : ""}`}>
      <button type="button" className="thought-head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <Sparkles size={15} aria-hidden="true" />
        <span>{title}</span>
        <small>{live ? t("进行中…") : seconds !== undefined ? `${t("用时")} ${duration(seconds)}` : ""}</small>
        <ChevronDown size={15} aria-hidden="true" className="thought-chevron" />
      </button>
      {open && (
        <div
          className="thought-body"
          ref={body}
          onScroll={(event) => {
            const area = event.currentTarget;
            following.current = area.scrollHeight - area.scrollTop - area.clientHeight < 40;
          }}
        >
          {shown.map((item, index) => item.kind === "tool" ? (
            <div key={index} className="thought-tool">
              <Wrench size={12} aria-hidden="true" />
              <span>{item.name}</span>
              {item.detail && <code title={item.detail}>{item.detail}</code>}
            </div>
          ) : (
            <p key={index} className={item.kind === "thinking" ? "thought-text" : "thought-said"}>{item.text?.trim()}</p>
          ))}
          {!shown.length && <p className="thought-text">{live ? t("正在开始…") : t("这一步没有思考内容。")}</p>}
          {!live && shown.length > 0 && !thought && <p className="thought-empty">{t("模型没有输出思考内容。")}</p>}
        </div>
      )}
    </div>
  );
}
