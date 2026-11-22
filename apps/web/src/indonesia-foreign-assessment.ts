import type {BasisField,IncomePolicy} from './income-assessment';
import type {IncomeTaxInput} from './income-tax';
const field=(key:string,zh:string,en:string):BasisField=>({key,label:[zh,en]});
const check=(key:string,zh:string,en:string):BasisField=>({...field(key,zh,en),boolean:true});
const group=(values:Record<string,string>,n:number)=>values[`ifc_group_${n}`]||String(n+1);
export function indonesiaForeignPolicy(input:IncomeTaxInput,values:Record<string,string>):IncomePolicy{
 const fields:BasisField[]=[];
 input.incomes.forEach((item,n)=>fields.push({key:`ifc_group_${n}`,label:[`收入${n+1}：来源组`,`Income ${n+1}: source group`],options:input.incomes.map((other,j)=>({other,j})).filter(({other})=>other.category===item.category&&other.source_jurisdiction===item.source_jurisdiction).map(({j}):[string,[string,string]]=>[String(j+1),[`来源${j+1}`,`Source ${j+1}`]])}));
 for(const id of new Set(input.incomes.map((_,n)=>group(values,n)))){
  const foreign=input.incomes.find((_,n)=>group(values,n)===id)?.source_jurisdiction!=='id';
  for(const [key,zh,en] of [['additions','应税调增','Taxable additions'],['allowed_expenses','可扣费用','Allowable expenses'],['exempt_income','免税部分','Exempt income']])fields.push(field(`ifc_${id}_${key}`,`来源${id}：${zh}`,`Source ${id}: ${en}`));
  if(foreign){
   fields.push(field(`ifc_${id}_tax`,`来源${id}：合资格境外税款`,`Source ${id}: creditable foreign tax`),check(`ifc_${id}_treaty`,`来源${id}：适用税收协定`,`Source ${id}: treaty applies`));
   if(values[`ifc_${id}_treaty`]==='true')fields.push(field(`ifc_${id}_ceiling`,`来源${id}：协定允许的境外税额（可为零）`,`Source ${id}: treaty-permitted tax (may be zero)`));
  }
  fields.push(check(`ifc_${id}_verified`,`来源${id}：已核实独立来源及应税处理`,`Source ${id}: separate source and taxable treatment verified`));
 }
 fields.push(field('ifc_recapture','以前已抵免税款退还或减免的补回','Recapture of previously credited tax reduced or refunded'),
  field('prepaid_tax','本期境内预缴税款','Domestic prepaid tax for this period'),
  check('ifc_ordinary','已核实普通居民企业且无最终税制、特殊税制或结转亏损','Ordinary resident company without final/special regimes or carried losses verified'),
  check('ifc_turnover','已核实完整第31E条营业额口径','Complete Article31E gross-receipts scope verified'),
  check('ifc_source','已核实来源、税期、费用与汇率','Source, tax period, expenses and FX verified'),
  check('ifc_treaty','已核实条约资格及税款凭证','Treaty entitlement and foreign-tax evidence verified'),
  check('ifc_recap_verified','已核实以前已抵免税款的补回金额','Recapture of previously credited tax verified'));
 return {id:'id_company_foreign_direct_2026',label:['印尼企业境外抵免（2026）','Indonesia company foreign credits (2026)'],notice:['同一来源的分批收入可归组；独立境外亏损来源须分开，其亏损不冲减其他所得。各组费用之和须等于已保存扣除。第31E条营业额包含已保存境内外收入；免税所得与抵免收入分开。协定仅允许印尼征税时，境外税额上限填零。结果尚未完成申报取整；不含最终税制、特殊税制及结转亏损。','Group split receipts from the same source. Keep independent foreign loss sources separate; their losses do not offset other income. Group expenses must equal saved deductions. Article31E turnover includes saved domestic and foreign receipts. Separate exempt and credit-bearing income. Enter a zero treaty ceiling when only Indonesia may tax the income. Results precede return rounding; excludes final/special regimes and carried losses.'],fields};
}
export function indonesiaForeignBasis(basis:Record<string,unknown>,input:IncomeTaxInput,values:Record<string,string>){
 const groups=new Map<string,number[]>();
 input.incomes.forEach((_,n)=>{const id=group(values,n);groups.set(id,[...(groups.get(id)||[]),n]);});
 basis.workpaper={groups:[...groups].map(([id,indexes])=>{
  const foreign=input.incomes[indexes[0]].source_jurisdiction!=='id';
  return {source_id:`source_${id}`,income_indexes:indexes,additions:basis[`ifc_${id}_additions`],allowed_expenses:basis[`ifc_${id}_allowed_expenses`],exempt_income:basis[`ifc_${id}_exempt_income`],
   creditable_foreign_tax:foreign?basis[`ifc_${id}_tax`]:'0',treaty_applies:foreign?basis[`ifc_${id}_treaty`]:false,
   treaty_permitted_tax:foreign&&basis[`ifc_${id}_treaty`]===true?basis[`ifc_${id}_ceiling`]:null,
   separate_source_and_taxable_treatment_verified:basis[`ifc_${id}_verified`]};}),
  prior_credit_reduction_or_refund:basis.ifc_recapture,ordinary_resident_no_final_special_or_carried_losses_verified:basis.ifc_ordinary,
  complete_article31e_gross_receipts_verified:basis.ifc_turnover,source_period_expenses_and_fx_verified:basis.ifc_source,
  treaty_entitlement_and_tax_evidence_verified:basis.ifc_treaty,recapture_of_previously_credited_tax_verified:basis.ifc_recap_verified};
 for(const key of Object.keys(basis))if(key.startsWith('ifc_'))delete basis[key];
 return basis;
}
