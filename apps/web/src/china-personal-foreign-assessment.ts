import type {BasisField,IncomePolicy} from './income-assessment';
import {taxJurisdictions,type IncomeTaxInput,type TaxJurisdiction} from './income-tax';
const count=(v:string|undefined,max:number)=>/^\d+$/.test(v||'')?Math.min(max,Number(v)):0;
const field=(key:string,zh:string,en:string):BasisField=>({key,label:[zh,en]});
export const personalForeignChecks=[
 ['ordinary_categories_and_no_special_treatment_verified','普通所得分类及无特殊计税待遇已核实','Ordinary categories and no special treatment verified'],
 ['source_fx_deductions_and_losses_verified','来源、汇率、扣除及亏损已核实','Sources, FX, deductions and losses verified'],
 ['paid_tax_evidence_and_history_verified','已缴税凭证及历史余额已核实','Paid-tax evidence and history verified'],
] as const;
export const personalForeignAmounts=[['business_deductions','经营所得扣除','Business deductions'],['business_prior_losses','经营所得可用历史亏损','Eligible prior business losses'],['eligible_foreign_tax_paid','核定境外已缴税额','Eligible foreign tax paid']] as const;
export const transferAmounts=[['original_cost','财产原值','Original cost'],['reasonable_transfer_expenses','合理转让费用','Reasonable transfer expenses'],['allowed_donation','核定捐赠扣除','Allowed donation'],['allowed_tax_reduction','核定减免税额','Allowed tax reduction']] as const;
export const transferChecks=[['single_transaction_source_and_ordinary_rate_verified','单笔交易、来源地及普通税率已核实','Single transaction, source and ordinary rate verified'],['original_cost_expenses_and_reliefs_verified','原值、费用及减免已核实','Original cost, expenses and reliefs verified']] as const;
export const rentalAmounts=[['gross_income','租金收入','Rental income'],['eligible_taxes_and_fees','核定税费','Established taxes and fees'],['eligible_sublease_rent','核定转租租金','Established sublease rent'],['eligible_new_repairs','新增合格修缮费','New eligible repairs'],['established_repair_deduction','本月修缮费扣除','Repair deduction used'],['allowed_donation','核定捐赠扣除','Allowed donation'],['allowed_tax_reduction','核定减免税额','Allowed tax reduction']] as const;
export const rentalChecks=[['ordinary_rate_source_and_monthly_allocation_verified','普通20%税率、来源和月份分配已核实','Ordinary20% rate, source and monthly allocation verified'],['property_aggregation_deductions_and_history_verified','物业归集、扣除资格和修缮历史已核实','Property aggregation, deduction eligibility and repair history verified']] as const;
const globalAmounts=[['comprehensive_deductions','综合所得核定扣除（不含6万元和法定费用）','Verified comprehensive deductions (excluding basic 60000 and statutory expenses)'],['comprehensive_tax_reductions','综合所得减免税额','Comprehensive tax reductions'],['business_tax_reductions','经营所得减免税额','Business tax reductions']] as const;
function countries(input:IncomeTaxInput,values:Record<string,string>):TaxJurisdiction[]{
 const result=[...new Set(input.incomes.map(i=>i.source_jurisdiction))];
 for(let n=0;n<count(values.pfx_extra_count,10);n++){
  const c=values[`pfx_extra_${n}`] as TaxJurisdiction;
  if(c&&c!=='cn'&&taxJurisdictions[c]&&!result.includes(c))result.push(c);
 }
 return result;
}
export function personalForeignPolicy(input:IncomeTaxInput,values:Record<string,string>):IncomePolicy{
 const fields:BasisField[]=globalAmounts.map(([key,zh,en])=>field('pfx_'+key,zh,en));
 fields.push({...field('pfx_extra_count','仅有历史抵免的额外国家数量','Additional countries with prior credits only'),integer:true,min:0,max:10});
 const saved=new Set(input.incomes.map(i=>i.source_jurisdiction));
 for(let n=0;n<count(values.pfx_extra_count,10);n++)fields.push({...field(`pfx_extra_${n}`,`历史抵免国家 ${n+1}`,`Prior-credit country ${n+1}`),options:Object.entries(taxJurisdictions).filter(([c])=>c!=='cn'&&!saved.has(c as TaxJurisdiction)).map(([c,name])=>[c,[name[0],name[1]]])});
 for(const c of countries(input,values)){
  const name=taxJurisdictions[c];
  if(saved.has(c))for(const [key,zh,en] of personalForeignAmounts)if(c!=='cn'||key!=='eligible_foreign_tax_paid')fields.push(field(`pfx_${c}_${key}`,`${name[0]}：${zh}`,`${name[1]}: ${en}`));
  if(c!=='cn'){
   fields.push({...field(`pfx_${c}_count`,`${name[0]}：历史超限额年度数量`,`${name[1]}: Prior excess year count`),integer:true,min:0,max:100});
   for(let n=0;n<count(values[`pfx_${c}_count`],100);n++)fields.push({...field(`pfx_${c}_${n}_year`,`${name[0]}：历史余额 ${n+1} 原始年度`,`${name[1]}: Excess ${n+1} origin year`),integer:true,min:2008,max:2025},field(`pfx_${c}_${n}_amount`,`${name[0]}：历史余额 ${n+1} 金额`,`${name[1]}: Excess ${n+1} amount`));
  }
 }
 input.incomes.forEach((item,n)=>{
  if(item.category==='rental'){
   fields.push({...field(`pfx_rental_${n}_property_id`,`租赁收入 ${n+1}：物业标识`,`Rental income ${n+1}: Property identifier`),text:true},field(`pfx_rental_${n}_opening_eligible_repairs`,`租赁收入 ${n+1}：期初合格修缮费余额`,`Rental income ${n+1}: Opening eligible repairs`));
   for(let month=1;month<=12;month++)for(const [key,zh,en] of rentalAmounts)fields.push(field(`pfx_rental_${n}_${month}_${key}`,`租赁收入 ${n+1}，${month}月：${zh}`,`Rental income ${n+1}, month ${month}: ${en}`));
   for(const [key,zh,en] of rentalChecks)fields.push({...field(`pfx_rental_${n}_${key}`,`租赁收入 ${n+1}：${zh}`,`Rental income ${n+1}: ${en}`),boolean:true});
  }
  if(item.category!=='capital_gain')return;
  for(const [key,zh,en] of transferAmounts)fields.push(field(`pfx_transfer_${n}_${key}`,`转让收入 ${n+1}：${zh}`,`Transfer income ${n+1}: ${en}`));
  for(const [key,zh,en] of transferChecks)fields.push({...field(`pfx_transfer_${n}_${key}`,`转让收入 ${n+1}：${zh}`,`Transfer income ${n+1}: ${en}`),boolean:true});
 });
 fields.push(...personalForeignChecks.map(([key,zh,en])=>({...field('pfx_'+key,zh,en),boolean:true})),field('prepaid_tax','归属本期的预缴税额','Prepaid tax for this period'));
 return {id:'cn_personal_foreign_2026',label:['中国居民个人普通境外所得（2026）','China resident ordinary foreign personal income (2026)'],fields,
 notice:['适用于普通综合所得、各国非负经营税基及普通20%利息股息。填写扣缴前人民币收入和明确已缴境外税额（无则0）。综合扣除、各国经营扣除、逐笔转让原值费用及捐赠之和须等于保存的扣除总额，不包括综合所得6万元及劳务、稿酬等法定费用；不得重复扣除。经营亏损限同国核定可用金额。抵免分国计算，保留历史余额原始年度。结果包括境内普通利息股息全年税额，不等同于B表申报金额。每条转让收入必须为一笔交易的全部收入而非净收益，亏损不自动抵其他交易；须核实境外股权涉及中国不动产的来源地规则。每条租赁收入对应一个物业和12个月，空置月份明确填0；按已核定普通20%税率计算。租赁税费、转租租金、实际使用的修缮费扣除及捐赠也须计入保存的扣除总额，不包括法定费用。修缮发生额不等于使用额；住房优惠及预收租金分摊不自动推定。不含特殊奖金股权、饶让抵免或自动认定优惠。',
 'Ordinary comprehensive income, nonnegative country business bases and ordinary20% interest/dividends. Save gross CNY income before withholding and explicit foreign tax paid (zero if none). Comprehensive and country business deductions plus transfer costs, expenses and donations must match saved deductions, excluding the comprehensive basic60000 and statutory remuneration expenses; do not double claim. Only verified same-country business losses. Credits remain per country with original years preserved. Full-year total includes domestic ordinary investment tax and is not a B-form filing amount. Each transfer income row must be one transaction with gross proceeds, not net gain; losses do not offset other transactions. Verify source rules for foreign equity linked to Chinese real estate. Each rental income covers one property and12 explicit months, including zero-income months, using established ordinary20% treatment. Rental taxes, subrent, repairs used and donations must also match saved deductions; statutory expenses are excluded. Repairs incurred are distinct from deductions used. Housing relief and advance-rent allocation are not inferred. Excludes special bonuses/equity, deemed credits and automatic incentive eligibility.']};
}
export function personalForeignBasis(basis:Record<string,unknown>,input:IncomeTaxInput,values:Record<string,string>){
 const saved=new Set(input.incomes.map(i=>i.source_jurisdiction));
 const extra=Array.from({length:count(values.pfx_extra_count,10)},(_,n)=>values[`pfx_extra_${n}`]);
 if(new Set(extra).size!==extra.length||extra.some(c=>!c||c==='cn'||saved.has(c as TaxJurisdiction)))throw new Error('Duplicate country');
 const workpaper:Record<string,unknown>={countries:countries(input,values).map(country=>({country,
  ...Object.fromEntries(personalForeignAmounts.map(([key])=>[key,basis[`pfx_${country}_${key}`]??'0'])),
  prior_excess:Array.from({length:count(values[`pfx_${country}_count`],100)},(_,n)=>({origin_year:basis[`pfx_${country}_${n}_year`],amount:basis[`pfx_${country}_${n}_amount`]}))}))};
 workpaper.transfers=input.incomes.flatMap((item,n)=>item.category==='capital_gain'?[{income_index:n,...Object.fromEntries([...transferAmounts,...transferChecks].map(([key])=>[key,basis[`pfx_transfer_${n}_${key}`]]))}]:[]);
 workpaper.rentals=input.incomes.flatMap((item,n)=>item.category==='rental'?[{income_index:n,property_id:basis[`pfx_rental_${n}_property_id`],opening_eligible_repairs:basis[`pfx_rental_${n}_opening_eligible_repairs`],...Object.fromEntries(rentalChecks.map(([key])=>[key,basis[`pfx_rental_${n}_${key}`]])),months:Array.from({length:12},(_,m)=>({month:m+1,...Object.fromEntries(rentalAmounts.map(([key])=>[key,basis[`pfx_rental_${n}_${m+1}_${key}`]]))}))}]:[]);
 for(const [key] of [...globalAmounts,...personalForeignChecks])workpaper[key]=basis['pfx_'+key];
 return {...Object.fromEntries(Object.entries(basis).filter(([k])=>!k.startsWith('pfx_'))),workpaper};
}
