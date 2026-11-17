import { useEffect, useState } from 'react';
import { request } from '../api';
import { useLocale } from '../locale';

type Row = Record<string, unknown>;
type Artifact = {run_id:string; case_revision:number; content:Row};
type Result = {tax:Row; taxes:Row[]; ranking:Row[]; paths:Row[]; items:Row[]};
function rows(value:unknown):Row[] {
  if(!Array.isArray(value)||value.some(row=>!row||typeof row!=='object'||Array.isArray(row)))throw Error('Invalid result');
  return value;
}
function display(value:unknown):string {
  return typeof value==='string'?value:JSON.stringify(value)??'—';
}

export default function PlanningResult({caseId,runId,revision}:{caseId:string;runId:string;revision:number}) {
  const {locale}=useLocale(), en=locale==='en';
  const say=(zh:string,english:string)=>en?english:zh;
  const [result,setResult]=useState<Result|null>(null),[failed,setFailed]=useState(false),[attempt,setAttempt]=useState(0);
  useEffect(()=>{
    let ignore=false;
    setResult(null);setFailed(false);
    Promise.all(['tax.json','ranking.json','paths.json','open_items.json'].map(name=>
      request<Artifact>(`/cases/${caseId}/planning-runs/${runId}/artifacts/${name}`)))
      .then(artifacts=>{
        const version=artifacts[0].content.version;
        if(typeof version!=='string'||artifacts.some(a=>a.run_id!==runId||a.case_revision!==revision||a.content.version!==version))throw Error('Mismatched result');
        const [tax,ranking,paths,items]=artifacts.map(a=>a.content);
        const next={tax,taxes:rows(tax.taxes),ranking:rows(ranking.ranking),paths:rows(paths.candidates),items:rows(items.open_items)};
        if(next.taxes.some(t=>typeof t.branch_id!=='string'||typeof t.cand_id!=='string'||typeof t.complete!=='boolean'||
            !t.answers_assumed||typeof t.answers_assumed!=='object'||Array.isArray(t.answers_assumed)||
            !Array.isArray(t.needs)||!Array.isArray(t.needs_under_assumption))||
          new Set(next.taxes.map(t=>t.branch_id)).size!==next.taxes.length||
          next.ranking.length!==next.taxes.length||new Set(next.ranking.map(r=>r.branch_id)).size!==next.ranking.length||
          next.ranking.some(r=>(r.rank!==null&&!(typeof r.rank==='number'&&Number.isInteger(r.rank)&&r.rank>0))||!next.taxes.some(t=>t.branch_id===r.branch_id&&t.cand_id===r.cand_id))||
          next.taxes.some(t=>!next.paths.some(p=>p.cand_id===t.cand_id&&Array.isArray(p.path)&&p.path.every(n=>typeof n==='string'))))throw Error('Incomplete result');
        if(!ignore)setResult(next);
      }).catch(()=>{if(!ignore)setFailed(true);});
    return ()=>{ignore=true;};
  },[caseId,runId,revision,attempt]);
  function range(value:unknown) {
    const r=value as {floor?:unknown;ceiling?:unknown}|null;
    const number=(n:unknown)=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString(en?'en':'zh-CN',{maximumFractionDigits:6}):say('未知','Unknown');
    if(!r||typeof r!=='object')return say('未知','Unknown');
    return r.floor===r.ceiling?number(r.floor):`${number(r.floor)} – ${number(r.ceiling)}`;
  }
  return <section className="planning-result" aria-label={say('规划结果','Planning results')}>
    <h4>{say('案件版本','Case revision')} {revision}</h4>
    {failed?<><p role="alert">{say('结果未能完整载入或校验，请重试。','The complete result could not be loaded or verified. Retry.')}</p><button type="button" onClick={()=>setAttempt(a=>a+1)}>{say('重新载入结果','Reload results')}</button></>:
      !result?<p role="status">{say('正在载入结果…','Loading results…')}</p>:<>
        <p>{say('以下为该次任务保存的结果，不随当前表单变化。排序包含条件假设，不代表确定的执行建议；税额不包含另列的重组费用。','These saved results belong to this task and do not change with the current form. Ordering includes conditional assumptions and is not a definitive recommendation; tax amounts exclude separately calculated restructuring costs.')}</p>
        <p>{say('本次股息金额','Submitted dividend amount')}: {display(result.tax.amount)} {display(result.tax.currency)}</p>
        {result.ranking.length===0&&<p>{say('没有生成候选方案。','No candidate options were generated.')}</p>}
        {result.ranking.map(r=>{
          const tax=result.taxes.find(t=>t.branch_id===r.branch_id)!;
          const path=result.paths.find(p=>p.cand_id===r.cand_id)!;
          return <details key={String(r.branch_id)} className="planning-option"><summary>
            {r.rank==null?say('未参与排序','Not ranked'):`${say('条件排序','Conditional order')} ${display(r.rank)}`} · {(path.path as string[]).join(' → ')} · {display(r.branch_id)}
          </summary>
            <p>{tax.complete===true?say('可计算；仍需核对下列条件。','Calculable; review the conditions below.'):say('资料不完整，不能形成完整税额结论。','Incomplete facts prevent a complete tax conclusion.')}</p>
            {r.why!=null&&<p>{display(r.why)}</p>}
            <p>{say('税额区间','Tax amount range')}: {range(tax.amount)} {display(result.tax.currency)}</p>
            <p>{say('每 100 单位股息税额','Tax per 100 dividend units')}: {range(tax.per_100)}</p>
            <h5>{say('假设及待确认条件','Assumptions and unresolved conditions')}</h5>
            <pre>{JSON.stringify({answers_assumed:tax.answers_assumed,answers_about:tax.answers_about,needs:tax.needs,needs_under_assumption:tax.needs_under_assumption},null,2)}</pre>
          </details>;
        })}
        <h4>{say('待确认事项','Open questions')}</h4>
        {result.items.length===0?<p>{say('引擎未列出额外事项；请仍核对各方案条件。','The engine listed no additional questions; still review each option’s conditions.')}</p>:
          <ul>{result.items.map((item,index)=><li key={index}>{display(item.question||item.key||item.need)}
            <details><summary>{say('查看条件详情','Condition details')}</summary><pre>{JSON.stringify(item,null,2)}</pre></details>
          </li>)}</ul>}
      </>}
  </section>;
}
