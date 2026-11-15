import { splitAttachments, imageThumbnail } from "../attachments";
import HintButton from "./HintButton";
import { useEffect, useRef, useState } from "react";
import { ArrowDown, Paperclip } from "lucide-react";
import AnswerText from "./AnswerText";
import type { ActivityItem, Case, Message, RunBlock } from "../workspace";
import { useLocale } from "../locale";
import BrandLoader from "./BrandLoader";
import ThoughtBlock from "./ThoughtBlock";
import { AGENT_LABEL, STEP_LABEL } from "./RunPanel";

type Entry = { at: string; message?: Message; block?: RunBlock };

export default function Conversation({
  current,
  busy,
  partial = "",
  process = [],
  blocks = [],
  working = false,
}: {
  current: Case;
  busy: boolean;
  partial?: string;
  process?: ActivityItem[];
  blocks?: RunBlock[];
  working?: boolean;
}) {
  const { t } = useLocale();
  const bottom = useRef<HTMLDivElement>(null);
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
  }, [current.id, current.messages.length, busy, partial, process, blocks]);
  const timeline: Entry[] = [
    ...current.messages.map((message) => ({ at: message.at || "9999", message })),
    ...blocks.filter((block) => block.items.length || !block.ended).map((block) => ({ at: block.started, block })),
  ].sort((a, b) => a.at.localeCompare(b.at));
  return (
    <section className="conversation" aria-label={t("案例对话")}>
      {timeline.map(({ message, block }) => {
        if (block) return (
          <ThoughtBlock
            key={block.id}
            title={`${t(AGENT_LABEL[block.agent] || block.agent)} · ${t(STEP_LABEL[block.node] || block.node)}`}
            items={block.items}
            live={!block.ended && working}
            seconds={block.ended ? (Date.parse(block.ended) - Date.parse(block.started)) / 1000 : undefined}
          />
        );
        if (!message) return null;
        const { text, files } = splitAttachments(message.text || "");
        return (
          <div key={message.id} className={`message ${message.role}`}>
            {message.role === "user" ? (
              <div className="user-message-content">
                {files.map((file, index) => <div className="sent-attachment" key={`${file.name}-${index}`}>
                  {imageThumbnail(file)
                    ? <img className="sent-image-thumbnail" src={imageThumbnail(file)} alt={file.name} />
                    : <Paperclip size={16} aria-hidden="true" />}
                  <span title={file.name}>{file.name}</span>
                </div>)}
                <p>{text}</p>
                {message.delivery === "failed" && (
                  <small className="delivery-failed">{t("发送未完成，可重试")}</small>
                )}
              </div>
            ) : (
              <>
                {Boolean(message.activity?.length) && (
                  <ThoughtBlock title={t("前台 Agent · 思考过程")} items={message.activity!} live={false} seconds={message.seconds} />
                )}
                <AnswerText text={message.text || ""} />
              </>
            )}
          </div>
        );
      })}
      {busy && process.length > 0 && <ThoughtBlock title={t("前台 Agent · 思考过程")} items={process} live />}
      {busy && !partial && !process.length && (
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
      <div ref={bottom} />
    </section>
  );
}
