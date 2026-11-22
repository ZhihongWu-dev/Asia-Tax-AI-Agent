import type {BasisField,IncomePolicy} from './income-assessment';
import type {IncomeTaxInput} from './income-tax';
const field=(key:string,zh:string,en:string):BasisField=>({key,label:[zh,en]});
const check=(key:string,zh:string,en:string):BasisField=>({...field(key,zh,en),boolean:true});
const group=(values:Record<string,string>,n:number)=>values[`mfc_group_${n}`]||String(n+1);
export function malaysiaForeignPolicy(input:IncomeTaxInput,values:Record<string,string>):IncomePolicy{
 const fields:BasisField[]=[];
 input.incomes.forEach((item,n)=>{
  fields.push({key:`mfc_group_${n}`,label:[`收入${n+1}：来源组`,`Income ${n+1}: source group`],options:input.incomes.map((other,j)=>({other,j})).filter(({other})=>other.category===item.category&&(item.category==='business'||other.source_jurisdiction===item.source_jurisdiction)).map(({j}):[string,[string,string]]=>[String(j+1),[`来源${j+1}`,`Source ${j+1}`]])});
  fields.push(field(`mfc_exempt_${n}`,`收入${n+1}：免税部分`,`Income ${n+1}: exempt income`),
   {key:`mfc_method_${n}`,label:[`收入${n+1}：抵免方法`,`Income ${n+1}: credit method`],options:[['none',['不申请','No claim']],['bilateral',['双边','Bilateral']],['unilateral',['单边','Unilateral']]]});
  if(values[`mfc_method_${n}`]&&values[`mfc_method_${n}`]!=='none')fields.push(
   {...field(`mfc_country_${n}`,`收入${n+1}：征税国家两位代码（如 in）`,`Income ${n+1}: taxing country two-letter code (e.g. in)`),text:true},
   field(`mfc_tax_${n}`,`收入${n+1}：合资格境外税款`,`Income ${n+1}: eligible foreign tax`));
  fields.push(check(`mfc_verified_${n}`,`收入${n+1}：已核实应税状态及抵免资格`,`Income ${n+1}: taxable status and credit eligibility verified`));
 });
 for(const id of new Set(input.incomes.map((_,n)=>group(values,n)))){
  for(const [key,zh,en] of [['additions','调增','Additions'],['expenses','可扣费用','Allowable expenses'],['statutory_charges','法定加回','Statutory charges'],['statutory_allowances','资本扣除','Capital allowances']])fields.push(field(`mfc_${id}_${key}`,`来源${id}：${zh}`,`Source ${id}: ${en}`));
  fields.push(check(`mfc_${id}_same`,`来源${id}：已核实同一来源分摊`,`Source ${id}: same-source allocation verified`));
 }
 fields.push(field('mfc_total_deductions','总所得扣除','Total-income deductions'),
  {key:'mfc_scheme',label:['企业税率方案','Company rate scheme'],options:[['ordinary',['普通','Ordinary']],['sme',['合资格中小企业','Eligible SME']]]},
  check('mfc_sme','已核实中小企业资格','SME eligibility verified'),
  check('mfc_ordinary','已核实普通居民企业且无亏损','Ordinary resident company without losses verified'),
  check('mfc_deductions','已核实扣除及来源分摊','Deductions and source allocation verified'),
  check('mfc_entitlement','已核实条约、税期、汇率及无重复抵免','Treaty, tax period, FX and no duplicate credit verified'),
  field('prepaid_tax','本期预缴税款','Prepaid tax for this period'));
 return {id:'my_company_foreign_direct_ya2026',label:['马来西亚企业境外抵免（YA2026）','Malaysia company foreign credits (YA2026)'],notice:['同一业务来源的境内外收入应归同组；非业务来源按国家分组。保存的扣除须等于费用、资本扣除及总所得扣除之和。免税与申请抵免的收入分开。双边抵免可涉及马来西亚来源所得；单边抵免仅限境外来源。仅普通居民独立企业，不含亏损、特殊税制及申报取整；条约资格及申报时限须核实。','Group domestic and foreign receipts of the same business source together; separate nonbusiness country sources. Saved deductions must equal expenses, capital allowances and total-income deductions. Separate exempt receipts from credit claims. Bilateral credits may cover Malaysia-source income; unilateral credits require foreign-source income. Ordinary standalone resident companies only; excludes losses, special regimes and filing rounding. Verify treaty entitlement and claim deadlines.'],fields};
}
export function malaysiaForeignBasis(basis:Record<string,unknown>,input:IncomeTaxInput,values:Record<string,string>){
 const groups=new Map<string,number[]>();
 input.incomes.forEach((_,n)=>{const id=group(values,n);groups.set(id,[...(groups.get(id)||[]),n]);});
 basis.workpaper={groups:[...groups].map(([id,indexes])=>({source_id:`source_${id}`,receipts:indexes.map(n=>({income_index:n,
  exempt_income:basis[`mfc_exempt_${n}`],method:basis[`mfc_method_${n}`],
  taxing_country:basis[`mfc_method_${n}`]==='none'?null:String(basis[`mfc_country_${n}`]||'').trim().toLowerCase(),
  eligible_foreign_tax:basis[`mfc_method_${n}`]==='none'?'0':basis[`mfc_tax_${n}`],
  taxable_status_and_credit_eligibility_verified:basis[`mfc_verified_${n}`]})),
  additions:basis[`mfc_${id}_additions`],expenses:basis[`mfc_${id}_expenses`],statutory_charges:basis[`mfc_${id}_statutory_charges`],statutory_allowances:basis[`mfc_${id}_statutory_allowances`],same_source_allocation_verified:basis[`mfc_${id}_same`]})),
  total_income_deductions:basis.mfc_total_deductions,scheme:basis.mfc_scheme,sme_eligibility_verified:basis.mfc_sme,
  ordinary_resident_company_no_losses_verified:basis.mfc_ordinary,deductions_and_source_allocation_verified:basis.mfc_deductions,
  treaty_tax_period_fx_and_no_duplicate_claim_verified:basis.mfc_entitlement};
 for(const key of Object.keys(basis))if(key.startsWith('mfc_'))delete basis[key];
 return basis;
}
