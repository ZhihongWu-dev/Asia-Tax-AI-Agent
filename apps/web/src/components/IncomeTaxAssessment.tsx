import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';
import { useLocale } from '../locale';
import type { Case } from '../workspace';
import { policies, resultLabels } from '../income-assessment';
import { koreaBasis } from '../korea-assessment';
import KoreaCompanyResult from './KoreaCompanyResult';
import { koreaSalaryBasis } from '../korea-salary-assessment';
import KoreaSalaryResult from './KoreaSalaryResult';
import { thaiDividendBasis } from '../thailand-dividend-assessment';
import { thaiForeignBasis } from '../thailand-foreign-assessment';
import ThailandForeignResult from './ThailandForeignResult';
import { vietnamBusinessBasis } from '../vietnam-business-assessment';
import VietnamBusinessResult from './VietnamBusinessResult';
import { vietnamRentalBasis } from '../vietnam-rental-assessment';
import VietnamRentalResult from './VietnamRentalResult';

export default function IncomeTaxAssessment({current, disabled, onUpdate}: {
  current: Case; disabled: boolean; onUpdate: (doc: Case) => void;
}) {
  const {locale} = useLocale(), index = locale === 'en' ? 1 : 0;
  const say = (zh: string, en: string) => index ? en : zh;
  const [selected,setSelected] = useState(''), [values,setValues] = useState<Record<string,string>>({});
  const options = current.income_tax ? policies(current.income_tax,values) : [];
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
    let basis: Record<string,unknown> = {policy:policy.id,basis_confirmed:confirmed,basis_explanation:explanation};
    for (const field of policy.fields) {
      if (field.showWhen && values[field.showWhen[0]] !== field.showWhen[1]) {basis[field.key]=field.boolean?false:null;continue;}
      if (field.monthsList) {
        const raw = values[field.key] || '';
        const months = raw.split(',').map(v=>Number(v.trim()));
        if (!/^\s*\d+\s*(,\s*\d+\s*)*$/.test(raw) || months.length>200 || months.some(v=>!Number.isInteger(v) || v<0 || v>12)) {
          setError(say('每名受抚养人的月份须为0至12的整数，用逗号分隔。','Enter comma-separated whole months from 0 to 12 for each dependent.')); return;
        }
        basis[field.key] = months;
      } else basis[field.key] = field.boolean ? values[field.key] === 'true' : field.integer ? Number(values[field.key]) : values[field.key];
    }
    if (policy.id==='my_individual_2026' && current.income_tax!.residency==='resident') {
      basis.workpaper={sources:current.income_tax!.incomes.map((_item,n)=>({
        income_index:n, additions:basis[`my_source_${n}_additions`],
        deductions:basis[`my_source_${n}_deductions`],
        statutory_charges:basis[`my_source_${n}_statutory_charges`],
        statutory_allowances:basis[`my_source_${n}_statutory_allowances`], explanation,
      })), eligible_prior_business_losses:current.income_tax!.carried_losses,
        schedule4_additions:basis.my_schedule4_additions,
        allowed_total_income_deductions:[basis.my_total_deductions],
        allowed_personal_reliefs:basis.my_personal_reliefs,
        eligibility_verified:basis.my_eligibility, separate_assessment_verified:basis.my_separate};
      for (const key of Object.keys(basis)) if (key.startsWith('my_')) delete basis[key];
    }
    if (policy.id==='vn_business_2026') basis=vietnamBusinessBasis(basis,current.income_tax!);
    if (policy.id==='vn_property_rental_2026') basis=vietnamRentalBasis(basis,current.income_tax!);
    if (policy.id==='vn_personal_transfer_2026') {
      basis.transfers=current.income_tax!.incomes.map((_item,n)=>{
        const prefix=`transfer_${n}_`, method=values[prefix+'method'];
        const line: Record<string,unknown>={income_index:n,asset_kind:method==='security'?'security':'capital_interest',cost_basis_established:method==='capital_known'};
        for(const key of ['recognition_date','purchase_cost','transfer_costs','prepaid_tax','ordinary_sale_confirmed','classification_valuation_and_scope_verified']) line[key]=basis[prefix+key];
        return line;
      });
      for(const key of Object.keys(basis)) if(key.startsWith('transfer_')) delete basis[key];
    }
    if(policy.id==='kr_company_ordinary_2026') {
      try {basis=koreaBasis(basis);} catch {setError(say('地方申报单位名称须非空且不能重复。','Local filing names must be nonempty and unique.'));return;}
    }
    if(policy.id==='kr_salary_standard_payroll_2026')basis=koreaSalaryBasis(basis);
    if(policy.id==='th_dividend_2026') {
      try {basis=thaiDividendBasis(basis,current.income_tax!);} catch {setError(say('请核对股息分笔数（每项1至100笔，合计不超过1000笔）。','Check dividend tranche counts (1–100 per income, at most1000 total).'));return;}
    }
    if(policy.id==='th_foreign_income_2026') {
      try {basis=thaiForeignBasis(basis,current.income_tax!);} catch {setError(say('请核对批次编号不可重复、各笔数为1至100，汇入总笔数不超过1000。','Check unique pool IDs, counts from1 to100 and at most1000 total remittances.'));return;}
    }
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
    <p>{say('按所选税制计算已核对的计税基础。结果保留原始资料和依据，尚不代表完成申报或专业审核；取整处理以所选税制说明为准。','Calculate a checked tax basis under the selected regime. The result retains the facts and sources. It is not a completed return or professional approval; rounding follows the selected regime’s stated treatment.')}</p>
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
          {policy.id==='my_individual_2026' && current.income_tax.residency==='resident' && <p>{say('居民核对表：已保存的扣除总额须等于各来源费用扣除、资本免税额、总所得扣除及个人减免之和（不含以前年度亏损）。总所得扣除须先按法定顺序及限额核定；未使用余额不代表已获准结转。','Resident workpaper: saved claimed deductions must equal source deductions, statutory allowances, total-income deductions and personal reliefs, excluding prior losses. Establish total-income deductions in statutory order and within their limits first. Unused balances do not establish carryforward entitlement.')}</p>}
          <div className="facts-field-grid">{policy.fields.filter(field=>!field.showWhen || values[field.showWhen[0]]===field.showWhen[1]).map(field=><label key={field.key}>{field.label[index]}
            {field.boolean || field.options ? <select required value={values[field.key] || ''} onChange={e=>edit(field.key,e.target.value)}>
              <option value="">{say('待确认','Not confirmed')}</option>
              {field.boolean ? <><option value="true">{say('是','Yes')}</option><option value="false">{say('否','No')}</option></> : field.options!.map(([value,label])=><option key={value} value={value}>{label[index]}</option>)}
            </select> : <input required type={field.date ? 'date' : field.monthsList || field.text ? 'text' : 'number'} min={field.date ? field.dateMin ?? '2026-07-01' : field.min ?? 0} max={field.date ? '2026-12-31' : field.max} step={field.integer ? '1' : 'any'} value={values[field.key] || ''} onChange={e=>edit(field.key,e.target.value)} />}
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
      {result.result.policy_version==='vn-resident-business-2026-2026-11-18'&&<VietnamBusinessResult result={result.result} index={index} />}
      {result.result.policy_version==='vn-resident-property-rental-2026-2026-11-18'&&<VietnamRentalResult result={result.result} index={index} />}
      {result.result.stage==='resident_foreign_income_assessment_before_rounding'&&<ThailandForeignResult result={result.result} index={index} />}
      {result.result.tax_scope==='ordinary_national_and_local_corporate_income_tax'&&<KoreaCompanyResult result={result.result} index={index} />}
      {result.result.tax_scope==='ordinary_salary_employer_national_and_local_settlement'&&<KoreaSalaryResult result={result.result} index={index} />}
      {result.result.regime==='company_normal'&&<p>{say('印度普通企业税制：已比较普通税与14% MAT，采用','India ordinary company regime: compared normal tax with 14% MAT; applied ')}{result.result.mat_applies?say('MAT。','MAT.'):say('普通税。','normal tax.')}{say(' 本期不使用历史MAT抵免，也不新增MAT抵免；账面利润调整须已核定。',' No legacy MAT credit used or new MAT credit generated; book-profit adjustments must be established.')}</p>}
      {result.result.regime==='personal_old_resident'&&<p>{say('印度居民个人旧税制；本税年最高年龄档：','India resident old regime; highest tax-year age band: ')}{result.result.resident_age_band==='under60'?say('未满60岁','Under 60'):result.result.resident_age_band==='60_to79'?say('60至79岁','60 to 79'):say('80岁及以上','80 or above')}{say('。本结果以有效税制选择、不适用AMT且无AMT结转抵免为前提。','; requires a valid election, AMT non-applicability and no carried AMT credit.')}</p>}
      {result.result.tax_scope==='india_ordinary_settlement_ty2026_27'&&<p>{say('印度TY 2026–27（2026年4月至2027年3月），不是AY 2026–27。本次补退额使用已核验的本期已缴款及累计利息、费用；利息和费用并非系统按日期自动核算。负数表示预计应退，不代表已获批准。不含退税利息、先前退税调整、更新申报、罚款、额外追缴或跨年度抵扣。','India TY 2026–27 (April 2026–March 2027), not AY 2026–27. Return balance uses verified period payments and cumulative interest/fees; interest and fees are not automatically computed from dates. A negative balance is a calculated refund, not approval. Excludes refund interest, prior-refund adjustments, updated returns, penalties, additional demands and cross-year offsets.')}</p>}
      {result.result.tax_scope==='india_ordinary_annual_ty2026_27'&&<p>{say('印度TY 2026–27（2026年4月至2027年3月），不是AY 2026–27。此结果为普通所得年度税额，尚未扣除已缴款，也不含利息或罚款；不含特殊税率所得、境外所得或其他税额调整。','India TY 2026–27 (April 2026–March 2027), not AY 2026–27. Ordinary annual liability before payment credits, interest and penalties; excludes special-rate income, foreign income and other tax adjustments.')}</p>}
      {result.result.tax_scope==='japan_three_national_company_taxes_only'&&<>
        <p>{say('此结果仅包含日本企业的三项国税，不含地方住民税、事业税或最低补足税。中间申告应纳义务不代表已缴清；各税种补退分别处理，不能自动互抵。','This result covers the three Japanese national company taxes only, excluding prefectural/municipal inhabitant, enterprise and minimum top-up taxes. Interim-return liabilities do not mean payment; settle each tax separately without automatic offsets.')}</p>
        <p>{say('防卫特别法人税申报：','Defence tax return: ')}{result.result.defence_return_required?say('需要，包括零税额申报。','Required, including zero-tax returns.'):say('本会计年度开始日尚不适用。','Not applicable for this accounting-period start date.')}</p>
      </>}
      {result.result.tax_scope==='national_income_and_reconstruction_tax_only'&&<p>{say('此结果仅为日本2026年度国家所得税及复兴特别所得税，不含住民税、事业税。扣除予定纳税通知金额不代表该税款已缴清，欠税另行处理。','This result covers Japan 2026 national income and reconstruction tax only, excluding local inhabitant and enterprise taxes. Deducting notified estimated tax does not mean it has been paid; arrears remain separate.')}</p>}
      <dl>{Object.entries(resultLabels).filter(([key])=>result.result[key]!==undefined).map(([key,label])=><div key={key}><dt>{key==='balance_due'&&result.result.tax_scope==='national_income_and_reconstruction_tax_only'?say('本次国家税应补／退额（予定纳税欠税另计）','National return balance (estimated-tax arrears separate)'):label[index]}</dt><dd>{String(result.result[key])}</dd></div>)}</dl>
      {Array.isArray(result.result.transfers) && <section aria-label={say('逐笔交易结果','Per-transfer results')}>
        <h5>{say('逐笔交易结果','Per-transfer results')}</h5>
        {(result.result.transfers as Record<string,unknown>[]).map(item=><section key={String(item.income_index)} aria-label={`${say('交易','Transfer')} ${Number(item.income_index)+1}`}>
          <h6>{say('交易','Transfer')} {Number(item.income_index)+1}</h6>
          <p>{say('收入确认日期：','Recognition date: ')}{String(item.recognition_date)}</p>
          <p>{say('计税方式：','Method: ')}{item.method==='capital_gain' ? say('资本净收益','Net capital gain') : item.method==='securities_proceeds' ? say('证券转让价款','Securities proceeds') : say('成本无法确定的资本转让价款','Capital proceeds with unestablished costs')}</p>
          <dl>{([
            ['transfer_value',say('转让价款','Transfer proceeds')],['taxable_base',say('计税基础','Tax base')],
            ['rate',say('适用税率（小数）','Tax rate (fraction)')],['final_tax',say('交易税额','Transaction tax')],
            ['prepaid_tax',say('此笔预缴','Transaction prepayment')],['balance_due',say('此笔应补／退差额','Transaction balance')]
          ] as [string,string][]).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String(item[key])}</dd></div>)}</dl>
        </section>)}
      </section>}
      {!!result.result.reconciliation && <section aria-label={say('计税基础核对','Tax basis reconciliation')}>
        <h5>{say('计税基础核对','Tax basis reconciliation')}</h5>
        <dl>{[
          ['aggregate_income',say('合计所得','Aggregate income')],
          ['prior_losses_used',say('已抵扣以前年度经营亏损','Prior business losses used')],
          ['prior_losses_unused',say('尚未使用的以前年度亏损','Unused prior business losses')],
          ['current_losses_used',say('已抵扣当期亏损','Current losses used')],
          ['total_income',say('总所得','Total income')],
          ['chargeable_income',say('应课税收入','Chargeable income')],
        ].map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String((result.result.reconciliation as Record<string,unknown>)[key])}</dd></div>)}</dl>
      </section>}
      <p>{say('适用规则版本：','Policy version: ')}{String(result.result.policy_version)}</p>
      <p>{say('官方依据：','Official sources:')}</p>
      <ul>{((result.result.sources || (result.result.source ? [result.result.source] : [])) as {url:string;title?:string;doc_id?:string;sha256?:string}[]).map(source=><li key={source.sha256 || source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.title || source.doc_id || say('官方原文','Official original')}</a></li>)}</ul>
    </article>}
  </section>;
}
