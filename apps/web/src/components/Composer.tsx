import { uploadAttachment, imageThumbnail, pdfErrors, splitAttachment, type Attachment } from '../attachments';
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
  onSend: (text: string, file?: Attachment) => Promise<boolean>;
  busy?: boolean;
  onStop?: () => void;
}) {
  const { t, locale } = useLocale();
  const say = (zh: string, en: string) => locale === 'zh' ? zh : en;
  const [file, setFile] = useState<Attachment>();
  useEffect(() => {
    const sent = splitAttachment(lastSentText || '').file;
    if (sent) setFile(current => current && JSON.stringify(current) === JSON.stringify(sent) ? undefined : current);
  }, [lastSentText]);
  const [reading, setReading] = useState(false);
  const [error, setError] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const form = useRef<HTMLFormElement>(null);
  const [dragging, setDragging] = useState(false);
  const upload = useRef<AbortController | null>(null);
  useEffect(() => () => upload.current?.abort(), []);
  async function select(selected?: File) {
    if (!selected) return;
    upload.current?.abort();
    const controller = new AbortController(); upload.current = controller;
    setReading(true); setError(''); setFile(undefined);
    try { setFile(await uploadAttachment(selected, AbortSignal.any([controller.signal, AbortSignal.timeout(55000)]))); }
    catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'pdf_invalid'); }
    finally { if (!controller.signal.aborted) setReading(false); }
  }
  const composing = useRef(false);
  const selectRef = useRef(select);
  selectRef.current = select;
  useEffect(() => {
    const area = form.current?.closest('.chat-body');
    if (!area) return;
    let depth = 0;
    const files = (event: DragEvent) => Array.from(event.dataTransfer?.types || []).includes('Files');
    const enter = (event: Event) => {
      if (!files(event as DragEvent)) return;
      event.preventDefault();
      if (++depth === 1 && !busy && !reading) setDragging(true);
    };
    const over = (event: Event) => {
      const drag = event as DragEvent;
      if (!files(drag)) return;
      event.preventDefault();
      if (drag.dataTransfer) drag.dataTransfer.dropEffect = busy || reading ? 'none' : 'copy';
    };
    const leave = (event: Event) => {
      if (!files(event as DragEvent)) return;
      if (--depth <= 0) { depth = 0; setDragging(false); }
    };
    const drop = (event: Event) => {
      const drag = event as DragEvent;
      if (!files(drag)) return;
      event.preventDefault(); depth = 0; setDragging(false);
      if (busy || reading) return;
      const selected = Array.from(drag.dataTransfer?.files || []);
      if (selected.length > 1) { setError('multiple_files'); return; }
      void selectRef.current(selected[0]);
    };
    const preventNavigation = (event: DragEvent) => { if (files(event)) event.preventDefault(); };
    area.addEventListener('dragenter', enter);
    area.addEventListener('dragover', over);
    area.addEventListener('dragleave', leave);
    area.addEventListener('drop', drop);
    window.addEventListener('dragover', preventNavigation);
    window.addEventListener('drop', preventNavigation);
    return () => {
      area.removeEventListener('dragenter', enter); area.removeEventListener('dragover', over);
      area.removeEventListener('dragleave', leave); area.removeEventListener('drop', drop);
      window.removeEventListener('dragover', preventNavigation); window.removeEventListener('drop', preventNavigation);
    };
  }, [busy, reading]);
  async function send() {
    if (busy || reading || (!text.trim() && !file) || text.length > 4000) return;
    const question = text.trim() || say('请阅读附件，概括主要内容。', 'Please read the attachment and summarize it.');
    if (await onSend(question, file)) setFile(undefined);
  }
  return (
    <form
      ref={form}
      className="composer"
      onSubmit={(e) => {
        e.preventDefault();
        send();
      }}
    >
      <input ref={input} type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.webp" hidden onChange={e => { void select(e.target.files?.[0]); e.target.value = ''; }} />
      {dragging && <p role="status">{say('松开以上传附件', 'Drop files to attach')}</p>}
      {reading && <p role="status">{say('正在读取附件…', 'Reading attachment…')}</p>}
      {error && <p role="alert">{error === 'multiple_files' ? say('当前一条消息支持一个附件，请选择单个文件。', 'Attach one file per message.') : pdfErrors[error]?.[locale === 'zh' ? 0 : 1] || say('上传失败，请重试。', 'Upload failed. Please try again.')}</p>}
      {file && <div className="attachment-strip">
        <div className="attachment-chip">
          <>{imageThumbnail(file) ? <img className="attachment-thumbnail" src={imageThumbnail(file)} alt={file.name} /> : <Paperclip size={15} aria-hidden="true" />}</>
          <span className="attachment-name" title={file.name}>{file.name}</span>
          <button type="button" className="attachment-remove" disabled={busy} aria-label={say('移除附件', 'Remove attachment')} onClick={() => setFile(undefined)}><X size={14} /></button>
        </div>
      </div>}
      <textarea
        aria-label={t("输入你的税务问题")}
        placeholder={t("有什么税务问题？")}
        value={text}
        rows={2}
        maxLength={4000}
        onChange={(e) => onChange(e.target.value)}
        onPaste={e => {
          const image = Array.from(e.clipboardData.files).find(item => /image\/(png|jpeg|webp)/.test(item.type));
          if (image && !busy && !reading) { e.preventDefault(); void select(image); }
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
        <button type="button" className="attachment-icon" disabled={busy || reading} onClick={() => input.current?.click()} aria-label={say('添加附件', 'Attach file')} title={say('添加 PDF、Word、Excel 或图片（最多 10 MB）', 'Attach PDF, Word, Excel or an image (up to 10 MB)')}><Paperclip size={21} /></button>
        <span className="key-hint">
          {t("Enter 发送")} · Shift + Enter {t("换行")}
        </span>
        {onStop ? <HintButton type="button" className="send-button" aria-label={t("停止生成")} onClick={onStop}><Square size={16} fill="currentColor" /></HintButton> : <HintButton
          type="submit"
          className="send-button"
          aria-label={t("发送消息")}
          disabled={busy || reading || (!text.trim() && !file)}
        >
          <ArrowUp size={19} />
        </HintButton>}
      </div>
    </form>
  );
}
