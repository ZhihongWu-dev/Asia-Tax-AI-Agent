import {uaeForeignBasis} from '../uae-foreign-assessment';
import {malaysiaForeignBasis} from '../malaysia-foreign-assessment';
import {indonesiaForeignBasis} from '../indonesia-foreign-assessment';
import {indiaForeignBasis} from '../india-foreign-assessment';
import {thaiCompanyForeignBasis} from '../thailand-company-foreign';
import IndonesiaForeignResult from './IndonesiaForeignResult';
import IndiaForeignResult from './IndiaForeignResult';
import ThaiCompanyForeignResult from './ThaiCompanyForeignResult';
import MalaysiaForeignResult from './MalaysiaForeignResult';
import UAEForeignResult from './UAEForeignResult';
import SingaporeForeignResult from './SingaporeForeignResult';
import {singaporeForeignBasis} from '../singapore-foreign-assessment';
import {personalForeignBasis} from '../china-personal-foreign-assessment';
import PersonalForeignResult from './PersonalForeignResult';
import { chinaForeignBasis } from '../china-foreign-assessment';
import ChinaForeignResult from './ChinaForeignResult';
import { osakaBasis } from '../japan-osaka-assessment';
import OsakaLocalResult from './OsakaLocalResult';
import { tokyoBasis } from '../japan-tokyo-assessment';
import TokyoLocalResult from './TokyoLocalResult';
import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';
import { useLocale } from '../locale';
import type { Case } from '../workspace';
import { policies, resultLabels } from '../income-assessment';
import { koreaBasis } from '../korea-assessment';
import KoreaCompanyResult from './KoreaCompanyResult';
import {koreaForeignBasis,koreaForeignHistoryBasis,koreaForeignBalancesBasis} from '../korea-foreign-assessment';
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
  const [downloading,setDownloading] = useState(false), [downloadError,setDownloadError] = useState('');
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
    if(policy.id==='ae_company_foreign_direct_2026')basis=uaeForeignBasis(basis,current.income_tax!,values);
    if(policy.id==='my_company_foreign_direct_ya2026')basis=malaysiaForeignBasis(basis,current.income_tax!,values);
    if(policy.id==='id_company_foreign_direct_2026')basis=indonesiaForeignBasis(basis,current.income_tax!,values);
    if(policy.id==='in_company_foreign_ty2026_27')basis=indiaForeignBasis(basis,current.income_tax!,values);
    if(policy.id==='th_company_2026')basis=thaiCompanyForeignBasis(basis,current.income_tax!);
    if(policy.id==='sg_company_foreign_direct_ya2026')basis=singaporeForeignBasis(basis,current.income_tax!,values);
    if(policy.id==='cn_personal_foreign_2026'){
      try{basis=personalForeignBasis(basis,current.income_tax!,values);}catch{setError(say('历史抵免国家不得重复或与现有来源国家重复。','Prior-credit countries must be unique and additional to saved source countries.'));return;}
    }
    if(policy.id==='cn_company_foreign_direct_2026'){
      try{basis=chinaForeignBasis(basis,current.income_tax!,values);}catch{setError(say('历史抵免国家不得重复或与现有来源国家重复。','Prior-credit countries must be unique and additional to saved source countries.'));return;}
    }
    if (policy.id==='jp_company_starting_2026') {
      try {basis=osakaBasis(tokyoBasis(basis,values,explanation),values,explanation);} catch {setError(values.jpo_enabled==='true'?say('请核对大阪行政区数量和不重复区名。','Check Osaka ward count and unique ward names.'):say('请核对区数量、主办公地点和不重复区名。','Check ward count, one principal office and unique ward names.'));return;}
    }
    if (policy.id==='hk_salaries_2025_26') {
      basis.workpaper={balancing_charge:basis.hks_balancing_charge,employment_expenses:basis.hks_employment_expenses,
        machinery_allowances:basis.hks_machinery_allowances,self_education:basis.hks_self_education,
        concessionary_deductions:basis.hks_concessionary_deductions,eligibility_and_salary_loss_verified:basis.hks_eligibility};
      for(const key of Object.keys(basis))if(key.startsWith('hks_'))delete basis[key];
    }
    if (policy.id==='hk_property_2025_26') {
      basis.properties=current.income_tax!.incomes.map((_item,n)=>({income_index:n,
        irrecoverable_rent:basis[`hk_property_${n}_irrecoverable_rent`],
        owner_rates_paid:basis[`hk_property_${n}_owner_rates_paid`]}));
      for (const key of Object.keys(basis)) if (key.startsWith('hk_property_')) delete basis[key];
    }
    if (policy.id==='my_company_2026' || policy.id==='my_individual_2026') {
      basis.workpaper={sources:current.income_tax!.incomes.map((_item,n)=>({
        income_index:n, additions:basis[`my_source_${n}_additions`],
        deductions:basis[`my_source_${n}_deductions`],
        statutory_charges:basis[`my_source_${n}_statutory_charges`],
        statutory_allowances:basis[`my_source_${n}_statutory_allowances`], explanation,
      })), eligible_prior_business_losses:current.income_tax!.carried_losses,
        schedule4_additions:basis.my_schedule4_additions,
        allowed_total_income_deductions:[basis.my_total_deductions],
        eligibility_verified:basis.my_eligibility,
        ...(policy.id==='my_company_2026'?{standalone_ordinary_verified:basis.my_separate}:{allowed_personal_reliefs:current.income_tax!.residency==='nonresident'?'0':basis.my_personal_reliefs,separate_assessment_verified:basis.my_separate})};
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
    if(['kr_company_ordinary_2026','kr_company_foreign_direct_2026','kr_company_foreign_history_2026','kr_company_foreign_balances_2026'].includes(policy.id)) {
      try {basis=policy.id==='kr_company_foreign_balances_2026'?koreaForeignBalancesBasis(basis,current.income_tax!):policy.id==='kr_company_foreign_history_2026'?koreaForeignHistoryBasis(basis,current.income_tax!):policy.id==='kr_company_foreign_direct_2026'?koreaForeignBasis(basis,current.income_tax!):koreaBasis(basis);} catch {setError(say('地方申报单位名称须非空且不能重复。','Local filing names must be nonempty and unique.'));return;}
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
        {policy.id==='th_company_2026'&&values.thfc_enabled==='true'&&<p>{say('逐国核对目前适用普通20%税率、无免税收入及结转亏损的第300号法令路径。请填已核实的最终费用；境内外费用合计须等于保存的扣除额，核定抵免额须与系统分国计算一致。协定路径和小企业另行处理。','Country reconciliation currently covers the RD300 ordinary 20% path without exemptions or carried losses. Enter verified final expenses; domestic and foreign expenses must equal saved deductions, and allowed credits must match the country calculation. Treaty and SME cases require separate treatment.')}</p>}
          {policy.id==='jp_company_starting_2026' && <>
            <button type="button" aria-pressed={values.jpt_enabled==='true'} onClick={()=>{setValues(v=>({...v,jpt_enabled:v.jpt_enabled==='true'?'false':'true',jpo_enabled:'false',jpt_ward_count:v.jpt_ward_count||'1',jpt_principal:v.jpt_principal||'1'}));setConfirmed(false);setError('');}}>{say('附加东京23区地方税评税','Include Tokyo 23-ward local assessment')}</button>
            <button type="button" aria-pressed={values.jpo_enabled==='true'} onClick={()=>{setValues(v=>({...v,jpo_enabled:v.jpo_enabled==='true'?'false':'true',jpt_enabled:'false',jpo_ward_count:v.jpo_ward_count||'1'}));setConfirmed(false);setError('');}}>{say('附加大阪市地方税评税','Include Osaka city local assessment')}</button>
            {values.jpo_enabled==='true'&&<p>{say('仅限全部办公地点全年位于大阪市的普通内国法人。须核实各行政区名称并合并同区员工数；排除外形标准课税、地方税抵免及协定更正减免。事业税调整与旧亏损须独立核实，府、市税款及预缴分别核算。','Ordinary domestic companies with all offices in Osaka city throughout the year only. Verify actual ward names and aggregate employees per ward. Excludes size-based taxation, local credits and treaty-amendment relief. Verify enterprise adjustments and prior losses independently; prefectural and city liabilities and interim amounts remain separate.')}</p>}
            {values.jpt_enabled==='true'&&<p>{say('已附加东京地方税，本次结果将包含此限定场景的地方税。仅限全部办公地点全年位于东京23区的普通内国法人，无外形标准课税、地方税抵免或协定更正减免。逐区合并员工数并指定唯一主办公地点。独立核实事业税调整和旧亏损，资本须核对准备金和法定调整。','Tokyo local tax is included for this scoped assessment. Ordinary domestic companies with all offices in Tokyo 23 wards throughout the year only; no size-based taxation, local credits or treaty-amendment relief. Aggregate employees by ward and identify one principal office. Verify enterprise adjustments and prior losses separately; verify capital reserves and statutory capital adjustments.')}</p>}
          </>}

          {['cn_company_2026','cn_small_company_2026'].includes(policy.id) && <p>{say('企业税基核对：保存的收入须为完成税务口径调整的收入总额，不是会计利润。不征税收入和免税收入须已包含在收入总额中、互不重叠，且不能再次计入扣除。保存的扣除及以前年度亏损须已核定资格、限额和年度。未用亏损不代表已获准结转；税基必须与这些资料计算的余额一致。','Company basis reconciliation: saved income is established statutory total income, not accounting profit. Non-taxable and exempt amounts must already be included, must not overlap, and must not also be claimed as deductions. Verify deduction eligibility, limits and loss vintages. Unused losses do not establish carryforward approval. The tax base must match the balance calculated from these facts.')}</p>}
          {policy.id==='vn_company_2026' && <p>{say('越南企业核对：已保存收入须包含完整法定收入及普通其他所得；减核定费用、免税所得，再抵扣可用以前年度亏损。免税所得不得重复计入扣除。须逐年核实从亏损次年起连续不超过5年的抵扣资格；本期亏损与旧亏损分别记录，不自动批准未来结转。优惠收入门槛仍按完整法定收入判断。特殊活动、境外所得及优惠所得分池另行处理。','Vietnam company reconciliation: saved income includes complete statutory revenue and ordinary other income. Deduct verified expenses and exempt income, then usable prior losses. Do not duplicate exempt income as deductions. Verify each loss vintage within the continuous five-year window starting after the loss year; current and prior losses remain separate without automatic future carryforward approval. Revenue eligibility thresholds still use complete statutory revenue. Special activities, foreign income and incentive-income pools require separate calculations.')}</p>}
          {policy.id==='ae_ordinary_2026' && <p>{say('核对经营税基：收入加税务调增，减免税收入和已核定经营扣除，再抵扣以前年度自有亏损，抵扣上限为抵亏前应税所得的75%。扣除不得包含个人排除收入对应费用或重复包含免税收入、亏损。须先核实亏损年度、资格及所有权延续条件。个人所有应税经营收入应分类为经营；其余收入须已核实符合工资或个人投资法定排除。此核对不计算转入亏损或税务集团。','Reconcile business income plus tax additions, less exempt income and established business deductions. Eligible own prior losses are capped at 75% of income before loss relief. Deductions exclude costs of excluded personal income and must not duplicate exemptions or losses. Verify loss years, eligibility and ownership continuity first. Classify all in-scope personal business receipts as business; other receipts must qualify as statutory wages or personal-investment exclusions. Transferred losses and tax groups require separate calculations.')}</p>}
          {policy.id==='hk_salaries_2025_26' && <p>{say('薪俸核对：已保存工资应为核定应评税入息，另列折旧结余课税。保存的扣除总额须等于受雇费用、机器免税额、个人进修及第4A部扣除之和，不含个人免税额或以前年度亏损。亏损栏只填按第12A条核定可用的薪俸亏损，不能填营业亏损。只有第12(1)(a)、(b)项超额单独记录为本期第12A条超额；进修及其他扣除不能自动结转。','Salaries workpaper: saved wages are established assessable income; enter machinery balancing charges separately. Saved deductions equal employment expenses, machinery allowances, self-education and Part 4A deductions, excluding personal allowances and prior losses. Prior losses must be eligible section12A salary losses, not business losses. Only excess section12(1)(a)/(b) amounts are recorded as current section12A excess; education and other deductions do not automatically carry forward.')}</p>}
          {policy.id==='hk_profits_2025_26' && <p>{say('利得税核对：已保存收入加应税调增，减核定剔除和扣除，得到抵亏前应评税利润或经调整亏损；再抵扣核定可用的以前年度亏损。扣除须已完成捐款限额、折旧免税额及来源规则审核，不含会计折旧、不允许费用或已单列的亏损。剔除金额不能重复列入扣除。未用亏损不代表获准结转。','Profits reconciliation: saved income plus taxable additions, less established exclusions and deductions, gives assessable profits or adjusted loss before prior-loss set-off. Then apply verified eligible prior losses. Establish donation limits, statutory allowances and source rules first; saved deductions exclude accounting depreciation, disallowed costs and separately entered losses. Do not duplicate exclusions as deductions. Unused losses do not establish carryforward entitlement.')}</p>}
          {policy.id==='my_company_2026' && <p>{say('公司核对表：逐来源核算调整收入、资本免税额和法定收入。以前年度营业亏损只能抵扣营业法定收入，本年营业亏损在汇总所得后扣除。保存的扣除总额须等于来源扣除、资本免税额和按法定顺序核定的总所得扣除，不含以前年度亏损。须先核实亏损期限、股权条件、捐款及其他限额；本表不计算境外收入、集团减免或优惠所得。','Company workpaper: reconcile adjusted income, capital allowances and statutory income by source. Prior business losses reduce business statutory income only; current business losses follow aggregation. Saved deductions must equal source deductions, statutory allowances and established total-income deductions, excluding prior losses. Verify loss vintages, ownership conditions, donation and other limits first. Foreign income, group relief and incentive income need separate calculations.')}</p>}
          {policy.id==='my_individual_2026' && current.income_tax.residency==='nonresident' && <p>{say('非居民普通所得须逐来源核对费用、加回及法定所得；个人减免为零。请核实短期受雇豁免、特殊税率及条约待遇不适用。','Reconcile ordinary nonresident source expenses, additions and statutory income. Personal reliefs are zero. Verify that short-term employment exemptions, special rates and treaty treatment do not apply to this ordinary assessment.')}</p>}
          {policy.id==='my_individual_2026' && current.income_tax.residency==='resident' && <p>{say('居民核对表：已保存的扣除总额须等于各来源费用扣除、资本免税额、总所得扣除及个人减免之和（不含以前年度亏损）。总所得扣除须先按法定顺序及限额核定；未使用余额不代表已获准结转。','Resident workpaper: saved claimed deductions must equal source deductions, statutory allowances, total-income deductions and personal reliefs, excluding prior losses. Establish total-income deductions in statutory order and within their limits first. Unused balances do not establish carryforward entitlement.')}</p>}
          <div className="facts-field-grid">{policy.fields.filter(field=>!field.showWhen || values[field.showWhen[0]]===field.showWhen[1]).map(field=><label key={field.key}>{field.label[index]}
            {field.boolean || field.options ? <select required value={values[field.key] || ''} onChange={e=>edit(field.key,e.target.value)}>
              <option value="">{say('待确认','Not confirmed')}</option>
              {field.boolean ? <><option value="true">{say('是','Yes')}</option><option value="false">{say('否','No')}</option></> : field.options!.map(([value,label])=><option key={value} value={value}>{label[index]}</option>)}
            </select> : <input required type={field.date ? 'date' : field.monthsList || field.text ? 'text' : 'number'} min={field.date ? field.dateMin ?? '2026-07-01' : field.min ?? 0} max={field.date ? field.dateMax ?? '2026-12-31' : field.max} step={field.integer ? '1' : 'any'} value={values[field.key] || ''} onChange={e=>edit(field.key,e.target.value)} />}
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
      <button type="button" disabled={downloading} onClick={async()=>{
        setDownloading(true);setDownloadError('');
        try {
          const report=await api.incomeTaxReport(current.id,result.id,locale);
          if(report.snapshot_hash!==result.snapshot_hash)throw new Error('snapshot mismatch');
          const url=URL.createObjectURL(new Blob([report.markdown],{type:'text/markdown;charset=utf-8'}));
          const link=document.createElement('a');link.href=url;link.download=`income-tax-${result.id}-${locale}.md`;
          link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
        } catch {if(mounted.current)setDownloadError(say('下载未完成，请重试。已保存结果未改变。','Download failed. Please retry; the saved result is unchanged.'));}
        finally {if(mounted.current)setDownloading(false);}
      }}>{downloading?say('正在准备下载…','Preparing download…'):say('下载计算记录','Download calculation record')}</button>
      {downloadError && <p role="alert">{downloadError}</p>}
      {disabled && <p>{say('此结果对应上次保存的资料，不包含当前未保存的修改。','This result uses the last saved facts and excludes unsaved changes.')}</p>}
      <p>{new Date(result.created_at).toLocaleString()} · {String(result.result.currency)}</p>
      {result.result.policy_version==='vn-resident-business-2026-2026-11-18'&&<VietnamBusinessResult result={result.result} index={index} />}
      {result.result.policy_version==='vn-resident-property-rental-2026-2026-11-18'&&<VietnamRentalResult result={result.result} index={index} />}
      {result.result.stage==='resident_foreign_income_assessment_before_rounding'&&<ThailandForeignResult result={result.result} index={index} />}
      {['ordinary_national_and_local_corporate_income_tax','current_direct_foreign_credit_national_and_local_corporate_income_tax'].includes(String(result.result.tax_scope))&&<KoreaCompanyResult result={result.result} index={index} />}
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
      {result.result.policy_version==='ae-ordinary-foreign-credit-20261122'&&<UAEForeignResult result={result.result} index={index}/>}
      {result.result.policy_version==='my-schedule7-direct-credit-20261122'&&<MalaysiaForeignResult result={result.result} index={index}/>}
      {result.result.policy_version==='id-article24-credit-20261122'&&<IndonesiaForeignResult result={result.result} index={index}/>}
      {['in-company-foreign-ty2026-27-20261122','in-company-foreign-ty2026-27-20261122-treaty-scope'].includes(String(result.result.policy_version))&&<IndiaForeignResult result={result.result} index={index}/>}
      {result.result.foreign_credit_reconciliation&&String(result.result.policy_version).includes('rd300')?<ThaiCompanyForeignResult result={result.result} index={index}/>:null}
      {result.result.policy_version==='sg-company-foreign-direct-ya2026-20261122'&&<SingaporeForeignResult result={result.result} index={index}/>}
      {result.result.tax_scope==='china_resident_ordinary_direct_foreign_credit_positive_bases'&&<ChinaForeignResult result={result.result} index={index}/>}
      {result.result.tax_scope==='china_resident_ordinary_comprehensive_business_investment_foreign_credit'&&<PersonalForeignResult result={result.result} index={index}/>}
      {!!result.result.osaka_local && <OsakaLocalResult result={result.result} index={index} />}
      {!!result.result.tokyo_local && <TokyoLocalResult result={result.result} index={index} />}
      {!!result.result.personal_basis_reconciliation && <section aria-label={say('印尼个人所得税税基核对','Indonesia personal basis reconciliation')}>
        <h4>{say('印尼个人所得税税基核对','Indonesia personal basis reconciliation')}</h4>
        <dl>{([
          ['saved_gross_income',say('已保存收入','Saved income')],
          ['verified_deductions',say('核定扣除（不含PTKP）','Verified deductions excluding PTKP')],
          ['income_after_deductions',say('扣除后所得','Income after deductions')],
          ['eligible_prior_losses',say('核定可用以前年度亏损','Verified eligible prior losses')],
          ['prior_losses_used',say('本期使用以前年度亏损','Prior losses used')],
          ['prior_losses_unused',say('未使用以前年度亏损','Prior losses unused')],
          ['net_income_before_ptkp',say('PTKP前净所得','Net income before PTKP')],
        ] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String((result.result.personal_basis_reconciliation as Record<string,unknown>)[key])}</dd></div>)}</dl>
      </section>}
      {!!result.result.employment_reconciliation && <section aria-label={say('越南工资薪金核对','Vietnam employment reconciliation')}>
        <h4>{say('越南工资薪金核对','Vietnam employment reconciliation')}</h4>
        <dl>{([
          ['saved_gross_income',say('已保存工资总额','Saved gross employment income')],
          ['exempt_employment_income',say('核定免税工资','Verified exempt employment income')],
          ['chargeable_employment_income',say('个人扣除前应税工资','Chargeable pay before personal deductions')],
          ['saved_claimed_deductions',say('已保存扣除总额','Saved claimed deductions')],
          ['reconciled_total_deductions',say('核对后扣除总额','Reconciled total deductions')],
          ['taxable_income',say('扣除后应税所得','Taxable income after deductions')],
        ] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String((result.result.employment_reconciliation as Record<string,unknown>)[key])}</dd></div>)}</dl>
      </section>}
      {!!result.result.salary_reconciliation && <section aria-label={say('香港薪俸税核对','Hong Kong salaries reconciliation')}>
        <h5>{say('香港薪俸税核对','Hong Kong salaries reconciliation')}</h5>
        <dl>{([
          ['saved_assessable_income',say('已保存应评税入息','Saved assessable income')],
          ['balancing_charge',say('结余课税','Balancing charge')],
          ['employment_expenses',say('受雇费用','Employment expenses')],
          ['machinery_allowances',say('机器免税额','Machinery allowances')],
          ['current_section12a_excess',say('本期第12A条超额（非结转批准）','Current section12A excess (not carryforward approval)')],
          ['prior_salary_losses_used',say('已用以前年度薪俸亏损','Prior salary losses used')],
          ['prior_salary_losses_unused',say('未用以前年度薪俸亏损','Unused prior salary losses')],
          ['self_education',say('个人进修扣除','Self-education deduction')],
          ['concessionary_deductions',say('第4A部扣除','Part 4A deductions')],
          ['net_income_before_allowances',say('免税额前入息净额','Net income before allowances')],
        ] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String((result.result.salary_reconciliation as Record<string,unknown>)[key])}</dd></div>)}</dl>
      </section>}
      {!!result.result.uae_basis_reconciliation && <section aria-label={say('阿联酋企业税税基核对','UAE corporate tax basis reconciliation')}>
        <h5>{say('阿联酋企业税税基核对','UAE corporate tax basis reconciliation')}</h5>
        <dl>{([
          ['in_scope_income',say('适用经营收入','In-scope business income')],
          ['excluded_personal_income',say('已核实排除的个人收入','Verified excluded personal income')],
          ['taxable_additions',say('应税调增','Taxable additions')],
          ['exempt_income',say('免税收入','Exempt income')],
          ['allowed_deductions',say('核定经营扣除','Established business deductions')],
          ['income_before_loss_relief',say('抵亏前所得','Income before loss relief')],
          ['current_period_loss',say('本期亏损','Current-period loss')],
          ['prior_loss_limit',say('以前年度亏损抵扣上限（75%）','Prior-loss ceiling (75%)')],
          ['prior_losses_used',say('实际抵扣以前年度亏损','Prior losses used')],
          ['prior_losses_unused',say('未用亏损（非结转批准）','Unused losses (not carryforward approval)')],
          ['taxable_income',say('抵亏后应税所得','Taxable income after loss relief')],
        ] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String((result.result.uae_basis_reconciliation as Record<string,unknown>)[key])}</dd></div>)}</dl>
      </section>}
      {!!result.result.hong_kong_profits_reconciliation && <section aria-label={say('香港利得税税基核对','Hong Kong profits basis reconciliation')}>
        <h5>{say('香港利得税税基核对','Hong Kong profits basis reconciliation')}</h5>
        <dl>{([
          ['saved_receipts',say('已保存收入','Saved income')],
          ['taxable_additions',say('应税调增','Taxable additions')],
          ['excluded_income',say('核定剔除','Established exclusions')],
          ['allowed_deductions',say('核定扣除','Established deductions')],
          ['assessable_profits_before_losses',say('抵亏前应评税利润','Assessable profits before loss relief')],
          ['adjusted_current_loss',say('本期经调整亏损','Current adjusted loss')],
          ['prior_losses_used',say('实际抵扣以前年度亏损','Prior losses used')],
          ['prior_losses_unused',say('未用以前年度亏损（非结转批准）','Unused prior losses (not carryforward approval)')],
          ['net_taxable_profits',say('抵亏后计税净额','Net taxable profits after loss relief')],
        ] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String((result.result.hong_kong_profits_reconciliation as Record<string,unknown>)[key])}</dd></div>)}</dl>
      </section>}
      {!!result.result.singapore_basis_reconciliation && <section aria-label={say('新加坡减免前税基核对','Singapore pre-exemption basis reconciliation')}>
        <h5>{say('新加坡减免前税基核对','Singapore pre-exemption basis reconciliation')}</h5>
        <dl>{([
          ['total_income',say('保存收入总额','Saved total income')],
          ['established_deductions_and_exclusions',say('核定扣除及非应税调整','Established deductions and exclusions')],
          ['established_prior_loss_deduction',say('核定本期以前年度亏损扣除','Established prior-loss deduction')],
          ['net_before_zero_floor',say('核对净额（负数不代表可结转亏损）','Reconciled net amount (negative is not a carryforward award)')],
          ['chargeable_income_before_exemption',say('自动减免前应课税收入','Chargeable income before automatic exemption')],
        ] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String((result.result.singapore_basis_reconciliation as Record<string,unknown>)[key])}</dd></div>)}</dl>
      </section>}
      {!!result.result.basis_reconciliation && <section aria-label={say('企业税基核对','Company basis reconciliation')}>
        <h5>{say('企业税基核对','Company basis reconciliation')}</h5>
        <dl>{([
          ['total_income',say('税务口径收入总额','Statutory total income')],
          ['non_taxable_income',say('不征税收入','Non-taxable income')],
          ['exempt_income',say('免税收入','Exempt income')],
          ['allowed_deductions',say('核定扣除','Established deductions')],
          ['income_before_loss_relief',say('弥补以前年度亏损前所得','Income before prior-loss relief')],
          ['current_period_loss',say('本期亏损','Current-period loss')],
          ['prior_losses_used',say('本期使用以前年度亏损','Prior losses used')],
          ['prior_losses_unused',say('以前年度亏损未使用余额（非结转批准）','Unused prior losses (not carryforward approval)')],
          ['taxable_income',say('核对后应纳税所得额','Reconciled taxable income')],
        ] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String((result.result.basis_reconciliation as Record<string,unknown>)[key])}</dd></div>)}</dl>
      </section>}
      {result.result.stage==='separate_property_before_assessment_rounding' && Array.isArray(result.result.properties) && <section aria-label={say('逐项物业结果','Per-property results')}>
        <h5>{say('逐项物业结果','Per-property results')}</h5>
        {(result.result.properties as Record<string,unknown>[]).map(item=><section key={String(item.income_index)}>
          <h6>{say('物业','Property')} {Number(item.income_index)+1}</h6>
          <dl>{([
            ['gross_consideration',say('租赁总代价','Gross rental consideration')],
            ['irrecoverable_rent',say('不可追回租金','Irrecoverable rent')],
            ['owner_rates_paid',say('业主已付差饷','Owner rates paid')],
            ['statutory_allowance',say('20%法定扣除','20% statutory allowance')],
            ['net_assessable_value',say('应评税净值','Net assessable value')],
            ['property_tax',say('物业税额','Property tax')],
          ] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String(item[key])}</dd></div>)}</dl>
        </section>)}
      </section>}
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
