import {useEffect, useState} from 'react';
import {request} from '../api';
import {useLocale} from '../locale';

type Summary = {id:string; created_at:string; matches_current_income_facts:boolean;
  document_inventory_complete:boolean; all_foreign_items_assessed:boolean};
type Workpaper = {result:{assessed_credit_subtotal:string; currency:string;
  unassessed_foreign_income_indexes:number[]; items:{income_index:number; credit:string;
  saved_income:{description:string; source_jurisdiction:string; gross_amount:string};
  basis:{basis_explanation:string; vietnam_tax_limit:string}}[]}};

export default function IncomeCreditHistory({caseId, revision}:{caseId:string; revision:number}) {
  const {locale}=useLocale();
  const say=(zh:string,en:string)=>locale==='en'?en:zh;
  const [rows,setRows]=useState<Summary[]|null>(null), [selected,setSelected]=useState('');
  const [detail,setDetail]=useState<Workpaper|null>(null), [error,setError]=useState(false);
  const [refresh,setRefresh]=useState(0);
  useEffect(()=>{
    let active=true;
    setRows(null);setSelected('');setDetail(null);setError(false);
    request<{workpapers:Summary[]}>(`/cases/${caseId}/income-tax/credit-workpapers`)
      .then(value=>{if(active)setRows(value.workpapers);})
      .catch(()=>{if(active)setError(true);});
    return ()=>{active=false;};
  },[caseId,revision,refresh]);
  useEffect(()=>{
    let active=true;setDetail(null);
    if(selected)request<Workpaper>(`/cases/${caseId}/income-tax/credit-workpapers/${selected}`)
      .then(value=>{if(active)setDetail(value);}).catch(()=>{if(active)setError(true);});
    return ()=>{active=false;};
  },[caseId,selected]);
  return <section aria-label={say('抵免底稿记录','Credit workpaper history')}>
    <h4>{say('抵免底稿记录','Credit workpaper history')}</h4>
    <p>{say('底稿记录已核对项目的抵免金额，完整所得税计算和申报核验仍需完成。','Workpapers record credits for reviewed items. Complete income-tax assessment and filing checks are still required.')}</p>
    {error && <p role="alert">{say('底稿读取失败，请重试。','Could not load workpapers. Please retry.')}</p>}
    <button type="button" onClick={()=>setRefresh(n=>n+1)}>{say('刷新底稿','Refresh workpapers')}</button>
    {!rows&&!error&&<p>{say('正在读取底稿…','Loading workpapers…')}</p>}
    {rows?.length===0&&<p>{say('此案件尚无已保存的抵免底稿。','No saved credit workpapers for this case.')}</p>}
    {rows?.map(row=><div key={row.id}>
      <button type="button" onClick={()=>{setError(false);setSelected(row.id);}} aria-pressed={selected===row.id}>
        {say('查看底稿','View workpaper')} {new Date(row.created_at).toLocaleString(locale==='en'?'en-GB':'zh-CN')}
      </button>
      <p>{row.matches_current_income_facts?say('与当前已保存收入一致','Matches current saved income'):say('收入资料已修改：此底稿仅供历史追溯','Income facts changed: historical workpaper only')}</p>
      <p>{row.document_inventory_complete?say('所选材料清单已核对','Selected document inventory checked'):say('材料仍有缺项或未核对项','Documents missing or unchecked')}</p>
      {!row.all_foreign_items_assessed&&<p>{say('仍有境外收入未纳入本底稿','Some foreign income is not assessed in this workpaper')}</p>}
    </div>)}
    {detail&&<section aria-label={say('抵免底稿明细','Credit workpaper details')}>
      <p>{say('已核对项目抵免小计','Reviewed credit subtotal')}: {detail.result.assessed_credit_subtotal} {detail.result.currency}</p>
      {detail.result.items.map(item=><div key={item.income_index}>
        <h5>{say('收入','Income')} {item.income_index+1}: {item.saved_income.description}</h5>
        <p>{item.saved_income.source_jurisdiction.toUpperCase()} · {say('收入总额','Gross income')}: {item.saved_income.gross_amount}</p>
        <p>{say('抵免限额','Credit limit')}: {item.basis.vietnam_tax_limit} · {say('抵免金额','Credit amount')}: {item.credit}</p>
        <p>{item.basis.basis_explanation}</p>
      </div>)}
    </section>}
  </section>;
}
