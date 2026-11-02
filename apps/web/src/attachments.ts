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
    if (!files.every(file => typeof file.name === 'string' && Array.isArray(file.pages) && file.pages.every((p: { page: unknown; text: unknown }) => typeof p?.page === 'number' && typeof p?.text === 'string'))) return { text, files: [] };
    return { text: text.slice(0, index), files };
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
export const pdfErrors: Record<string, [string, string]> = {
  pdf_invalid: ['无法读取此 PDF，请检查文件是否损坏。', 'Unable to read this PDF. Check that the file is valid.'],
  pdf_too_large: ['附件不能超过 10 MB。', 'Attachments must be no larger than 10 MB.'],
  pdf_too_many_pages: ['每份 PDF 最多 50 页，请拆分后上传。', 'Please split this PDF into files of up to 50 pages.'],
  pdf_too_much_text: ['文字超过 20,000 字符，请上传相关页面。未截断读取。', 'The attachment exceeds 20,000 text characters. Upload the relevant pages. No partial text was accepted.'],
  pdf_encrypted: ['暂不支持加密 PDF，请先解除密码保护。', 'Password-protected PDFs are not supported. Upload an unlocked copy.'],
  pdf_no_text: ['未提取到文字。这可能是扫描件，请先进行 OCR。', 'No text could be extracted. This may be a scanned PDF. Apply OCR first.'],
  pdf_timeout: ['读取超时，请拆分文件后重试。', 'Reading timed out. Split the file and try again.'],
  pdf_busy: ['文件读取服务繁忙，请稍后重试。', 'The document reader is busy. Please try again shortly.'],
};

export function attachmentText(file: Attachment) {
  return file.pages.map(p => `[${p.label || ('Page ' + p.page)}]\n${p.text}`).join('\n\n');
}
export const attachmentWarnings: Record<string, [string, string]> = {
  word_body_only: ['已读取正文和表格文字，图片、页眉页脚、批注等可能未包含。', 'Body and table text extracted. Images, headers, footers and comments may not be included.'],
  excel_values_only: ['已读取单元格内容，未读取图片或图表，也未执行宏或重新计算公式。', 'Cell contents extracted. Images and charts are not read. Macros and formulas are not executed.'],
  excel_cached_formulas: ['公式结果为文件保存的缓存，可能过期或缺失，请核实。', 'Formula results are saved cached values and may be outdated or missing. Please verify them.'],
};
Object.assign(pdfErrors, {
  attachment_image_dimensions: ['图片不能超过 2000 万像素，请缩小后上传。', 'Images must not exceed 20 megapixels. Resize and retry.'],
  attachment_type: ['请选择 PDF、Word、Excel 或图片（PNG/JPG/WebP）。', 'Choose PDF, Word, Excel, or an image (PNG/JPG/WebP).'],
  attachment_invalid: ['文件损坏、加密或格式不匹配，无法读取。', 'The file is damaged, encrypted, or does not match its format.'],
  attachment_no_text: ['文件中未找到可读取的文字；图片请使用清晰的文字截图。', 'No readable text or cells were found.'],
  attachment_expanded_limit: ['文件解压后过大，请拆分后上传。', 'The expanded file is too large. Split it and try again.'],
  attachment_sheet_limit: ['Excel 最多支持 20 个工作表，请拆分文件。', 'Excel files may contain up to 20 worksheets. Please split this file.'],
  attachment_cell_limit: ['表格范围过大，请仅保留相关数据区域后上传。', 'The worksheet range is too large. Upload the relevant data range only.'],
  attachment_doc_unavailable: ['此环境尚未安装旧版 Word 读取组件，请另存为 .docx。', 'The legacy Word reader is unavailable here. Save the file as .docx.'],
});

export function imageThumbnail(file?: Attachment) {
  return file?.kind === 'image' && /^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(file.thumbnail || '') && file.thumbnail!.length < 13000 ? file.thumbnail : undefined;
}
