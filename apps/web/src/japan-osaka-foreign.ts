import type {BasisField,IncomePolicy} from './income-assessment';
import type {IncomeTaxInput} from './income-tax';
import {osakaFields,osakaAmounts,osakaChecks} from './japan-osaka-assessment';

const sourceChecks=[
 ['japanese_source_income_and_expense_allocation_verified','已核实日本来源所得及费用分配','Japanese source income and expense allocation verified'],
 ['foreign_tax_eligibility_high_tax_exclusions_treaty_fx_and_period_verified','已核实境外税资格、高税排除、协定、汇率及期间','Foreign tax eligibility, high-tax exclusions, treaty, FX and period verified'],
 ['foreign_tax_exempt_income_and_no_double_deduction_verified','已核实境外免税所得及无重复扣除','Foreign-exempt income and no double deduction verified'],
 ['no_losses_dividend_exemptions_pe_adjustments_groups_or_special_regimes_verified','无亏损、股息免税、常设机构调整、集团或特殊税制','No losses, dividend exemptions, PE adjustments, groups or special regimes'],
] as const;
const localChecks=[
 ['all_offices_in_osaka_city_full_year_no_foreign_offices_verified','全年全部办公室在大阪市，无境外办公室','All offices in Osaka city throughout the year; no foreign offices'],
 ['ordinary_domestic_entity_and_size_based_exclusion_verified','已核实普通内国法人及2025至2026扩围后的外形标准课税排除','Ordinary domestic entity and expanded 2025–2026 size-based exclusion verified'],
 ['capital_employees_and_enterprise_adjustments_verified','已核实资本、员工及事业税调整','Capital, employees and enterprise adjustments verified'],
 ['standard_local_limits_no_actual_rate_election_verified','已核实采用标准抵免限额，不选择实际税率','Standard local credit limits verified; no actual-rate election'],
 ['no_other_local_credits_additions_history_losses_or_treaty_amendments_verified','无其他地方抵免、加算、历史余额、亏损或协定更正','No other local credits, additions, history, losses or treaty amendments'],
] as const;
const nationalChecks=[
 ['rate_classification_verified','已核实资本、控制关系和法人税率分类','Capital, control and corporation-rate classification verified'],
 ['no_other_tax_credits_additions_or_history_verified','无其他国税抵免、加算或历史余额','No other national credits, additions or historical balances'],
] as const;

export function japanOsakaForeignPolicy(input:IncomeTaxInput,values:Record<string,string>):IncomePolicy {
 const removed=new Set<string>(['jpo_eligible_enterprise_prior_losses',...osakaChecks.map(([key])=>'jpo_'+key)]);
 const fields:BasisField[]=[
  {key:'rate_regime',label:['法人税率分类','Corporation-rate classification'],options:[['ordinary',['普通23.2%','Ordinary 23.2%']],['sme_reduced',['小企业15%／17%','SME 15% / 17%']],['sme_excluded',['适用除外19%','Excluded business 19%']]]},
  ...osakaFields({...values,jpo_enabled:'true'}).filter(f=>!removed.has(f.key)),
  {key:'jpo_corporation_interim_liability',label:['法人税中间申告义务','Corporation interim liability']},
  {key:'jpo_local_corporation_interim_liability',label:['地方法人税中间申告义务','Local corporation interim liability']},
 ];
 input.incomes.forEach((item,n)=>{
  fields.push({key:`jpfc_${n}_expenses`,label:[`收入${n+1}：核定费用`,`Income ${n+1}: verified expenses`]});
  if(item.source_jurisdiction!=='jp')fields.push(
   {key:`jpfc_${n}_exempt`,label:[`收入${n+1}：境外免税净所得`,`Income ${n+1}: foreign-tax-exempt net income`]},
   {key:`jpfc_${n}_eligible`,label:[`收入${n+1}：合资格境外税额`,`Income ${n+1}: eligible foreign tax`]});
 });
 for(const [key,zh,en] of [...sourceChecks,...localChecks,...nationalChecks])fields.push({key,label:[zh,en],boolean:true});
 return {id:'jp_osaka_company_foreign_starting_2026',label:['日本大阪企业境外抵免（2026年开始）','Japan Osaka company foreign credits (starting 2026)'],fields,
  notice:['完整年度、全部办公室在大阪市的普通企业。收入、费用和实缴境外税须与保存记录核对。使用标准地方抵免限额；九项税费补退分别结算。无历史余额、境外办公室、股息、特殊税制或其他抵免。超限额尚不代表准予结转。',
   'Full-year ordinary companies with all offices in Osaka city. Reconcile income, expenses and foreign payments to saved facts. Standard local credit limits; nine tax components settle separately. No historical balances, foreign offices, dividends, special regimes or competing credits. Excess does not establish carryforward entitlement.']};
}

export function japanOsakaForeignBasis(flat:Record<string,unknown>,input:IncomeTaxInput):Record<string,unknown> {
 const count=Number(flat.jpo_ward_count);
 if(!Number.isInteger(count)||count<1||count>24)throw new Error('Invalid ward count');
 const wards=Array.from({length:count},(_,n)=>({ward_name:flat[`jpo_ward_${n}`],employees:flat[`jpo_employees_${n}`]}));
 if(new Set(wards.map(w=>w.ward_name)).size!==count)throw new Error('Duplicate ward');
 const local:Record<string,unknown>={wards,local_adjustments_explanation:flat.basis_explanation};
 for(const [key] of osakaAmounts)if(key!=='eligible_enterprise_prior_losses')local[key]=flat['jpo_'+key];
 for(const key of ['corporation_interim_liability','local_corporation_interim_liability'])local[key]=flat['jpo_'+key];
 for(const [key] of localChecks)local[key]=flat[key];
 const source:Record<string,unknown>={groups:input.incomes.map((item,n)=>({source_id:`income_${n+1}`,income_indexes:[n],
  allowable_expenses:flat[`jpfc_${n}_expenses`],foreign_income_exempt_from_foreign_tax:item.source_jurisdiction==='jp'?'0':flat[`jpfc_${n}_exempt`],
  eligible_foreign_corporate_tax:item.source_jurisdiction==='jp'?'0':flat[`jpfc_${n}_eligible`]}))};
 for(const [key] of sourceChecks)source[key]=flat[key];
 return {policy:flat.policy,basis_confirmed:flat.basis_confirmed,basis_explanation:flat.basis_explanation,
  rate_regime:flat.rate_regime,rate_classification_verified:flat.rate_classification_verified,
  no_other_tax_credits_additions_or_history_verified:flat.no_other_tax_credits_additions_or_history_verified,
  source_workpaper:source,local_workpaper:local};
}
