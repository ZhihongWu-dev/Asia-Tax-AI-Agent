import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check } from "lucide-react";
import { useState } from "react";
import { useLocale } from "../locale";
import HintButton from "./HintButton";

export default function AnswerText({ text, streaming = false }: { text: string; streaming?: boolean }) {
  const { t } = useLocale();
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const label = copied ? t("Copied") : t("Copy answer");
  return <div className="answer-text">
    <div className="chat-reply markdown-answer"><Markdown remarkPlugins={[remarkGfm]} skipHtml
      disallowedElements={["img"]} components={{
        a: ({ children, href }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>,
        table: ({ children }) => <div className="answer-table"><table>{children}</table></div>,
      }}>{text}</Markdown></div>
    {!streaming && <HintButton className="answer-copy icon-button" aria-label={label} onClick={async () => {
      try { await navigator.clipboard.writeText(text); setCopied(true); setFailed(false); }
      catch { setFailed(true); }
    }}>{copied ? <Check size={16} /> : <Copy size={16} />}</HintButton>}
    {failed && <small role="alert">{t("Could not copy. Select the text to copy manually.")}</small>}
  </div>;
}
