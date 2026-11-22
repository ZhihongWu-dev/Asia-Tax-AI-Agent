import type {BasisField,IncomePolicy} from './income-assessment';
import type {IncomeTaxInput} from './income-tax';
const field=(key:string,zh:string,en:string):BasisField=>({key,label:[zh,en]});
const group=(values:Record<string,string>,n:number)=>values[`infc_group_${n}`]||String(n+1);
export const indiaForeignChecks=[
 ['domestic_company_regime_and_base_verified','已核实印度内国公司税制及计税基础','Indian domestic company regime and taxable base verified'],
 ['source_attribution_and_expenses_verified','已核实逐来源印度税额和费用','Statutory Indian tax attribution and expenses verified by source'],
 ['tax_year_fx_disputes_and_treaty_limits_verified','已核实税年、汇率、争议税款及协定限额','Tax year, FX, disputed tax and treaty limits verified'],
 ['required_filings_and_accountant_verification_confirmed','已确认所需申报、凭证及会计师验证','Required filings, payment evidence and accountant verification confirmed'],
 ['no_prior_credit_refunds_special_regimes_or_losses_verified','已核实无以前抵免退税调整、特殊税制及亏损','Absence of prior-credit refunds, special regimes and losses verified'],
 ['period_prepayments_verified','已核实本期预缴税款','Period prepayments verified'],
 ['no_legacy_mat_credit_or_other_reliefs_verified','已核实无历史最低税额抵免及其他减免','Absence of legacy MAT credits and other reliefs verified'],
] as const;
export function indiaForeignPolicy(input:IncomeTaxInput,values:Record<string,string>):IncomePolicy{
 const fields:BasisField[]=[{key:'infc_scheme',label:['印度企业税制','Indian company regime'],options:[['section200',['第200条优惠税制','Section200 option']],['normal',['普通税制及最低税额比较','Normal regime with MAT comparison']]]}];
 const normal=values.infc_scheme==='normal';
 if(normal)fields.push(field('infc_turnover','2024—25年度核定营业额','Verified turnover for2024-25'),field('infc_book','核定最低税额账面利润','Verified MAT book profit'));
 input.incomes.forEach((item,n)=>fields.push({key:`infc_group_${n}`,label:[`收入${n+1}：独立来源组`,`Income ${n+1}: separate source group`],options:input.incomes.map((other,j)=>({other,j})).filter(({other})=>other.category===item.category&&other.source_jurisdiction===item.source_jurisdiction).map(({j}):[string,[string,string]]=>[String(j+1),[`来源${j+1}`,`Source ${j+1}`]])}));
 for(const id of new Set(input.incomes.map((_,n)=>group(values,n)))){
  const foreign=input.incomes.find((_,n)=>group(values,n)===id)?.source_jurisdiction!=='in';
  fields.push(field(`infc_${id}_expenses`,`来源${id}：可扣费用`,`Source ${id}: allowable expenses`));
  if(foreign){
   for(const [key,zh,en] of [['paid','境外实缴税（卢比）','foreign tax paid in INR'],['disputed','排除的争议税款（卢比）','disputed tax excluded in INR'],['normal_tax','归属本来源的普通印度税额','normal Indian tax attributable to this source']])fields.push(field(`infc_${id}_${key}`,`来源${id}：${zh}`,`Source ${id}: ${en}`));
   if(normal)fields.push(field(`infc_${id}_mat_tax`,`来源${id}：归属本来源的最低税额`,`Source ${id}: Section206 tax attributable to this source`));
   fields.push({...field(`infc_${id}_treaty`,`来源${id}：适用税收协定`,`Source ${id}: treaty applies`),boolean:true});
   if(values[`infc_${id}_treaty`]==='true')fields.push(field(`infc_${id}_treaty_limit`,`来源${id}：协定允许税额（可为零）`,`Source ${id}: treaty-permitted tax (may be zero)`));
   if(values[`infc_${id}_treaty`]==='false')fields.push(field(`infc_${id}_section160`,`来源${id}：核定第160条平均税率抵免限额`,`Source ${id}: established Section160 average-rate relief limit`));
  }
 }
 fields.push(field('prepaid_tax','本期核定预缴税款','Verified prepayments for this period'));
 for(const [key,zh,en] of indiaForeignChecks)fields.push({...field('infc_'+key,zh,en),boolean:true});
 return {id:'in_company_foreign_ty2026_27',label:['印度企业境外抵免（税年2026—27）','Indian company foreign credits (TY2026-27)'],
  notice:['按独立来源核对保存收入、费用及境外已缴税。来源印度税额须先按普通税制及最低税额规则核定，含附加税及健康教育税，不含利息、费用或罚款；本表不自动推定统一分摊比例。第200条须满足适用选择与扣除限制。无协定时先核定第160条平均税率限额。结果含核定预缴税款，尚未加入利息及费用；不含特殊税制、亏损、历史MAT抵免或以前抵免退税调整。',
   'Reconcile saved income, expenses and foreign tax by separate source. Establish attributable Indian tax under normal and MAT rules, including surcharge and cess but excluding interest, fees and penalties; no universal allocation ratio is inferred. Section200 requires a valid election and compliant deductions. Establish Section160 average-rate limits for non-treaty cases. Results include verified prepayments but precede interest and fees; special regimes, losses, legacy MAT credits and prior-credit refunds are excluded.'],fields};
}
export function indiaForeignBasis(basis:Record<string,unknown>,input:IncomeTaxInput,values:Record<string,string>){
 const groups=new Map<string,number[]>();
 input.incomes.forEach((_,n)=>{const id=group(values,n);groups.set(id,[...(groups.get(id)||[]),n]);});
 const normal=basis.infc_scheme==='normal';
 const paper:Record<string,unknown>={scheme:basis.infc_scheme,turnover_2024_25:normal?basis.infc_turnover:null,mat_book_profit_before_rounding:normal?basis.infc_book:null,
  groups:[...groups].map(([id,indexes])=>{
   const country=input.incomes[indexes[0]].source_jurisdiction, treaty=basis[`infc_${id}_treaty`]===true;
   return {source_id:`source_${id}`,income_indexes:indexes,allowable_expenses:basis[`infc_${id}_expenses`],foreign_credit:country==='in'?null:{
    source_id:`source_${id}`,country,foreign_tax_paid_inr:basis[`infc_${id}_paid`],disputed_tax_excluded_inr:basis[`infc_${id}_disputed`],treaty_applies:treaty,
    treaty_permitted_tax_inr:treaty?basis[`infc_${id}_treaty_limit`]:null,section160_relief_limit_inr:treaty?null:basis[`infc_${id}_section160`],
    normal_indian_tax_attributable:basis[`infc_${id}_normal_tax`],section206_tax_attributable:normal?basis[`infc_${id}_mat_tax`]:null}};
  })};
 for(const [key] of indiaForeignChecks)paper[key]=basis['infc_'+key];
 basis.workpaper=paper;
 for(const key of Object.keys(basis))if(key.startsWith('infc_'))delete basis[key];
 return basis;
}
