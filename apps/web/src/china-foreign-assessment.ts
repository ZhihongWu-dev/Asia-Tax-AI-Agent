import type {BasisField,IncomePolicy} from './income-assessment';
import {taxJurisdictions,type IncomeTaxInput,type TaxJurisdiction} from './income-tax';
const count=(raw:string|undefined,max:number)=>/^\d+$/.test(raw||'')?Math.min(max,Number(raw)):0;
const field=(key:string,zh:string,en:string):BasisField=>({key,label:[zh,en]});
export const cnForeignChecks=[
 ['ordinary_25_percent_positive_bases_verified','普通25%税率及非负税基已核实','Ordinary 25% rate and nonnegative country bases verified'],
 ['income_tax_eligibility_and_fx_verified','税款资格、协定限额及汇率已核实','Tax eligibility, treaty limits and FX verified'],
 ['method_lock_and_carryforward_history_verified','抵免方式五年锁定及结转历史已核实','Five-year method lock and carryforward history verified'],
 ['direct_tax_only_no_other_reliefs_verified','仅直接税额且无其他税收优惠','Direct tax only and no other tax reliefs'],
 ['gross_before_withholding_and_expense_allocation_verified','收入为扣缴前金额且费用分摊已核实','Income before withholding and expense allocation verified'],
] as const;
export const cnForeignAmounts=[['deductions','分摊扣除','Allocated deductions'],['exempt_income','收入中免税部分','Exempt income included in gross'],
 ['non_taxable_income','收入中不征税部分','Non-taxable income included in gross'],['eligible_prior_losses','本期可用所得亏损','Eligible prior income losses'],
 ['eligible_direct_tax','核定可抵免直接税额','Eligible direct foreign tax']] as const;
function countries(input:IncomeTaxInput,values:Record<string,string>):TaxJurisdiction[]{
 const base=[...new Set(input.incomes.map(i=>i.source_jurisdiction))];
 for(let i=0;i<count(values.cfx_extra_count,10);i++){
  const code=values[`cfx_extra_${i}`] as TaxJurisdiction;
  if(code&&code!=='cn'&&taxJurisdictions[code]&&!base.includes(code))base.push(code);
 }
 return base;
}
export function chinaForeignPolicy(input:IncomeTaxInput,values:Record<string,string>):IncomePolicy{
 const fields:BasisField[]=[{...field('cfx_method','已核定抵免方式','Established credit method'),options:[['per_country',['分国不分项','Per country']],['pooled',['不分国不分项','Pooled foreign income']]]},
 {...field('cfx_extra_count','仅有历史抵免的额外国家数量','Additional countries with prior credits only'),integer:true,min:0,max:10}];
 const present=new Set(input.incomes.map(i=>i.source_jurisdiction));
 for(let i=0;i<count(values.cfx_extra_count,10);i++)fields.push({...field(`cfx_extra_${i}`,`历史抵免国家 ${i+1}`,`Prior-credit country ${i+1}`),options:Object.entries(taxJurisdictions).filter(([c])=>c!=='cn'&&!present.has(c as TaxJurisdiction)).map(([c,n])=>[c,[n[0],n[1]]])});
 for(const code of countries(input,values)){
  const names=taxJurisdictions[code];
  if(present.has(code))for(const [key,zh,en]of cnForeignAmounts)if(code!=='cn'||key!=='eligible_direct_tax')fields.push(field(`cfx_${code}_${key}`,`${names[0]}：${zh}`,`${names[1]}: ${en}`));
  if(code!=='cn'){
   fields.push({...field(`cfx_${code}_count`,`${names[0]}：历史超限额年度数量`,`${names[1]}: Prior excess year count`),integer:true,min:0,max:100});
   for(let n=0;n<count(values[`cfx_${code}_count`],100);n++)fields.push(
    {...field(`cfx_${code}_${n}_year`,`${names[0]}：历史余额 ${n+1} 原始年度`,`${names[1]}: Excess ${n+1} origin year`),integer:true,min:2008,max:2025},
    field(`cfx_${code}_${n}_amount`,`${names[0]}：历史余额 ${n+1} 金额`,`${names[1]}: Excess ${n+1} amount`));
  }
 }
 fields.push(...cnForeignChecks.map(([key,zh,en])=>({...field('cfx_'+key,zh,en),boolean:true})),field('prepaid_tax','归属本期的预缴税额','Prepaid tax for this period'));
 return {id:'cn_company_foreign_direct_2026',label:['中国企业普通境外直接抵免（2026）','China company ordinary direct foreign credit (2026)'],
 notice:['适用于居民企业普通25%税率及各国非负税基。逐国分摊扣除和已核定可用所得亏损须与保存资料一致；免税及不征税收入不得重复计入扣除。境外收入填扣缴前人民币金额，已缴境外税额须明确填写（无则0）。抵免方式须符合五年锁定，不能自动选最优方式；历史余额须填写原始年度，不能重置年限。不含间接或饶让抵免、特殊税率、其他税额优惠或负税基。',
 'Resident ordinary 25% company with nonnegative country bases. Allocated deductions and verified usable income losses must match saved totals; do not duplicate excluded income in deductions. Save gross CNY income before withholding and explicit foreign tax paid, including zero. Verify the five-year method lock; no automatic best-method selection. Preserve original excess-credit years. Excludes indirect/deemed credits, special rates, other reliefs and negative country bases.'],fields};
}
export function chinaForeignBasis(basis:Record<string,unknown>,input:IncomeTaxInput,values:Record<string,string>):Record<string,unknown>{
 const original=new Set(input.incomes.map(i=>i.source_jurisdiction));
 const extra=Array.from({length:count(values.cfx_extra_count,10)},(_,i)=>values[`cfx_extra_${i}`]);
 if(new Set(extra).size!==extra.length||extra.some(c=>!c||c==='cn'||original.has(c as TaxJurisdiction)))throw new Error('Duplicate country');
 const allocations=countries(input,values).map(country=>{
  const row:Record<string,unknown>={country};
  for(const [key] of cnForeignAmounts)row[key]=basis[`cfx_${country}_${key}`]??'0';
  row.prior_excess=Array.from({length:count(values[`cfx_${country}_count`],100)},(_,n)=>({origin_year:basis[`cfx_${country}_${n}_year`],amount:basis[`cfx_${country}_${n}_amount`]}));
  return row;
 });
 const workpaper:Record<string,unknown>={method:basis.cfx_method,allocations};
 for(const [key] of cnForeignChecks)workpaper[key]=basis['cfx_'+key];
 const result={...basis,workpaper};
 for(const key of Object.keys(result))if(key.startsWith('cfx_'))delete (result as Record<string,unknown>)[key];
 return result;
}
