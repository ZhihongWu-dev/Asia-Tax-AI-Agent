import type { IncomeTaxInput } from './income-tax';
import type { BasisField, IncomePolicy } from './income-assessment';

const count = (value: unknown) => {
  const n=Number(value); if(!Number.isInteger(n)||n<1||n>100)throw new Error('Invalid count'); return n;
};

export function thaiForeignPolicy(input: IncomeTaxInput, values: Record<string,string>): IncomePolicy {
  const fields: BasisField[]=[
    {key:'net_taxable_income',label:['核定应税净所得（扣除不纳入的汇入收入及已保存扣除）','Verified net taxable income after excluded receipts and saved deductions']},
    {key:'prepaid_tax',label:['泰国本期已缴税款（不含境外税）','Thai period prepayments (exclude foreign tax)']},
  ];
  let total=0;
  input.incomes.forEach((item,n)=>{
    if(item.source_jurisdiction==='th')return;
    const prefix=`foreign_${n}_`;
    fields.push({key:prefix+'count',label:[`收入 ${n+1}：原始收入批次数`,`Income ${n+1}: original earnings pool count`],integer:true,min:1,max:100});
    let pools;try{pools=count(values[prefix+'count']||'1');}catch{return;}
    for(let j=0;j<pools;j++) {
      if(++total>1000)return;
      const key=prefix+`${j}_`,zh=`收入 ${n+1} 批次 ${j+1}：`,en=`Income ${n+1}, pool ${j+1}: `;
      fields.push(
        {key:key+'pool_id',label:[zh+'凭证／收入批次唯一编号',en+'unique evidence / earnings pool ID'],text:true},
        {key:key+'total_foreign_income',label:[zh+'原始境外收入总额',en+'total original foreign earnings']},
        {key:key+'foreign_income_tax_paid',label:[zh+'原始收入实际已缴境外所得税',en+'foreign income tax paid on original earnings']},
        {key:key+'eligible_foreign_income_tax_paid',label:[zh+'核定符合协定及来源国征税上限的税额',en+'tax eligible under verified treaty taxing rights and source caps']},
        {key:key+'previously_remitted_income',label:[zh+'以前年度已汇入收入',en+'income remitted in prior years']},
        {key:key+'entitlement_and_fx_explanation',label:[zh+'协定资格、税款凭证及统一泰铢换算依据（至少20字）',en+'treaty eligibility, tax evidence and consistent THB valuation basis (20+ characters)'],text:true},
        {key:key+'remittance_count',label:[zh+'本年汇入笔数',en+'current-year remittance count'],integer:true,min:1,max:100});
      let remittances;try{remittances=count(values[key+'remittance_count']||'1');}catch{continue;}
      for(let k=0;k<remittances;k++) {
        const line=key+`remit_${k}_`,z=zh+`汇入 ${k+1}：`,e=en+`remittance ${k+1}: `;
        fields.push({key:line+'remitted_income',label:[z+'收入金额（不含本金）',e+'income amount (exclude capital)']},
          {key:line+'income_date',label:[z+'原始收入取得日期',e+'original earnings date'],date:true,dateMin:'1900-01-01'},
          {key:line+'remittance_date',label:[z+'汇入日期',e+'remittance date'],date:true,dateMin:'2026-01-01'},
          {key:line+'days_in_thailand_in_income_year',label:[z+'取得收入当年在泰天数',e+'days in Thailand in the earnings year'],integer:true,min:0,max:366});
      }
    }
  });
  fields.push(...([
    ['ordinary_treatment_confirmed','已核实普通年度税制及特殊税制排除条件','Ordinary annual treatment and special-regime exclusions verified'],
    ['assessable_income_classification_confirmed','已核实第40条所得类别、费用及扣除','Section40 income types, expenses and deductions verified'],
    ['tracing_fx_and_entitlement_verified','已核实批次不重叠、汇入追溯、汇率及协定抵免资格','Disjoint pools, remittance tracing, FX and treaty credit eligibility verified'],
    ['saved_tax_represents_original_pool_tax','已保存境外税额为原始收入批次税额，尚未按汇入比例分摊','Saved foreign tax is the original pool tax before remittance apportionment'],
  ] as [string,string,string][]).map(([key,zh,en])=>({key,label:[zh,en] as [string,string],boolean:true})));
  return {id:'th_foreign_income_2026',label:['泰国居民境外所得汇入及抵免（2026）','Thailand resident foreign income remittance and credit (2026)'],
    notice:['已保存境外收入须为2026年实际汇入的收入部分，不含本金；境外税额须为对应原始收入批次的已缴所得税。每个批次采用一致且有凭证的泰铢换算依据，原始税额与汇入金额分别对账。取得收入年度的居民身份决定是否纳入；抵免资格和来源国征税上限须逐笔核实。无抵免资格填0，不代表收入免税。结果为申报取整前金额；不含资本利得、泰国境内股息及特殊税制。',
      'Saved foreign income is the income portion remitted in2026, excluding capital; saved foreign tax is tax paid on the corresponding original earnings pools. Use one documented THB valuation basis per pool. Original tax and remitted income reconcile separately. Earnings-year residence determines inclusion; verify treaty entitlement and source taxing caps per pool. Enter0 eligible tax where no credit applies; this does not exempt the income. Results precede return rounding; excludes capital gains, Thai domestic dividends and special regimes.'],fields};
}

export function thaiForeignBasis(basis: Record<string,unknown>, input: IncomeTaxInput) {
  const result={...basis}, pools:Record<string,unknown>[]=[], ids=new Set<string>();let totalRemittances=0;
  input.incomes.forEach((item,n)=>{
    if(item.source_jurisdiction==='th')return;
    const prefix=`foreign_${n}_`;
    for(let j=0;j<count(basis[prefix+'count']);j++) {
      const key=prefix+`${j}_`, pool:Record<string,unknown>={income_index:n};
      for(const field of ['pool_id','total_foreign_income','foreign_income_tax_paid','eligible_foreign_income_tax_paid','previously_remitted_income','entitlement_and_fx_explanation'])pool[field]=basis[key+field];
      const id=String(pool.pool_id||'').trim();if(!id||ids.has(id))throw new Error('Duplicate or empty pool ID');ids.add(id);pool.pool_id=id;
      const remittances=[];
      for(let k=0;k<count(basis[key+'remittance_count']);k++) {
        if(++totalRemittances>1000)throw new Error('Too many remittances');
        const line=key+`remit_${k}_`, row:Record<string,unknown>={income_index:n};
        for(const field of ['remitted_income','income_date','remittance_date','days_in_thailand_in_income_year'])row[field]=basis[line+field];
        remittances.push(row);
      }
      pool.remittances=remittances;pools.push(pool);
      if(pools.length>1000)throw new Error('Too many pools');
    }
  });
  for(const key of Object.keys(result))if(key.startsWith('foreign_'))delete result[key];
  return {...result,pools};
}
