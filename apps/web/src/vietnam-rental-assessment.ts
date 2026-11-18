import type { IncomePolicy, BasisField } from './income-assessment';
import type { IncomeTaxInput } from './income-tax';

export function vietnamRentalPolicy(input: IncomeTaxInput): IncomePolicy {
  const fields: BasisField[] = [];
  input.incomes.forEach((_income,n)=>{
    const prefix=`rental_${n}_`;
    fields.push(
      {key:prefix+'contract_id',label:[`${n+1}. 合同编号`,`${n+1}. Contract identifier`],text:true},
      {key:prefix+'allocated_revenue_deduction',label:[`${n+1}. 分配的年度租金扣除`,`${n+1}. Allocated annual rental deduction`]},
      {key:prefix+'prepaid_tax',label:[`${n+1}. 本期实际已缴税额`,`${n+1}. Actual tax paid for this period`]},
      {key:prefix+'tenant_files',label:[`${n+1}. 由承租人申报代缴`,`${n+1}. Tenant files and pays on behalf`],boolean:true},
      {key:prefix+'filing_and_allocation_verified',label:[`${n+1}. 已核实合同申报责任、扣除分配和实缴凭证`,`${n+1}. Contract filing, allocation and payment evidence verified`],boolean:true},
    );
  });
  fields.push(
    {key:'rental_only_scope_verified',label:['已核实仅含境内房产租金，无住宿服务或其他经营所得','Domestic property rental only; no accommodation or other business verified'],boolean:true},
    {key:'annual_recognition_and_all_contracts_verified',label:['已核实全年收入确认及全部租赁合同','Annual revenue recognition and all rental contracts verified'],boolean:true},
  );
  return {id:'vn_property_rental_2026',label:['越南居民个人房产出租（2026）','Vietnam resident property rental (2026)'],fields,
    notice:['每项已保存租金对应一份合同，使用归属本年度的收入，不直接把多年预收款作为本年收入。全部合同共享10亿越南盾年度扣除，分配合计须与已保存扣除一致。承租人代报须核对合同中的代报责任和扣除分配。分别保留各合同已缴款及余额；汇总多缴不代表可跨合同直接抵扣或已获退税。不含住宿服务、混合经营、境外所得、增值税或申报取整。',
      'Each saved rental income maps to one contract using revenue recognized for this year, not unadjusted multi-year advances. All contracts share a VND 1bn annual deduction; allocations must match saved deductions. Verify contractual filing responsibility and allocation for tenant-filed returns. Payments and balances remain separate per contract; an aggregate overpayment does not authorize cross-contract offsets or refunds. Excludes accommodation, mixed business, foreign income, VAT and return rounding.']};
}

export function vietnamRentalBasis(basis:Record<string,unknown>,input:IncomeTaxInput) {
  const result={...basis};
  result.contracts=input.incomes.map((_income,n)=>{
    const row:Record<string,unknown>={income_index:n};
    for(const key of ['contract_id','allocated_revenue_deduction','prepaid_tax','tenant_files','filing_and_allocation_verified'])row[key]=result[`rental_${n}_${key}`];
    return row;
  });
  for(const key of Object.keys(result))if(/^rental_\d+_/.test(key))delete result[key];
  return result;
}
