import type { IncomeTaxInput } from './income-tax';
import type { BasisField, IncomePolicy } from './income-assessment';

export function thaiDividendPolicy(input: IncomeTaxInput, values: Record<string,string>): IncomePolicy {
  const fields: BasisField[] = [
    {key:'election',label:['股息申报选择','Dividend election'],options:[['aggregate',['汇总申报并申请抵免','Aggregate and claim credit']],['final_withholding',['10%预扣税作为最终税款','Final 10% withholding']]]},
    {key:'allowed_expenses_and_allowances',label:['核定费用及扣除合计（须与保存金额一致）','Verified expenses and allowances (must match saved amount)']},
    {key:'other_prepaid_tax',label:['其他收入已缴税额（不含股息预扣税）','Other income prepayments (exclude dividend withholding)']},
  ];
  input.incomes.forEach((item,n)=>{
    if(item.category!=='dividend')return;
    const prefix=`dividend_${n}_`, count=Number(values[prefix+'count'] || '1');
    fields.push({key:prefix+'count',label:[`收入 ${n+1}：凭证税率分笔数`,`Income ${n+1}: certificate tranche count`],integer:true,min:1,max:100});
    if(!Number.isInteger(count)||count<1||count>100)return;
    for(let j=0;j<count;j++) {
      const key=prefix+`${j}_`, zh=`收入 ${n+1} 第 ${j+1} 笔：`, en=`Income ${n+1}, tranche ${j+1}: `;
      fields.push({key:key+'gross_dividend',label:[zh+'预扣税前股息',en+'dividend before withholding']},
        {key:key+'credit_eligible',label:[zh+'符合股息抵免条件',en+'eligible for dividend credit'],boolean:true},
        {key:key+'corporate_rate_percent',label:[zh+'凭证记载的企业税率（%）',en+'certified corporate rate (%)'],max:99.999999,showWhen:[key+'credit_eligible','true']},
        {key:key+'withholding_tax',label:[zh+'已扣股息税',en+'dividend tax withheld']});
    }
  });
  fields.push(
    {key:'certificates_verified',label:['已核对全部凭证、各笔企业税率及预扣税','All certificates, tranche corporate rates and withholding verified'],boolean:true},
    {key:'recipient_eligibility_verified',label:['已核实收款人抵免资格','Recipient credit eligibility verified'],boolean:true},
    {key:'election_scope_verified',label:['已包含全部应纳税境内股息及抵免付款方，排除免税、境外及特殊股息','All taxable domestic dividends and creditable payers included; exempt, foreign and special dividends excluded'],boolean:true},
    {key:'ordinary_income_classification_verified',label:['其他收入及扣除均已按普通年度税制核实','Other income and deductions verified under ordinary annual treatment'],boolean:true});
  return {id:'th_dividend_2026',label:['泰国居民股息年度结算（2026）','Thailand resident dividend settlement (2026)'],
    notice:['每笔已保存股息按凭证税率拆分，分笔税前金额之和必须等于该收入。汇总申报不能只挑选部分可抵免付款方；抵免可产生退税。最终税款选择要求每笔已足额扣缴10%，该预扣税不再抵退年度税款。无抵免资格的股息不填企业税率；免税股息不适用此流程。结果为申报取整前金额。',
      'Split each saved dividend by certified corporate rate; tranche amounts before withholding must reconcile to that income. Aggregation must include all creditable payers and can produce refundable credit. Final treatment requires full 10% withholding on every tranche, excluded from annual refunds. Non-creditable tranches have no corporate rate; exempt dividends need a separate workflow. Results are before return rounding.'],fields};
}

export function thaiDividendBasis(basis: Record<string,unknown>, input: IncomeTaxInput) {
  const result={...basis}, tranches: Record<string,unknown>[]=[];
  input.incomes.forEach((item,n)=>{
    if(item.category!=='dividend')return;
    const prefix=`dividend_${n}_`, count=Number(basis[prefix+'count']);
    if(!Number.isInteger(count)||count<1||count>100)throw new Error('Invalid tranche count');
    for(let j=0;j<count;j++) {
      const key=prefix+`${j}_`;
      tranches.push({income_index:n,gross_dividend:basis[key+'gross_dividend'],
        credit_eligible:basis[key+'credit_eligible'],corporate_rate_percent:basis[key+'corporate_rate_percent'],
        withholding_tax:basis[key+'withholding_tax']});
    }
  });
  if(tranches.length>1000)throw new Error('Too many dividend tranches');
  for(const key of Object.keys(result))if(key.startsWith('dividend_'))delete result[key];
  return {...result,tranches};
}
