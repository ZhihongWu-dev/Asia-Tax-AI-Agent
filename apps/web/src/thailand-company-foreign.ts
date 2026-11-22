import type {BasisField} from './income-assessment';
import type {IncomeTaxInput} from './income-tax';
const field=(key:string,zh:string,en:string):BasisField=>({key,label:[zh,en]});
const check=(key:string,zh:string,en:string):BasisField=>({...field(key,zh,en),boolean:true});
const countries=(input:IncomeTaxInput)=>[...new Set(input.incomes.map(i=>i.source_jurisdiction).filter(c=>c!=='th'))];
export function thaiCompanyForeignFields(input:IncomeTaxInput,values:Record<string,string>):BasisField[]{
 if(input.residency!=='resident'||!countries(input).length)return [];
 const fields=[check('thfc_enabled','使用第300号法令逐国核对境外抵免与费用','Reconcile foreign credits and expenses by country under RD300')];
 if(values.thfc_enabled!=='true')return fields;
 fields.push(field('thfc_domestic_expenses','境内可扣费用','Domestic allowable expenses'));
 for(const country of countries(input)){
  const prefix=`thfc_${country}_`, name=country.toUpperCase();
  fields.push({key:prefix+'treatment',label:[`${name}：境外所得处理`,`${name}: foreign income treatment`],options:[
   ['business_net',['境外经营净所得','Foreign business net income']],
   ['company_receipts',['外国公司付款收入','Receipts from foreign companies']],
   ['mixed_combined',['同国两类所得合并按净所得','Same-country mixed income combined on net basis']],
   ['mixed_separate',['同国两类所得符合条件分别计算','Same-country mixed income qualifying for separate calculation']]]});
  const method=values[prefix+'treatment']||'company_receipts';
  if(method!=='company_receipts')for(const [key,zh,en] of [
   ['business_revenue','境外经营收入','Foreign business revenue'],
   ['business_allowable_expenses','经营可扣费用（含核定可扣境外税）','Business allowable expenses including verified deductible foreign tax'],
   ['business_foreign_tax_paid','经营所得已缴境外税','Foreign tax paid on business income']])fields.push(field(prefix+key,`${name}：${zh}`,`${name}: ${en}`));
  if(method!=='business_net')for(const [key,zh,en] of [
   ['company_receipts','外国公司付款收入总额','Gross receipts from foreign companies'],
   ['company_receipt_foreign_tax_paid','外国公司付款已缴境外税','Foreign tax paid on company receipts']])fields.push(field(prefix+key,`${name}：${zh}`,`${name}: ${en}`));
  if(method==='mixed_combined')fields.push(field(prefix+'company_receipt_allowable_expenses',`${name}：外国公司付款相关可扣费用`,`${name}: allowable expenses for company receipts`));
  if(method==='mixed_separate')fields.push(check(prefix+'separate',`${name}：已核实付款收入单独完税且不再并入境外年度税基`,`${name}: separately taxed receipts excluded from foreign annual tax verified`));
  fields.push(field(prefix+'annual_expenses',`${name}：年度可扣费用合计`,`${name}: total annual allowable expenses`),
   field(prefix+'deducted_tax',`${name}：年度费用中包含的境外税款`,`${name}: foreign tax included in annual expenses`));
 }
 fields.push(check('thfc_election','已核实泰国设立资格及第300号法令适用选择','Thai incorporation and RD300 election verified'),
  check('thfc_expenses','已核实最终费用口径及境外税款扣除资格','Final expense bases and foreign tax deduction eligibility verified'),
  check('thfc_evidence','已核实来源、期间、汇率及税局认证的缴税凭证','Source, period, FX and tax-authority-certified payment evidence verified'));
 return fields;
}
export function thaiCompanyForeignBasis(basis:Record<string,unknown>,input:IncomeTaxInput){
 if(basis.thfc_enabled===true){
  basis.rd300_workpaper={domestic_allowable_expenses:basis.thfc_domestic_expenses,
   thai_incorporation_and_rd300_election_verified:basis.thfc_election,
   final_expense_bases_and_foreign_tax_deductions_verified:basis.thfc_expenses,
   source_period_fx_and_certified_payment_evidence_verified:basis.thfc_evidence,
   countries:countries(input).map(country=>{
    const prefix=`thfc_${country}_`, treatment=basis[prefix+'treatment'];
    const row:Record<string,unknown>={country,treatment,separate_receipts_excluded_from_foreign_annual_tax_verified:treatment==='mixed_separate'&&basis[prefix+'separate']===true};
    for(const key of ['business_revenue','business_allowable_expenses','company_receipts','company_receipt_allowable_expenses','business_foreign_tax_paid','company_receipt_foreign_tax_paid'])row[key]=basis[prefix+key]??'0';
    return {basis:row,annual_allowable_expenses:basis[prefix+'annual_expenses'],foreign_tax_in_annual_expenses:basis[prefix+'deducted_tax']};
   })};
 }
 for(const key of Object.keys(basis))if(key.startsWith('thfc_'))delete basis[key];
 return basis;
}
