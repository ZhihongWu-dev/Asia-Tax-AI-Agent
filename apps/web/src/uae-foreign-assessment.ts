import type {BasisField,IncomePolicy} from './income-assessment';
import type {IncomeTaxInput} from './income-tax';
const field=(key:string,zh:string,en:string):BasisField=>({key,label:[zh,en]});
const check=(key:string,zh:string,en:string):BasisField=>({...field(key,zh,en),boolean:true});
const group=(values:Record<string,string>,n:number)=>values[`afc_group_${n}`]||String(n+1);
export function uaeForeignPolicy(input:IncomeTaxInput,values:Record<string,string>):IncomePolicy{
 const fields:BasisField[]=[];
 input.incomes.forEach((item,n)=>fields.push({key:`afc_group_${n}`,label:[`收入${n+1}：所得来源组`,`Income ${n+1}: source group`],options:input.incomes.map((other,j)=>({other,j})).filter(({other})=>other.category===item.category&&other.source_jurisdiction===item.source_jurisdiction).map(({j}):[string,[string,string]]=>[String(j+1),[`来源${j+1}`,`Source ${j+1}`]])}));
 for(const id of new Set(input.incomes.map((_,n)=>group(values,n)))){
  for(const [key,zh,en] of [['taxable_additions','应税调增','Taxable additions'],['linked_deductions','经济关联费用','Economically linked deductions'],['exempt_income','已计入收入的免税部分','Exempt income included in saved gross'],['eligible_foreign_tax','合资格境外税款','Eligible foreign tax']])fields.push(field(`afc_${id}_${key}`,`来源${id}：${zh}`,`Source ${id}: ${en}`));
  fields.push(check(`afc_${id}_verified`,`来源${id}：已核实所得处理及抵免资格`,`Source ${id}: treatment and credit eligibility verified`));
 }
 fields.push(field('prepaid_tax','本期预缴税款','Prepaid tax for this period'),check('afc_ordinary','已核实普通居民企业且无减免选择或结转亏损','Ordinary resident company without relief elections or carried losses verified'),check('afc_distinct','已核实独立来源及关联费用','Distinct sources and linked expenses verified'),check('afc_eligible','已核实税款资格、条约限额及汇率','Foreign tax eligibility, treaty limits and FX verified'));
 return {id:'ae_company_foreign_direct_2026',label:['阿联酋企业逐项境外抵免（2026）','UAE company income-by-income foreign credit (2026)'],notice:['同一来源分批收款可归入同组；不同所得来源不得互抵超额境外税款。已保存扣除总额须等于各组关联费用。免税和应税境外收入请分开。仅普通独立居民企业及非负来源所得，不含自由区、最低补足税、税务集团、亏损或减免选择。未用境外税款不可结转，也不可作为费用再次扣除。','Group split receipts from the same source together. Excess foreign tax cannot offset a different source. Saved deductions must equal linked group expenses. Separate exempt and taxable foreign receipts. Ordinary standalone resident companies and nonnegative sources only; excludes free-zone, minimum top-up, tax-group, loss and relief-election regimes. Unused foreign tax cannot carry forward/back or be deducted as an expense.'],fields};
}
export function uaeForeignBasis(basis:Record<string,unknown>,input:IncomeTaxInput,values:Record<string,string>){
 const groups=new Map<string,number[]>();
 input.incomes.forEach((_,n)=>{const id=group(values,n);groups.set(id,[...(groups.get(id)||[]),n]);});
 basis.workpaper={groups:[...groups].map(([id,indexes])=>({source_id:`source_${id}`,income_indexes:indexes,
  taxable_additions:basis[`afc_${id}_taxable_additions`],linked_deductions:basis[`afc_${id}_linked_deductions`],exempt_income:basis[`afc_${id}_exempt_income`],eligible_foreign_tax:basis[`afc_${id}_eligible_foreign_tax`],source_treatment_and_eligibility_verified:basis[`afc_${id}_verified`]})),
  ordinary_resident_company_no_reliefs_verified:basis.afc_ordinary,distinct_sources_and_linked_expenses_verified:basis.afc_distinct,foreign_tax_eligibility_treaty_and_fx_verified:basis.afc_eligible};
 for(const key of Object.keys(basis))if(key.startsWith('afc_'))delete basis[key];
 return basis;
}
