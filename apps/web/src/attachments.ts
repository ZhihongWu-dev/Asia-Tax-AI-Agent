import { ApiError } from './api';
export type Attachment = { name: string; kind?: 'pdf' | 'word' | 'excel' | 'image'; thumbnail?: string; warnings?: string[]; page_count: number; pages: { page: number; label?: string; text: string }[]; empty_pages: number[] };
const marker = '\n\n[Taxrora attachment]\n';
const legacyMarker = '\n\n[Taxrora PDF attachment]\n';
export const MAX_ATTACHMENTS = 30;
export function withAttachments(text: string, files: Attachment[]) {
  return files.length ? text + marker + JSON.stringify(files) : text;
}
export function splitAttachments(text: string): { text: string; files: Attachment[] } {
  const delimiter = text.includes(marker) ? marker : legacyMarker;
  const index = text.indexOf(delimiter);
  if (index < 0) return { text, files: [] };
  try {
    const parsed = JSON.parse(text.slice(index + delimiter.length));
    const files: Attachment[] = Array.isArray(parsed) ? parsed : [parsed];                       // messages stored before several files were allowed
    // a file needs its name; pages, where given, must be well formed (a message sent by a script carries only id and name)
    if (!files.every(file => typeof file?.name === 'string' && (file.pages === undefined || (Array.isArray(file.pages) && file.pages.every((p: { page: unknown; text: unknown }) => typeof p?.page === 'number' && typeof p?.text === 'string'))))) return { text, files: [] };
    return { text: text.slice(0, index), files: files.map(file => ({ ...file, pages: file.pages ?? [], page_count: file.page_count ?? 0, empty_pages: file.empty_pages ?? [] })) };
  } catch { return { text, files: [] }; }
}
export async function uploadAttachment(file: File, signal: AbortSignal): Promise<Attachment> {
  if (!/\.(pdf|docx?|xlsx?|png|jpe?g|webp)$/i.test(file.name)) throw new ApiError('attachment_type');
  if (file.size > 10 * 1024 * 1024) throw new ApiError('pdf_too_large');
  const response = await fetch(`/api/attachments?filename=${encodeURIComponent(file.name)}`, {
    method: 'POST', credentials: 'same-origin', signal,
    headers: { 'Content-Type': 'application/octet-stream', 'X-Taxrora-Request': '1' }, body: file,
  });
  if (response.status === 401) window.dispatchEvent(new Event('taxora:unauthorized'));
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(typeof data.detail === 'string' ? data.detail : 'pdf_invalid');
  return data;
}
export const pdfErrors: Record<string, string> = {
  pdf_invalid: 'Unable to read this PDF. Check that the file is valid.',
  pdf_too_large: 'Attachments must be no larger than 10 MB.',
  pdf_too_many_pages: 'Please split this PDF into files of up to 50 pages.',
  pdf_too_much_text: 'The attachment exceeds 20,000 text characters. Upload the relevant pages. No partial text was accepted.',
  pdf_encrypted: 'Password-protected PDFs are not supported. Upload an unlocked copy.',
  pdf_no_text: 'No text could be extracted. This may be a scanned PDF. Apply OCR first.',
  pdf_timeout: 'Reading timed out. Split the file and try again.',
  pdf_busy: 'The document reader is busy. Please try again shortly.',
};

export function attachmentText(file: Attachment) {
  return file.pages.map(p => `[${p.label || ('Page ' + p.page)}]\n${p.text}`).join('\n\n');
}
export const attachmentWarnings: Record<string, string> = {
  word_body_only: 'Body and table text extracted. Images, headers, footers and comments may not be included.',
  excel_values_only: 'Cell contents extracted. Images and charts are not read. Macros and formulas are not executed.',
  excel_cached_formulas: 'Formula results are saved cached values and may be outdated or missing. Please verify them.',
};
Object.assign(pdfErrors, {
  attachment_image_dimensions: 'Images must not exceed 20 megapixels. Resize and retry.',
  attachment_type: 'Choose PDF, Word, Excel, or an image (PNG/JPG/WebP).',
  attachment_invalid: 'The file is damaged, encrypted, or does not match its format.',
  attachment_no_text: 'No readable text or cells were found.',
  attachment_expanded_limit: 'The expanded file is too large. Split it and try again.',
  attachment_sheet_limit: 'Excel files may contain up to 20 worksheets. Please split this file.',
  attachment_cell_limit: 'The worksheet range is too large. Upload the relevant data range only.',
  attachment_doc_unavailable: 'The legacy Word reader is unavailable here. Save the file as .docx.',
});

export function imageThumbnail(file?: Attachment) {
  return file?.kind === 'image' && /^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(file.thumbnail || '') && file.thumbnail!.length < 13000 ? file.thumbnail : undefined;
}
