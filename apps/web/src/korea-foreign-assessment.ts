import type {BasisField, IncomePolicy} from './income-assessment';
import type {IncomeTaxInput} from './income-tax';
import {koreaBasis, koreaPolicy} from './korea-assessment';

const checks = [
  ['korean_income_basis_and_expense_classification_verified','已核实韩国计税收入及两类费用归属','Korean income basis and expense classification verified'],
  ['direct_paid_tax_treaty_fx_and_filing_evidence_verified','已核实境外直接实缴税、协定限额、汇率及申报凭证','Direct paid tax, treaty limits, FX and filing evidence verified'],
  ['no_losses_exemptions_special_income_or_other_base_adjustments_verified','已核实无亏损、免税所得、特殊所得或其他税基调整','No losses, exempt/special income or other base adjustments'],
] as const;
const annualChecks = [
  ['current_direct_credit_and_local_deduction_eligibility_verified','已核实本期直接抵免和地方税税基扣除资格','Current direct credit and local deduction eligibility verified'],
  ['no_prior_foreign_balances_other_reliefs_or_separate_taxes_verified','已核实无历史境外余额、其他国税减免或单独税负','No prior foreign balances, competing national reliefs or separate taxes'],
] as const;

export function koreaForeignPolicy(input:IncomeTaxInput, values:Record<string,string>):IncomePolicy {
  const base = koreaPolicy({...values, relief_count:'0'});
  const fields:BasisField[] = base.fields.filter(f=>!['national_taxable_base','local_taxable_base','relief_count','ordinary_domestic_scope_confirmed'].includes(f.key));
  input.incomes.forEach((item,n)=>{
    const foreign=item.source_jurisdiction!=='kr';
    fields.push({key:`krfc_${n}_expenses`,label:[`收入${n+1}：${foreign?'已计入境外所得的':'境内可扣'}费用`,`Income ${n+1}: ${foreign?'expenses already included in foreign income':'allowable domestic expenses'}`]});
    if(foreign)fields.push(
      {key:`krfc_${n}_corresponding`,label:[`收入${n+1}：尚未计入境外所得的对应费用`,`Income ${n+1}: corresponding expenses not already included in foreign income`]},
      {key:`krfc_${n}_eligible`,label:[`收入${n+1}：核定合资格直接境外税`,`Income ${n+1}: verified eligible direct foreign tax`]});
  });
  for(const [key,zh,en] of [...checks,...annualChecks])fields.push({key,label:[zh,en],boolean:true});
  return {id:'kr_company_foreign_direct_2026',label:['韩国企业境外直接抵免（2026）','Korean company direct foreign credits (2026)'],fields,
    notice:['适用于2026完整历年居民企业的普通经营、利息、租金及特许权使用费所得。两类费用合计须与保存扣除一致；境外已缴税来自保存收入，合资格税额不能超出实缴金额。按国家合并计算限额，国税与各地方机关分别结算。地方税税基扣除采用合资格境外税额，不直接复制国税抵免额。当前不含股息、历史结转、其他国税减免、亏损、特殊税负、更正申报或分期缴款。',
      'For resident companies with ordinary business, interest, rental and royalty income in calendar2026. Both expense classes must reconcile to saved deductions. Eligible tax cannot exceed saved foreign tax paid. Limits aggregate by country; national and local authorities settle separately. The local-base deduction uses eligible foreign tax, not the national credit amount. Excludes dividends, prior balances, competing national reliefs, losses, special taxes, amended returns and installments.']};
}

export function koreaForeignBasis(flat:Record<string,unknown>, input:IncomeTaxInput):Record<string,unknown> {
  const base=koreaBasis({...flat, relief_count:0});
  const workpaper:Record<string,unknown>={groups:input.incomes.map((item,n)=>({source_id:`income_${n+1}`,income_indexes:[n],
    expenses_already_in_foreign_income:flat[`krfc_${n}_expenses`],
    corresponding_expenses:item.source_jurisdiction==='kr'?'0':flat[`krfc_${n}_corresponding`],
    eligible_direct_foreign_tax:item.source_jurisdiction==='kr'?'0':flat[`krfc_${n}_eligible`]}))};
  for(const [key] of checks)workpaper[key]=flat[key];
  const result:Record<string,unknown>={policy:flat.policy,basis_confirmed:flat.basis_confirmed,basis_explanation:flat.basis_explanation,
    workpaper,national_inputs:base.national_inputs,local_inputs:base.local_inputs};
  for(const [key] of annualChecks)result[key]=flat[key];
  return result;
}
