import { useEffect, useRef, useState } from 'react';
import { api, ApiError, request } from '../api';
import { useLocale } from '../locale';
import { taxJurisdictions } from '../income-tax';
import type { Case } from '../workspace';
import './planning-panel.css';
import PlanningResult from './PlanningResult';

type Input = {date:string; mode:string; amount:number; currency:string;
  payer:{jur:string; facts?:Record<string,unknown>}; payee:{jur:string; subject?:string; facts?:Record<string,unknown>};
  [key:string]:unknown};
type View = {revision:number; planning_input:Input|null};
type Run = {id:string; case_revision:number; status:string; created_at:number; error:string|null};
type Page = {items:Run[]; next_before:string|null};

export default function PlanningPanel({current,onUpdate}:{current:Case;onUpdate:(doc:Case)=>void}) {
  const {locale}=useLocale(), en=locale==='en';
  const say=(zh:string,english:string)=>en?english:zh;
  const [base,setBase]=useState<Input|null>(null), [revision,setRevision]=useState(current.revision);
  const [form,setForm]=useState({date:'',mode:'plan',amount:'',currency:'',payer:'',payee:'',subject:'company'});
  const [ready,setReady]=useState(false),[pending,setPending]=useState(false),[dirty,setDirty]=useState(false);
  const [error,setError]=useState(''),[notice,setNotice]=useState(''),[historyError,setHistoryError]=useState(false);
  const [history,setHistory]=useState<Page>({items:[],next_before:null});
  const [selected,setSelected]=useState<Run|null>(null);
  const alive=useRef(true),receipt=useRef({signature:'',id:''}),submission=useRef({revision:-1,id:''});
  const loadingHistory=useRef(false);
  const prefix=`/cases/${current.id}`;
  function install(view:View) {
    const input=view.planning_input;
    setBase(input);setRevision(view.revision);setDirty(false);setReady(true);
    if(input)setForm({date:input.date,mode:input.mode,amount:String(input.amount),currency:input.currency,
      payer:input.payer.jur,payee:input.payee.jur,subject:input.payee.subject||'company'});
  }
  function fail(cause:unknown) {
    setError(cause instanceof ApiError && cause.code==='revision_conflict'
      ?say('案件已修改，请重新载入已保存资料后再提交。','The case changed. Reload saved details before submitting.')
      :say('操作未完成，请重试。','The operation did not complete. Retry.'));
  }
  async function refresh(before?:string) {
    if(loadingHistory.current)return;
    loadingHistory.current=true;
    try {
      const page=await request<Page>(`${prefix}/planning-runs${before?`?before=${before}`:''}`);
      if(alive.current){setHistory(old=>before?{...page,items:[...old.items,...page.items]}:page);setHistoryError(false);}
    }catch{if(alive.current)setHistoryError(true);}finally{loadingHistory.current=false;}
  }
  useEffect(()=>{
    alive.current=true;
    let ignore=false;
    request<View>(`${prefix}/planning-input`).then(view=>{if(!ignore)install(view);}).catch(cause=>{if(!ignore)fail(cause);});
    void refresh();
    return ()=>{ignore=true;alive.current=false;};
  },[current.id]);
  function edit(key:keyof typeof form,value:string){setForm(old=>({...old,[key]:value}));setDirty(true);setNotice('');setError('');}
  async function reload(){setPending(true);try{const view=await request<View>(`${prefix}/planning-input`);if(alive.current){install(view);setError('');}}catch(cause){if(alive.current)fail(cause);}finally{if(alive.current)setPending(false);}}
  async function save(event:React.FormEvent){
    event.preventDefault();setError('');setNotice('');
    if(base&&(base.payer.jur!==form.payer||base.payee.jur!==form.payee||(base.payee.subject||'company')!==form.subject)){
      setError(say('更换税区或主体请新建案件，以免沿用原持股及税务事实。','Create a new case to change jurisdictions or taxpayer type without carrying over prior tax facts.'));return;
    }
    const amount=Number(form.amount);
    if(form.amount.trim()===''||!Number.isFinite(amount)||amount<0)return;
    const inputs={...(base||{}),date:form.date,mode:form.mode,amount,currency:form.currency,
      payer:{...(base?.payer||{}),jur:form.payer},payee:{...(base?.payee||{}),jur:form.payee,subject:form.subject}};
    const signature=JSON.stringify([revision,inputs]);
    if(receipt.current.signature!==signature)receipt.current={signature,id:crypto.randomUUID()};
    setPending(true);
    try{
      const view=await request<View>(`${prefix}/planning-input`,'PUT',{revision,request_id:receipt.current.id,inputs});
      if(alive.current){install(view);setNotice(say('规划资料已保存。','Planning details saved.'));}
      const doc=await api.get(current.id);if(alive.current)onUpdate(doc);
    }catch(cause){if(alive.current)fail(cause);}finally{if(alive.current)setPending(false);}
  }
  async function submit(){
    if(!base||dirty)return;
    if(submission.current.revision!==revision)submission.current={revision,id:crypto.randomUUID()};
    setPending(true);setError('');
    try{
      await request(`${prefix}/planning-runs`,'POST',{revision,request_id:submission.current.id});
      if(alive.current)setNotice(say('任务已提交，可刷新查看进度。','Task submitted. Refresh to check progress.'));
      await refresh();
    }catch(cause){if(alive.current)fail(cause);}finally{if(alive.current)setPending(false);}
  }
  const countries=Object.entries(taxJurisdictions).map(([code,names])=><option key={code} value={code}>{names[en?1:0]}</option>);
  const states:Record<string,string>={queued:say('排队中','Queued'),running:say('计算中','Running'),succeeded:say('计算完成','Completed'),failed:say('未完成','Failed')};
  return <details className="planning-panel"><summary>{say('跨境股息规划','Cross-border dividend planning')}</summary>
    <p>{say('付款方为企业，收款方可为企业或个人。资料不足或法规依据尚未核验时，任务不能形成完整结论。','The payer is a company; the recipient may be a company or individual. Missing facts or unverified sources prevent a complete conclusion.')}</p>
    {error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
    <button type="button" disabled={pending} onClick={()=>void reload()}>{say('重新载入已保存资料','Reload saved details')}</button>
    <form onSubmit={save}><fieldset disabled={!ready||pending}>
      <label>{say('付款方税区','Payer jurisdiction')}<select required value={form.payer} onChange={e=>edit('payer',e.target.value)}><option value="">{say('请选择','Choose')}</option>{countries}</select></label>
      <label>{say('收款方税区','Recipient jurisdiction')}<select required value={form.payee} onChange={e=>edit('payee',e.target.value)}><option value="">{say('请选择','Choose')}</option>{countries}</select></label>
      <label>{say('收款方类型','Recipient type')}<select value={form.subject} onChange={e=>edit('subject',e.target.value)}><option value="company">{say('企业','Company')}</option><option value="individual">{say('个人','Individual')}</option></select></label>
      <label>{say('付款日期','Payment date')}<input required type="date" value={form.date} onChange={e=>edit('date',e.target.value)}/></label>
      <label>{say('股息金额','Dividend amount')}<input required type="number" min="0" step="any" value={form.amount} onChange={e=>edit('amount',e.target.value)}/></label>
      <label>{say('付款币种','Payment currency')}<input required pattern="[A-Z]{3}" maxLength={3} value={form.currency} onChange={e=>edit('currency',e.target.value.toUpperCase())}/></label>
      <label>{say('分析方式','Analysis mode')}<select value={form.mode} onChange={e=>edit('mode',e.target.value)}><option value="plan">{say('比较方案','Compare options')}</option><option value="record">{say('按已知事实分析','Assess known facts')}</option></select></label>
      <button type="submit">{say('保存规划资料','Save planning details')}</button>
    </fieldset></form>
    <button type="button" disabled={pending||!base||dirty} onClick={()=>void submit()}>{say('提交规划任务','Submit planning task')}</button>
    <h3>{say('规划历史','Planning history')}</h3>
    <button type="button" disabled={pending} onClick={()=>void refresh()}>{say('刷新进度','Refresh progress')}</button>
    {historyError&&<p role="alert">{say('无法载入历史任务，请刷新重试。','Could not load task history. Refresh to retry.')}</p>}
    {!historyError&&history.items.length===0&&<p>{say('暂无规划任务。','No planning tasks yet.')}</p>}
    <ul>{history.items.map(run=><li key={run.id}>{new Date(run.created_at*1000).toLocaleString(en?'en':'zh-CN')} · {say('案件版本','Case revision')} {run.case_revision} · {states[run.status]||run.status}
      {run.status==='succeeded'&&<button type="button" onClick={()=>setSelected(run)}>{say('查看结果','View results')}</button>}
      {run.error&&<p>{run.error==='planning_sources_unavailable'?say('法规依据缺失或仍待审核。','Legal sources are missing or awaiting review.'):say('任务未完成，请核对资料或联系维护人员。','The task did not complete. Check the details or contact support.')}</p>}</li>)}</ul>
    {history.next_before&&<button type="button" onClick={()=>void refresh(history.next_before!)}>{say('更早的任务','Earlier tasks')}</button>}
    {selected&&<><button type="button" onClick={()=>setSelected(null)}>{say('关闭结果','Close results')}</button><PlanningResult key={selected.id} caseId={current.id} runId={selected.id} revision={selected.case_revision}/></>}
  </details>;
}
