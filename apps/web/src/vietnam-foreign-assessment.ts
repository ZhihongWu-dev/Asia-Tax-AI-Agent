import type {BasisField, IncomePolicy} from './income-assessment';
import type {IncomeTaxInput} from './income-tax';

const checks = [
 ['vietnam_establishment_ordinary20_and_full_calendar_periods_verified','已核实越南设立、普通20%税率及完整历年期间','Vietnam establishment, ordinary 20% rate and full calendar periods verified'],
 ['statutory_revenue_and_no_exemptions_incentives_or_losses_verified','已核实法定收入，无免税、优惠或亏损','Statutory revenue verified; no exemptions, incentives or losses'],
 ['source_basis_expenses_and_no_foreign_tax_deduction_verified','已核实来源所得及费用，未重复扣除境外税','Source income and expenses verified; no foreign tax expense deduction'],
 ['treaty_source_entitlement_mli_payment_fx_and_filing_verified','已核实协定资格、多边公约、税款凭证、汇率及申报要求','Treaty entitlement, MLI, payment evidence, FX and filings verified'],
 ['no_other_sparing_underlying_topup_or_special_tax_claims_verified','无其他饶让、间接抵免、补足税或特殊税额申报','No other sparing, underlying credits, top-up or special tax claims'],
] as const;

export function vietnamForeignPolicy(input:IncomeTaxInput):IncomePolicy {
 const fields:BasisField[]=[
  {key:'previous_full_year_statutory_revenue',label:['上年完整法定收入（须超过500亿越南盾）','Prior full-year statutory revenue (over VND 50bn)']},
  {key:'current_full_year_statutory_revenue',label:['本年完整法定收入（须超过100亿越南盾）','Current full-year statutory revenue (over VND 10bn)']},
  {key:'prepaid_tax',label:['本期境内预缴税款','Domestic prepaid tax for this period']},
 ];
 input.incomes.forEach((item,n)=>{
  fields.push({key:`vnfc_${n}_expenses`,label:[`收入${n+1}：核定可扣费用`,`Income ${n+1}: verified allowable expenses`]});
  if(item.source_jurisdiction!=='vn')fields.push({key:`vnfc_${n}_eligible`,label:[`收入${n+1}：合资格境外实缴税额`,`Income ${n+1}: eligible foreign tax actually paid`]});
 });
 for(const [key,zh,en] of checks)fields.push({key,label:[zh,en],boolean:true});
 return {id:'vn_company_foreign_ordinary20_2026',label:['越南企业境外抵免（普通20%，2026）','Vietnam company foreign credits (ordinary 20%, 2026)'],fields,
  notice:['适用于完整历年、上年收入超过500亿且本年超过100亿越南盾的普通企业。各项收入及费用必须与保存记录一致。限普通经营、利息、租金和特许权使用费；新加坡与印尼特定视同已缴税规则单列。低营业额减税、股息、间接抵免及其他特殊规则另行处理。结果尚未申报取整。',
   'For full-calendar-year ordinary companies with prior revenue over VND 50bn and current revenue over VND 10bn. Receipts and expenses must reconcile to saved facts. Covers ordinary business, interest, rental and royalty income, including specified Singapore and Indonesia deemed-tax rules. Low-revenue relief, dividends, underlying credits and other special rules require separate treatment. Before filing rounding.']};
}

export function vietnamForeignBasis(flat:Record<string,unknown>,input:IncomeTaxInput):Record<string,unknown> {
 const workpaper:Record<string,unknown>={
  previous_full_year_statutory_revenue:flat.previous_full_year_statutory_revenue,
  current_full_year_statutory_revenue:flat.current_full_year_statutory_revenue,
  groups:input.incomes.map((item,n)=>({source_id:`income_${n+1}`,income_indexes:[n],
   allowable_expenses:flat[`vnfc_${n}_expenses`],eligible_foreign_tax_paid:item.source_jurisdiction==='vn'?'0':flat[`vnfc_${n}_eligible`]})),
 };
 for(const [key] of checks)workpaper[key]=flat[key];
 return {policy:flat.policy,basis_confirmed:flat.basis_confirmed,basis_explanation:flat.basis_explanation,prepaid_tax:flat.prepaid_tax,workpaper};
}
