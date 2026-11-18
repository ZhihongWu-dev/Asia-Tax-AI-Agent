import {useEffect, useRef, useState} from 'react';
import {api, ApiError, request} from '../api';
import {useLocale} from '../locale';
import type {Case} from '../workspace';

const documents=[
  ['treaty_credit_application','协定抵免申请','Treaty credit application'],
  ['foreign_income_tax_return','境外所得税申报表','Foreign income tax return'],
  ['foreign_payment_receipt','境外缴税凭证','Foreign payment receipt'],
  ['foreign_authority_paid_tax_confirmation','境外税务机关已缴税确认','Foreign authority paid-tax confirmation'],
  ['foreign_business_legal_evidence','境外经营法律文件','Foreign business legal evidence'],
  ['foreign_authority_sparing_confirmation','境外税务机关饶让确认','Foreign authority sparing confirmation'],
  ['ownership_legal_evidence','持股法律文件','Ownership legal evidence'],
  ['distributor_foreign_tax_return','分配公司境外申报表','Distributor foreign tax return'],
  ['dividend_withholding_return','股息预提税申报表','Dividend withholding return'],
  ['foreign_authority_underlying_tax_confirmation','境外税务机关底层税确认','Foreign authority underlying-tax confirmation'],
  ['representative_authorisation','代理授权文件','Representative authorisation'],
] as const;

export default function VietnamCreditForm({current,disabled,onUpdate}:{current:Case;disabled:boolean;onUpdate:(doc:Case)=>void}) {
  const {locale}=useLocale(), index=locale==='en'?2:1;
  const say=(zh:string,en:string)=>locale==='en'?en:zh;
  const [values,setValues]=useState<Record<string,string>>({}),[saving,setSaving]=useState(false),[error,setError]=useState('');
  const retry=useRef({payload:'',id:''}), mounted=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  const facts=current.income_tax;
  if(!facts || facts.jurisdiction!=='vn'||facts.subject!=='company'||facts.residency!=='resident'||facts.period_start!=='2026-01-01'||facts.period_end!=='2026-12-31')return null;
  const candidates=facts.incomes.map((item,n)=>({item,n,method:
    item.source_jurisdiction==='id'&&['dividend','interest','royalty'].includes(item.category)?'indonesia_deemed':
    item.source_jurisdiction==='sg'&&['interest','royalty'].includes(item.category)?'singapore_interest_royalty':
    ['hk','sg'].includes(item.source_jurisdiction)&&item.category==='dividend'&&item.foreign_tax_paid!==null&&/^0(?:\.0+)?$/.test(item.foreign_tax_paid)?'underlying_dividend':''}));
  if(!candidates.some(row=>row.method))return null;
  const edit=(key:string,value:string)=>{setValues(v=>({...v,[key]:value}));setError('');};
  const check=(key:string,label:string)=><label><input type="checkbox" checked={values[key]==='true'} onChange={e=>edit(key,String(e.target.checked))}/>{label}</label>;
  const input=(key:string,label:string,required=true)=><label>{label}<input required={required} value={values[key]||''} onChange={e=>edit(key,e.target.value)}/></label>;
  async function save(event:React.FormEvent) {
    event.preventDefault();if(disabled||saving)return;
    const lines=candidates.filter(row=>row.method&&values[`${row.n}_include`]==='true').map(({n,method})=>{
      const line:Record<string,unknown>={method,income_index:n,vietnam_tax_limit:values[`${n}_limit`],basis_explanation:values[`${n}_explanation`],treaty_and_same_income_basis_verified:values[`${n}_verified`]==='true'};
      if(method==='singapore_interest_royalty')line.eligible_singapore_tax_paid=values[`${n}_paid`];
      if(method==='underlying_dividend'){
        for(const field of ['qualifying_holding_percent','distributing_profit_after_tax','corporate_tax_paid_on_profit'])line[field]=values[`${n}_${field}`];
        line.corporate_recipient_and_pool_verified=values[`${n}_pool`]==='true';
      }
      return line;
    });
    const credit_types=['direct','tax_sparing','indirect'].filter(kind=>values[kind]==='true');
    if(!lines.length||!credit_types.length){setError(say('请选择收入项目和待核验的抵免材料类别。','Select income items and credit document categories.'));return;}
    const basis={lines,dossier:{credit_types,represented:values.represented==='true',documents:documents.filter(([key])=>values[key]?.trim()).map(([kind])=>({kind,evidence_reference:values[kind].trim(),required_form_and_content_checked:values[`${kind}_checked`]==='true'}))}};
    const payload=JSON.stringify([current.revision,basis]);
    if(retry.current.payload!==payload)retry.current={payload,id:crypto.randomUUID()};
    setSaving(true);setError('');
    try {
      await request(`/cases/${current.id}/income-tax/credit-workpapers`,'POST',{revision:current.revision,request_id:retry.current.id,basis});
      const next=await api.get(current.id);if(mounted.current)onUpdate(next);
    } catch(e){if(mounted.current)setError(e instanceof ApiError&&e.code==='revision_conflict'?say('案件已更新，请重新打开案件并核对最新收入后填写。','Case changed. Reopen it and review the latest income before completing the form.'):say('保存未完成，请核对金额、资格确认及材料类别后重试；填写内容已保留。','Could not save. Check amounts, eligibility confirmations and document categories, then retry. Entries are retained.'));}
    finally {if(mounted.current)setSaving(false);}
  }
  return <section aria-label={say('越南境外抵免底稿','Vietnam foreign credit workpaper')}>
    <h4>{say('越南境外抵免底稿','Vietnam foreign credit workpaper')}</h4>
    <p>{say('金额均为越南盾。当前支持印尼股息、利息和特许权使用费，新加坡利息和特许权使用费，以及香港或新加坡的底层股息税抵免。资格与同项所得抵免限额需依据材料核实。','Amounts are VND. Currently supports Indonesian dividends, interest and royalties, Singapore interest and royalties, and underlying dividend tax from Hong Kong or Singapore. Verify treaty eligibility and the same-income credit limit against evidence.')}</p>
    <form onSubmit={save}><fieldset disabled={disabled||saving}>
      {candidates.filter(row=>row.method).map(({item,n,method})=><fieldset key={n}><legend>{say('收入','Income')} {n+1}: {item.description}</legend>
        <p>{item.source_jurisdiction.toUpperCase()} · {say('已保存总额','Saved gross amount')}: {item.gross_amount}</p>
        {check(`${n}_include`,say('纳入本次底稿','Include in this workpaper'))}
        {values[`${n}_include`]==='true'&&<>
          {input(`${n}_limit`,say('该项所得的越南税额限额','Vietnam tax limit for this income'))}
          {input(`${n}_explanation`,say('协定资格及限额依据说明（至少20字符）','Treaty entitlement and limit explanation (20+ characters)'))}
          {check(`${n}_verified`,say('已核实协定资格及同项所得税额依据','Treaty eligibility and same-income tax basis verified'))}
          {method==='singapore_interest_royalty'&&input(`${n}_paid`,say('符合协定的已缴新加坡税额','Eligible Singapore tax paid'))}
          {method==='underlying_dividend'&&<>
            {input(`${n}_qualifying_holding_percent`,say('符合条件的持股比例（%）','Qualifying holding percentage'))}
            {input(`${n}_distributing_profit_after_tax`,say('分配利润池税后利润','Distributing profit pool after tax'))}
            {input(`${n}_corporate_tax_paid_on_profit`,say('利润池已缴企业税','Corporate tax paid on the profit pool'))}
            {check(`${n}_pool`,say('已核实企业收款人及同质利润池','Corporate recipient and homogeneous profit pool verified'))}
          </>}
        </>}
      </fieldset>)}
      <p>{say('未勾选的境外收入将列为未核算项目。底稿不会替代完整所得税评估。','Unselected foreign income remains unassessed. This workpaper does not replace a complete income-tax assessment.')}</p>
      <fieldset><legend>{say('材料清单','Document inventory')}</legend>
        {check('direct',say('直接抵免材料','Direct-credit documents'))}
        {check('tax_sparing',say('饶让抵免材料','Tax-sparing documents'))}
        {check('indirect',say('间接抵免材料','Indirect-credit documents'))}
        {check('represented',say('由代理人办理','Filed through a representative'))}
        <p>{say('填写案件材料编号；未提供或未核对的必要材料会保留为待补项。','Enter case evidence references. Missing or unchecked required documents remain outstanding.')}</p>
        {documents.map(row=><div key={row[0]}>{input(row[0],row[index],false)}{values[row[0]]?.trim()&&check(`${row[0]}_checked`,row[index]+say('：已核对法定形式及内容',': required form and content checked'))}</div>)}
      </fieldset>
      <button type="submit">{saving?say('保存中…','Saving…'):say('计算并保存抵免底稿','Calculate and save credit workpaper')}</button>
    </fieldset>{error&&<p role="alert">{error}</p>}</form>
  </section>;
}
