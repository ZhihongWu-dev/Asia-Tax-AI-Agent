import type { IncomePolicy, BasisField } from './income-assessment';
import type { IncomeTaxInput } from './income-tax';

export const businessCategories: [string, [string, string]][] = [
  ['goods', ['商品分销／供应', 'Goods distribution/supply']],
  ['services_without_materials', ['服务／不包材料施工', 'Services/construction without materials']],
  ['asset_rental_or_specified_agency', ['非房产资产租赁／指定代理业务', 'Non-property asset rental/specified agency']],
  ['production_transport_with_materials', ['生产／运输／包材料施工', 'Production/transport/construction with materials']],
  ['digital_content', ['数字内容业务', 'Digital content business']],
  ['other_business', ['经核定的其他经营业务', 'Verified other business']],
];

export function vietnamBusinessPolicy(input: IncomeTaxInput): IncomePolicy {
  const fields: BasisField[] = [
    {key:'method', label:['有效计税方法', 'Valid calculation method'], options:[
      ['revenue', ['收入比例法', 'Revenue percentage method']],
      ['profit', ['利润法', 'Profit method']]]},
    {key:'deductible_expenses', label:['核定可扣除经营费用', 'Verified deductible business expenses'], showWhen:['method','profit']},
    {key:'revenue_method_started_within_limit', label:['已核实采用收入比例法时符合30亿收入限额条件', 'Revenue-method entry within the VND 3bn limit verified'], boolean:true, showWhen:['method','revenue']},
  ];
  input.incomes.forEach((_income,n)=>{
    fields.push({key:`business_${n}_category`, label:[`${n+1}. 经营收入分类`, `${n+1}. Business income classification`], options:businessCategories});
    fields.push({key:`business_${n}_deduction`, label:[`${n+1}. 分配的年度收入扣除`, `${n+1}. Allocated annual revenue deduction`], showWhen:['method','revenue']});
  });
  fields.push(
    {key:'prepaid_tax',label:['本期实际预缴及扣缴税额', 'Actual prepaid and withheld tax for this period']},
    {key:'ordinary_domestic_business_verified',label:['已核实仅含境内普通经营所得，无房产出租、特殊优惠或境外经营', 'Domestic ordinary business only; no property rent, special relief or foreign business verified'],boolean:true},
    {key:'revenue_and_expense_evidence_verified',label:['已核实全部经营收入、分类及费用凭证，含平台代扣收入', 'All business receipts, classifications and expense evidence verified, including platform-withheld receipts'],boolean:true},
    {key:'method_election_and_continuity_verified',label:['已核实方法选择及两年延续要求，未仅按较低税额切换', 'Method election and two-year continuity verified; no switch solely for lower tax'],boolean:true},
  );
  return {id:'vn_business_2026',label:['越南居民个人经营所得（2026）', 'Vietnam resident business income (2026)'],fields,
    notice:['逐项使用已保存的全年经营收入，须覆盖全部业务和经营地点。收入比例法的10亿越南盾扣除由各项共享，分配合计须与已保存扣除一致；利润法须填入核定费用，与已保存扣除一致。不得重复扣除费用和收入扣除。法定全年收入不超过100亿时计算30%减税；有效收入比例法本年超过30亿时提示次年转利润法。不含房产出租、境外所得、特殊免税、增值税或申报取整。',
      'Uses each saved annual business receipt across all activities and locations. Revenue-method activities share one VND 1bn deduction; allocations must reconcile to saved deductions. Profit-method verified expenses must match saved deductions. Do not deduct both expenses and the revenue allowance. Annual revenue up to VND 10bn receives 30% relief; a valid revenue-method business crossing VND 3bn is flagged for next-year profit treatment. Excludes property rent, foreign income, special exemptions, VAT and return rounding.']};
}

export function vietnamBusinessBasis(basis: Record<string,unknown>, input: IncomeTaxInput) {
  const result = {...basis};
  result.activities = input.incomes.map((_income,n)=>({income_index:n,
    category:result[`business_${n}_category`],
    allocated_revenue_deduction:result.method==='revenue'?result[`business_${n}_deduction`]:'0'}));
  for(const key of Object.keys(result)) if(key.startsWith('business_'))delete result[key];
  return result;
}
