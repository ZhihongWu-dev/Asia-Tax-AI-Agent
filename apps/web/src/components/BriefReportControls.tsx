import { useCallback, useEffect, useRef, useState } from 'react';
import { Download, FileText, X } from 'lucide-react';
import { request, api } from '../api';
import type { Case } from '../workspace';
import { useLocale } from '../locale';
import { useOverlayFocus } from '../hooks/useOverlayFocus';
import '../consultation.css';

type Job = { id: string; status: 'queued' | 'running' | 'ready' | 'failed' | 'cancelled' | 'expired'; progress: number; message: string; stale?: boolean };
export default function BriefReportControls({doc, busy, update, edit}: {doc: Case; busy: boolean; update: (doc: Case) => void; edit: () => void}) {
  const {locale} = useLocale();
  const say = (zh: string, en: string) => locale === 'en' ? en : zh;
  const brief = doc.consultation;
  const [dialog, setDialog] = useState(false), [confirmed, setConfirmed] = useState(false);
  const [job, setJob] = useState<Job | null>(null), [error, setError] = useState(''), [starting, setStarting] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const modal = useRef<HTMLDivElement>(null), controls = useRef<HTMLDivElement>(null);
  const docRef = useRef(doc), inFlight = useRef(false), updateRef = useRef(update);
  const shownHash = useRef('');
  docRef.current = doc; updateRef.current = update;
  useOverlayFocus(modal, dialog, true, () => setDialog(false));
  useEffect(() => {
    if (job?.status === 'ready' || job?.status === 'cancelled') controls.current?.scrollIntoView({block: 'nearest', behavior: 'smooth'});
  }, [job?.status]);
  useEffect(() => {
    if (brief?.stage === 'ready' && brief.analyzed_hash && !brief.report_job && !brief.generation_consent && shownHash.current !== brief.analyzed_hash) {
      shownHash.current = brief.analyzed_hash; setConfirmed(false); setDialog(true);
    }
  }, [brief?.stage, brief?.analyzed_hash, brief?.report_job, brief?.generation_consent]);
  const start = useCallback(async () => {
    if (inFlight.current) return;
    const snapshot = docRef.current;
    if (!snapshot.consultation?.analyzed_hash) return;
    inFlight.current = true; setStarting(true); setError('');
    try {
      const result = await request<{case: Case; job: Job}>(`/cases/${snapshot.id}/brief/reports`, 'POST', {
        revision: snapshot.revision, request_id: crypto.randomUUID(), input_hash: snapshot.consultation.analyzed_hash, confirmed: true,
      });
      setJob(result.job); updateRef.current(result.case); setDialog(false); setDownloaded(false);
    } catch (e) {
      setError((e as Error).message);
      try { updateRef.current(await api.get(snapshot.id)); } catch { /* preserve original error */ }
    } finally { inFlight.current = false; setStarting(false); }
  }, []);
  useEffect(() => {
    if (brief?.generation_consent && !brief.report_job) void start();
  }, [brief?.generation_consent, brief?.report_job, start]);
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const id = brief?.report_job;
    if (!id) { setJob(null); return; }
    const poll = async () => {
      try {
        const next = await request<Job>(`/cases/${doc.id}/brief/reports/${id}`);
        if (!live) return;
        setJob(next); setError('');
        if (['queued', 'running'].includes(next.status)) timer = setTimeout(poll, 800);
      } catch (e) {
        if (live) { setError((e as Error).message); timer = setTimeout(poll, 3000); }
      }
    };
    void poll();
    return () => { live = false; clearTimeout(timer); };
  }, [doc.id, brief?.report_job]);
  async function cancel() {
    if (!job) return;
    try { setJob(await request<Job>(`/cases/${doc.id}/brief/reports/${job.id}`, 'DELETE')); setError(''); }
    catch (e) { setError((e as Error).message); }
  }
  async function download() {
    if (!job) return;
    try {
      const response = await fetch(`/api/cases/${doc.id}/brief/reports/${job.id}/download`, {credentials:'same-origin'});
      if (!response.ok) throw new Error((await response.json()).detail || 'download_failed');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      link.href = url; link.download = `Taxrora-dividend-brief-${job.id.slice(0,8)}.pdf`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 30000); setDownloaded(true);
    } catch (e) { setError((e as Error).message); }
  }
  const working = starting || (job && ['queued', 'running'].includes(job.status));
  const canGenerate = brief?.stage === 'ready' && (!job || ['failed', 'cancelled', 'expired'].includes(job.status) || job.stale);
  return <div className="consultation-report-controls" ref={controls}>
    {canGenerate && !busy && <div className="conversation-actions">
      <button className="primary-button" disabled={!!working} onClick={() => {setConfirmed(false);setDialog(true);}}>{say('确认生成 PDF', 'Generate PDF')}</button>
      <button className="text-button" onClick={edit}>{say('继续补充信息', 'Add information')}</button>
    </div>}
    {job && <div className="consultation-report-status" role="status" aria-live="polite">
      <p><FileText size={17}/>{job.status === 'ready' ? say('咨询简报生成完成', 'Your brief is ready') : say('PDF 咨询简报', 'PDF consultation brief')} · {job.progress}%</p>
      <progress value={job.progress} max={100} aria-label={say('PDF 生成进度', 'PDF generation progress')}/>
      <p>{job.message}</p>
      {job.stale && <p>{say('资料已更新，旧报告不可下载，请重新生成。', 'Information changed. Generate a fresh report to download.')}</p>}
      {job.status === 'ready' && !job.stale && <div className="conversation-actions">
        <button className="primary-button" onClick={download}><Download size={16}/>{say('下载到本地', 'Download PDF')}</button>
        <button className="text-button" onClick={cancel}><X size={16}/>{say('取消下载并删除文件', 'Cancel download & delete')}</button>
      </div>}
      {downloaded && job.status === 'ready' && <small>{say('已发起浏览器下载。', 'Browser download started.')}</small>}
      {['running','queued'].includes(job.status) && <button className="text-button" onClick={cancel}>{say('取消生成并删除', 'Cancel generation & delete')}</button>}
    </div>}
    {error && <p role="alert" className="request-error">{say('报告操作未完成：', 'Report action failed: ')}{error}</p>}
    {dialog && <div className="consultation-report-backdrop"><div className="consultation-report-dialog" role="dialog" aria-modal="true" aria-labelledby="brief-dialog-title" ref={modal}>
      <h2 id="brief-dialog-title">{say('还有补充信息吗？是否生成 PDF？', 'Anything to add before generating the PDF?')}</h2>
      <p>{say('报告将包含现状、备选路径、建议方案、税负比较、法律条件与实施步骤。未知信息和工具缺口会一并列出。', 'The brief includes the current state, options, recommendation, tax comparison, legal conditions and implementation steps, with any unknowns and tool gaps.')}</p>
      <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>{say('没有其他需要补充的信息，可以生成 PDF 报告。', 'I have no further information to add. Generate the PDF report.')}</label>
      <div className="conversation-actions">
        <button className="text-button" disabled={starting} onClick={() => {setDialog(false);edit();}}>{say('返回补充', 'Go back')}</button>
        <button className="primary-button" disabled={!confirmed || starting} onClick={() => void start()}>{starting ? say('正在创建任务…', 'Starting…') : say('生成 PDF', 'Generate PDF')}</button>
      </div>
    </div></div>}
  </div>;
}
