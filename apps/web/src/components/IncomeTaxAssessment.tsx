import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';
import { useLocale } from '../locale';
import type { Case } from '../workspace';
import { policies, resultLabels } from '../income-assessment';

export default function IncomeTaxAssessment({current, disabled, onUpdate}: {
  current: Case; disabled: boolean; onUpdate: (doc: Case) => void;
}) {
  const {locale} = useLocale(), index = locale === 'en' ? 1 : 0;
  const say = (zh: string, en: string) => index ? en : zh;
  const options = current.income_tax ? policies(current.income_tax) : [];
  const [selected,setSelected] = useState(''), [values,setValues] = useState<Record<string,string>>({});
  const [explanation,setExplanation] = useState(''), [confirmed,setConfirmed] = useState(false);
  const [saving,setSaving] = useState(false), [error,setError] = useState('');
  const [conflict,setConflict] = useState(false);
  const retry = useRef({payload:'',id:''}), mounted = useRef(true);
  useEffect(() => { mounted.current=true; return () => {mounted.current=false;}; },[]);
  const policy = options.find(p => p.id === selected);
  const result = current.income_tax_result;
  function edit(key: string, value: string) {setValues(v=>({...v,[key]:value}));setConfirmed(false);setError('');}
  async function calculate(event: React.FormEvent) {
    event.preventDefault(); if (!policy) return;
    const basis: Record<string,unknown> = {policy:policy.id,basis_confirmed:confirmed,basis_explanation:explanation};
    for (const field of policy.fields) basis[field.key] = field.boolean ? values[field.key] === 'true' : values[field.key];
    const payload = JSON.stringify([current.revision,basis]);
    if (retry.current.payload !== payload) retry.current={payload,id:crypto.randomUUID()};
    setSaving(true);setError('');
    try {
      await api.calculateIncomeTax(current.id,current.revision,basis,retry.current.id);
      const next=await api.get(current.id);
      if (mounted.current) onUpdate(next);
    } catch(e) {
      if(mounted.current && e instanceof ApiError && e.code==='revision_conflict') setConflict(true);
      if(mounted.current) setError(e instanceof ApiError && e.code==='revision_conflict'
        ? say('案例已更新，请载入最新已保存资料并重新核对计税基础。','The case changed. Reload saved details and recheck the calculation basis.')
        : say('计算未完成，请核对期间、税制资格和金额后重试。填写内容已保留。','Calculation did not complete. Check the period, regime eligibility and amounts, then retry. Your entries are retained.'));
    } finally {if(mounted.current)setSaving(false);}
  }
  if (!current.income_tax) return null;
  return <section className="income-tax-assessment" aria-label={say('所得税计算','Income-tax calculation')}>
    <h3>{say('核对计税基础并计算','Review the tax basis and calculate')}</h3>
    <p>{say('按所选税制计算已核对的计税基础。结果保留原始资料和依据，尚不代表完成申报或专业审核；金额尚未作评税舍入。','Calculate a checked tax basis under the selected regime. The result retains the facts and sources. It is not a completed return or professional approval; assessment rounding has not been applied.')}</p>
    {disabled && <p>{say('请先保存当前资料，再进行计算。','Save the current details before calculating.')}</p>}
    {!options.length ? <p>{say('此税区、主体或期间的计算流程尚待接入，资料仍可保存。','The calculation workflow for this jurisdiction, taxpayer or period is not yet available. Details can still be saved.')}</p> :
    <form onSubmit={calculate}>
      <fieldset disabled={disabled || saving || current.income_tax_status==='needs_information'}>
        <legend>{say('计算依据','Calculation basis')}</legend>
        <label>{say('适用税制','Applicable regime')}<select required value={selected} onChange={e=>{setSelected(e.target.value);setValues({});setConfirmed(false);setError('');}}>
          <option value="">{say('请选择并核对条件','Select and check the conditions')}</option>
          {options.map(p=><option key={p.id} value={p.id}>{p.label[index]}</option>)}
        </select></label>
        {policy && <><p>{policy.notice[index]}</p><p>{say('金额币种：','Currency: ')}{current.income_tax.currency}</p>
          <div className="facts-field-grid">{policy.fields.map(field=><label key={field.key}>{field.label[index]}
            {field.boolean || field.options ? <select required value={values[field.key] || ''} onChange={e=>edit(field.key,e.target.value)}>
              <option value="">{say('待确认','Not confirmed')}</option>
              {field.boolean ? <><option value="true">{say('是','Yes')}</option><option value="false">{say('否','No')}</option></> : field.options!.map(([value,label])=><option key={value} value={value}>{label[index]}</option>)}
            </select> : <input required type="number" min="0" step="any" value={values[field.key] || ''} onChange={e=>edit(field.key,e.target.value)} />}
          </label>)}</div>
          <label>{say('税基调整和资格依据说明','Tax-basis adjustments and eligibility explanation')}<textarea required minLength={20} maxLength={4000} value={explanation} onChange={e=>{setExplanation(e.target.value);setConfirmed(false);}} /></label>
          <label className="income-tax-confirm"><input type="checkbox" required checked={confirmed} onChange={e=>setConfirmed(e.target.checked)} />{say('我已核对所选税制、计税基础及其与已保存资料的关系。','I have checked the regime, tax basis and reconciliation to the saved facts.')}</label>
          <button type="submit" className="primary-button">{saving ? say('计算中…','Calculating…') : say('计算并保存结果','Calculate and save result')}</button>
        </>}
      </fieldset>
      {error && <p role="alert">{error}</p>}
      {conflict && <button type="button" disabled={saving} onClick={async()=>{
        setSaving(true);
        try { const next=await api.get(current.id); if(mounted.current){onUpdate(next);setConfirmed(false);setConflict(false);setError('');} }
        catch {if(mounted.current)setError(say('无法载入，请重试。','Could not reload. Retry.'));}
        finally {if(mounted.current)setSaving(false);}
      }}>{say('载入最新资料并重新核对','Reload latest facts and review')}</button>}
    </form>}
    {result && <article aria-label={say('已保存计算结果','Saved calculation result')}>
      <h4>{say('已保存计算结果','Saved calculation result')}</h4>
      {disabled && <p>{say('此结果对应上次保存的资料，不包含当前未保存的修改。','This result uses the last saved facts and excludes unsaved changes.')}</p>}
      <p>{new Date(result.created_at).toLocaleString()} · {String(result.result.currency)}</p>
      <dl>{Object.entries(resultLabels).filter(([key])=>result.result[key]!==undefined).map(([key,label])=><div key={key}><dt>{label[index]}</dt><dd>{String(result.result[key])}</dd></div>)}</dl>
      <p>{say('适用规则版本：','Policy version: ')}{String(result.result.policy_version)}</p>
      <p>{say('官方依据：','Official sources:')}</p>
      <ul>{((result.result.sources || (result.result.source ? [result.result.source] : [])) as {url:string;title:string;sha256:string}[]).map(source=><li key={source.sha256}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a></li>)}</ul>
    </article>}
  </section>;
}
