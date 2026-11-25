import { MAX_ATTACHMENTS, uploadAttachment, imageThumbnail, pdfErrors, splitAttachments, type Attachment } from '../attachments';
import HintButton from "./HintButton";
import FileWindow from "./FileWindow";
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
  const { t } = useLocale();
  const [files, setFiles] = useState<Attachment[]>([]);
  useEffect(() => {
    const sent = splitAttachments(lastSentText || '').files;
    if (sent.length) setFiles(current => JSON.stringify(current) === JSON.stringify(sent) ? [] : current);
  }, [lastSentText]);
  const [reading, setReading] = useState('');
  const [error, setError] = useState('');
  const [failed, setFailed] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const form = useRef<HTMLFormElement>(null);
  const upload = useRef<AbortController | null>(null);
  const [dragging, setDragging] = useState(false);
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
  const selectRef = useRef(select);
  selectRef.current = select;
  useEffect(() => {
    const area = form.current?.closest('.chat-body');
    if (!area) return;
    let depth = 0;
    const hasFiles = (e: DragEvent) => Array.from(e.dataTransfer?.types || []).includes('Files');
    const enter = (e: Event) => {
      const event = e as DragEvent;
      if (!hasFiles(event)) return;
      event.preventDefault();
      if (++depth === 1 && !busy && !reading) setDragging(true);
    };
    const over = (e: Event) => {
      const event = e as DragEvent;
      if (!hasFiles(event)) return;
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = busy || reading ? 'none' : 'copy';
    };
    const leave = (e: Event) => {
      if (!hasFiles(e as DragEvent)) return;
      if (--depth <= 0) { depth = 0; setDragging(false); }
    };
    const drop = (e: Event) => {
      const event = e as DragEvent;
      if (!hasFiles(event)) return;
      event.preventDefault();
      depth = 0; setDragging(false);
      if (!busy && !reading) void selectRef.current(Array.from(event.dataTransfer?.files || []));
    };
    const preventNavigation = (e: DragEvent) => { if (hasFiles(e)) e.preventDefault(); };
    area.addEventListener('dragenter', enter);
    area.addEventListener('dragover', over);
    area.addEventListener('dragleave', leave);
    area.addEventListener('drop', drop);
    window.addEventListener('dragover', preventNavigation);
    window.addEventListener('drop', preventNavigation);
    return () => {
      area.removeEventListener('dragenter', enter);
      area.removeEventListener('dragover', over);
      area.removeEventListener('dragleave', leave);
      area.removeEventListener('drop', drop);
      window.removeEventListener('dragover', preventNavigation);
      window.removeEventListener('drop', preventNavigation);
    };
  }, [busy, reading]);
  const composing = useRef(false);
  async function send() {
    if (busy || reading || (!text.trim() && !files.length) || text.length > 4000) return;
    const words = text.trim() || t('The attached documents belong to this case.');
    if (await onSend(words, files)) setFiles([]);
  }
  return (
    <form
      ref={form}
      className={`composer${dragging ? ' is-dragging' : ''}`}
      onSubmit={(e) => {
        e.preventDefault();
        send();
      }}
    >
      <input ref={input} type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.webp" hidden onChange={e => { void select(Array.from(e.target.files || [])); e.target.value = ''; }} />
      {dragging && <p role="status">{t('Drop files to attach')}</p>}
      {reading && <p role="status">{t('Uploading attachments')} {reading}</p>}
      {error && <p role="alert">{failed && `${failed}: `}{error === 'too_many' ? t('A message can carry up to {n} attachments.').replace('{n}', String(MAX_ATTACHMENTS)) : pdfErrors[error] ? t(pdfErrors[error]) : t('Upload failed. Please try again.')}</p>}
      {files.length > 0 && <FileWindow count={files.length} listClass="attachment-strip">
        {files.map((file, index) => <div className="attachment-chip" key={`${file.name}-${index}`}>
          <>{imageThumbnail(file) ? <img className="attachment-thumbnail" src={imageThumbnail(file)} alt={file.name} /> : <Paperclip size={15} aria-hidden="true" />}</>
          <span className="attachment-name" title={file.name}>{file.name}</span>
          <button type="button" className="attachment-remove" disabled={busy} aria-label={t('Remove attachment')} onClick={() => setFiles(current => current.filter((_, at) => at !== index))}><X size={14} /></button>
        </div>)}
      </FileWindow>}
      <textarea
        aria-label={t("Describe the transaction background")}
        placeholder={t("Describe the transaction background and attach the documents")}
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
        <button type="button" className="attachment-icon" disabled={busy || Boolean(reading)} onClick={() => input.current?.click()} aria-label={t('Attach file')} title={t('Attach PDF, Word, Excel or an image (up to 10 MB)')}><Paperclip size={21} /></button>
        <span className="key-hint">
          {t("Enter to send")} · Shift + Enter {t("New line")}
        </span>
        {onStop ? <HintButton type="button" className="send-button" aria-label={t("Stop generating")} onClick={onStop}><Square size={16} fill="currentColor" /></HintButton> : <HintButton
          type="submit"
          className="send-button"
          aria-label={t("Send message")}
          disabled={busy || Boolean(reading) || (!text.trim() && !files.length)}
        >
          <ArrowUp size={19} />
        </HintButton>}
      </div>
    </form>
  );
}
