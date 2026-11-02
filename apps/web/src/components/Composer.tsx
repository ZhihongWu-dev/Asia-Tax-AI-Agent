import { MAX_ATTACHMENTS, uploadAttachment, imageThumbnail, pdfErrors, splitAttachments, type Attachment } from '../attachments';
import HintButton from "./HintButton";
import { useEffect, useState, useRef } from "react";
import { ArrowUp, Square, Paperclip, X } from "lucide-react";
import { useLocale } from "../locale";

export default function Composer({
  text,
  lastSentText,
  onChange,
  onSend,
  busy = false,
  onStop,
}: {
  text: string;
  lastSentText?: string;
  onChange: (text: string) => void;
  onSend: (text: string, files: Attachment[]) => Promise<boolean>;
  busy?: boolean;
  onStop?: () => void;
}) {
  const { t, locale } = useLocale();
  const say = (zh: string, en: string) => locale === 'zh' ? zh : en;
  const [files, setFiles] = useState<Attachment[]>([]);
  useEffect(() => {
    const sent = splitAttachments(lastSentText || '').files;
    if (sent.length) setFiles(current => JSON.stringify(current) === JSON.stringify(sent) ? [] : current);
  }, [lastSentText]);
  const [reading, setReading] = useState('');
  const [error, setError] = useState('');
  const [failed, setFailed] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const upload = useRef<AbortController | null>(null);
  useEffect(() => () => upload.current?.abort(), []);
  async function select(selected: File[]) {
    if (!selected.length) return;
    const room = MAX_ATTACHMENTS - files.length;
    const batch = selected.slice(0, Math.max(0, room));
    upload.current?.abort();
    const controller = new AbortController(); upload.current = controller;
    setError(selected.length > room ? 'too_many' : ''); setFailed('');
    for (const [index, item] of batch.entries()) {
      setReading(`${index + 1} / ${batch.length}`);
      try {
        const done = await uploadAttachment(item, AbortSignal.any([controller.signal, AbortSignal.timeout(55000)]));
        setFiles(current => [...current, done]);
      } catch (e) {
        if (controller.signal.aborted) return;
        setError(e instanceof Error ? e.message : 'pdf_invalid'); setFailed(item.name);
      }
    }
    if (!controller.signal.aborted) setReading('');
  }
  const composing = useRef(false);
  async function send() {
    if (busy || reading || (!text.trim() && !files.length) || text.length > 4000) return;
    const words = text.trim() || say('附件是这个案子的材料。', 'The attached documents belong to this case.');
    if (await onSend(words, files)) setFiles([]);
  }
  return (
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault();
        send();
      }}
    >
      <input ref={input} type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.webp" hidden onChange={e => { void select(Array.from(e.target.files || [])); e.target.value = ''; }} />
      {reading && <p role="status">{say('正在上传附件', 'Uploading attachments')} {reading}</p>}
      {error && <p role="alert">{failed && `${failed}: `}{error === 'too_many' ? say(`一条消息最多 ${MAX_ATTACHMENTS} 个附件。`, `A message can carry up to ${MAX_ATTACHMENTS} attachments.`) : pdfErrors[error]?.[locale === 'zh' ? 0 : 1] || say('上传失败，请重试。', 'Upload failed. Please try again.')}</p>}
      {files.length > 0 && <div className="attachment-strip">
        {files.map((file, index) => <div className="attachment-chip" key={`${file.name}-${index}`}>
          <>{imageThumbnail(file) ? <img className="attachment-thumbnail" src={imageThumbnail(file)} alt={file.name} /> : <Paperclip size={15} aria-hidden="true" />}</>
          <span className="attachment-name" title={file.name}>{file.name}</span>
          <button type="button" className="attachment-remove" disabled={busy} aria-label={say('移除附件', 'Remove attachment')} onClick={() => setFiles(current => current.filter((_, at) => at !== index))}><X size={14} /></button>
        </div>)}
      </div>}
      <textarea
        aria-label={t("描述交易背景")}
        placeholder={t("描述交易背景，并附上相关文件")}
        value={text}
        rows={2}
        maxLength={4000}
        onChange={(e) => onChange(e.target.value)}
        onPaste={e => {
          const image = Array.from(e.clipboardData.files).find(item => /image\/(png|jpeg|webp)/.test(item.type));
          if (image && !busy && !reading) { e.preventDefault(); void select([image]); }
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
        <button type="button" className="attachment-icon" disabled={busy || Boolean(reading)} onClick={() => input.current?.click()} aria-label={say('添加附件', 'Attach file')} title={say('添加 PDF、Word、Excel 或图片（最多 10 MB）', 'Attach PDF, Word, Excel or an image (up to 10 MB)')}><Paperclip size={21} /></button>
        <span className="key-hint">
          {t("Enter 发送")} · Shift + Enter {t("换行")}
        </span>
        {onStop ? <HintButton type="button" className="send-button" aria-label={t("停止生成")} onClick={onStop}><Square size={16} fill="currentColor" /></HintButton> : <HintButton
          type="submit"
          className="send-button"
          aria-label={t("发送消息")}
          disabled={busy || Boolean(reading) || (!text.trim() && !files.length)}
        >
          <ArrowUp size={19} />
        </HintButton>}
      </div>
    </form>
  );
}
