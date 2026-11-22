import type {BasisField,IncomePolicy} from './income-assessment';
import type {IncomeTaxInput} from './income-tax';
const money=(key:string,zh:string,en:string):BasisField=>({key,label:[zh,en]});
const check=(key:string,zh:string,en:string):BasisField=>({...money(key,zh,en),boolean:true});
function groupId(input:IncomeTaxInput,values:Record<string,string>,n:number){
 return input.incomes[n].category==='business'?`trade_${values[`sfc_group_${n}`]||'1'}`:`passive_${n+1}`;
}
export function singaporeForeignPolicy(input:IncomeTaxInput,values:Record<string,string>):IncomePolicy{
 const fields:BasisField[]=[];
 const businessCount=input.incomes.filter(i=>i.category==='business').length;
 input.incomes.forEach((item,n)=>{
  if(item.category==='business')fields.push({key:`sfc_group_${n}`,label:[`收入${n+1}：营业来源组`,`Income ${n+1}: trade source group`],options:Array.from({length:businessCount},(_,i)=>[String(i+1),[`营业组${i+1}`,`Trade group ${i+1}`]])});
  if(item.source_jurisdiction!=='sg')fields.push(
   money(`sfc_tax_${n}`,`收入${n+1}：合资格直接境外税`,`Income ${n+1}: eligible direct foreign tax`),
   money(`sfc_rate_${n}`,`收入${n+1}：来源地最高企业税率（%）`,`Income ${n+1}: foreign headline rate (%)`),
   check(`sfc_pool_${n}`,`收入${n+1}：选择汇总抵免`,`Income ${n+1}: elect pooling`),
   check(`sfc_entitled_${n}`,`收入${n+1}：已核实同一所得抵免资格`,`Income ${n+1}: same-income credit entitlement verified`));
 });
 for(const id of new Set(input.incomes.map((_,n)=>groupId(input,values,n))))fields.push(money(`sfc_ded_${id}`,`${id}：核定费用及资本扣除`,`${id}: verified expenses and capital allowances`));
 fields.push(money('sfc_donations','核准捐赠扣除','Approved donation deduction'),
  {key:'exemption_scheme',label:['所得豁免制度','Income exemption scheme'],options:[['partial',['部分豁免','Partial exemption']],['startup',['初创豁免','Start-up exemption']],['none',['不适用','None']]]},
  check('startup_eligibility_confirmed','已核实初创豁免资格','Start-up eligibility confirmed'),
  check('cash_grant_eligible','符合现金补助资格','Cash grant eligible'),money('prepaid_tax','归属本期的预缴税额','Prepaid tax for this period'),
  check('sfc_allocation','已核实居民身份、同一所得及来源分摊','Residence, same income and source allocation verified'),
  check('sfc_ordinary','仅普通非负所得、直接税额及无结转亏损','Ordinary nonnegative income, direct taxes and no carried losses verified'));
 return {id:'sg_company_foreign_direct_ya2026',label:['新加坡企业境外直接抵免（YA2026）','Singapore company direct foreign credit (YA2026)'],
 notice:['同一营业来源的境内外收入须使用同一组；不同业务分组核算。被动所得逐项核算。保存的扣除总额应等于各组费用、资本扣除及核准捐赠。境外收入须已核实应税且不适用免税；不含间接抵免、特殊税率或亏损分摊。汇总须满足来源地最高企业税率至少15%等条件，不能仅依据实际扣缴税率判断。',
 'Group domestic and foreign income from the same trade together; separate different trades. Passive sources are assessed individually. Saved deductions must equal group expenses, capital allowances and approved donations. Verify foreign income is taxable and not exempt. Excludes underlying credits, special rates and loss allocation. Pooling requires a headline corporate rate of at least15% and other eligibility conditions; the actual withholding rate alone does not establish eligibility.'],fields};
}
export function singaporeForeignBasis(basis:Record<string,unknown>,input:IncomeTaxInput,values:Record<string,string>){
 const grouped=new Map<string,{source_id:string;kind:string;deductions:unknown;sources:unknown[]}>();
 input.incomes.forEach((item,n)=>{
  const id=groupId(input,values,n);
  if(!grouped.has(id))grouped.set(id,{source_id:id,kind:item.category==='business'?'trade':'passive',deductions:basis[`sfc_ded_${id}`],sources:[]});
  const domestic=item.source_jurisdiction==='sg';
  grouped.get(id)!.sources.push({income_index:n,eligible_direct_tax:domestic?'0':basis[`sfc_tax_${n}`],
   pool_elected:domestic?false:basis[`sfc_pool_${n}`],headline_rate_percent:domestic?'0':basis[`sfc_rate_${n}`],credit_entitlement_verified:domestic?false:basis[`sfc_entitled_${n}`]});
 });
 basis.workpaper={groups:[...grouped.values()],approved_donations:basis.sfc_donations,
  resident_same_income_and_allocation_verified:basis.sfc_allocation,direct_tax_ordinary_positive_sources_verified:basis.sfc_ordinary};
 for(const key of Object.keys(basis))if(key.startsWith('sfc_'))delete basis[key];
 return basis;
}
