import { splitAttachments, imageThumbnail } from "../attachments";
import HintButton from "./HintButton";
import FileWindow from "./FileWindow";
import { useEffect, useRef, useState } from "react";
import { ArrowDown, FileText, Paperclip, X } from "lucide-react";
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
  onRemove,
  onReport,
}: {
  current: Case;
  busy: boolean;
  partial?: string;
  process?: ActivityItem[];
  blocks?: RunBlock[];
  working?: boolean;
  onRemove?: (name: string) => Promise<boolean>;
  onReport?: () => void;
}) {
  const { t } = useLocale();
  const [confirming, setConfirming] = useState("");
  const inCase = new Set(current.documents || []);
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
    <section className="conversation" aria-label={t("Case conversation")}>
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
                {files.length > 0 && <FileWindow count={files.length} listClass="sent-attachments">{files.map((file, index) => {
                  const sent = !message.delivery && Boolean(current.documents);
                  const removed = sent && !inCase.has(file.name);
                  const key = `${message.id}/${file.name}`;
                  return <div className={`sent-attachment ${removed ? "is-removed" : ""}`} key={`${file.name}-${index}`}>
                    {imageThumbnail(file)
                      ? <img className="sent-image-thumbnail" src={imageThumbnail(file)} alt={file.name} />
                      : <Paperclip size={16} aria-hidden="true" />}
                    <span title={file.name}>{file.name}</span>
                    {removed && <small className="attachment-state">{t("removed from the case")}</small>}
                    {sent && !removed && onRemove && (confirming === key
                      ? <span className="attachment-confirm">
                          <HintButton type="button" disabled={busy || working} onClick={() => { setConfirming(""); void onRemove(file.name); }}>{t("Remove")}</HintButton>
                          <HintButton type="button" onClick={() => setConfirming("")}>{t("Cancel")}</HintButton>
                        </span>
                      : <HintButton type="button" className="attachment-remove" disabled={busy || working} aria-label={t("Remove this document from the case")}
                          title={t("Wrong file? Remove it from the case")} onClick={() => setConfirming(key)}><X size={14} /></HintButton>)}
                  </div>;
                })}</FileWindow>}
                <p>{text}</p>
                {message.delivery === "failed" && (
                  <small className="delivery-failed">{t("Not completed. You can retry.")}</small>
                )}
              </div>
            ) : (
              <>
                {Boolean(message.activity?.length) && (
                  <ThoughtBlock title={t("Front agent · Thought process")} items={message.activity!} live={false} seconds={message.seconds} />
                )}
                <AnswerText text={message.text || ""} />
                {message.panel && onReport && (
                  <button type="button" className="g-search message-report" onClick={onReport} aria-label={t("Open report")}>
                    <FileText size={14} />{t("Open report")}
                  </button>
                )}
              </>
            )}
          </div>
        );
      })}
      {busy && process.length > 0 && <ThoughtBlock title={t("Front agent · Thought process")} items={process} live />}
      {busy && !partial && !process.length && (
        <div className="assistant-pending">
          <BrandLoader label={t("Thinking…")} />
        </div>
      )}
      {partial && <div className="message assistant streaming-answer"><AnswerText text={partial} streaming /></div>}
      {away && <HintButton className="jump-bottom" aria-label={t("Back to bottom")} onClick={() => {
        const area = bottom.current?.closest(".workspace-scroll");
        following.current = true;
        if (area) area.scrollTop = area.scrollHeight;
        setAway(false);
      }}><ArrowDown size={16} /></HintButton>}
      <div ref={bottom} />
    </section>
  );
}
