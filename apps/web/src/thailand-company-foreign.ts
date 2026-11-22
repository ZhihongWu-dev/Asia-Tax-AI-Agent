import type {BasisField} from './income-assessment';
import type {IncomeTaxInput} from './income-tax';
const field=(key:string,zh:string,en:string):BasisField=>({key,label:[zh,en]});
const check=(key:string,zh:string,en:string):BasisField=>({...field(key,zh,en),boolean:true});
const countries=(input:IncomeTaxInput)=>[...new Set(input.incomes.map(i=>i.source_jurisdiction).filter(c=>c!=='th'))];
const periodCount=(value:unknown)=>Math.max(1,Math.min(200,Math.trunc(Number(value)||1)));
const periodAmounts=[['total_foreign_period_basis','境外完整税期的利润或收入','Profit or receipts for the full foreign period'],['basis_in_overlapping_period','与本期重叠部分的利润或收入','Profit or receipts in the overlapping period'],['foreign_tax_paid','境外已缴税（原币）','Foreign tax paid in original currency'],['payment_date_market_thb_per_unit','支付日市场汇率（每原币单位兑泰铢）','Payment-date market THB per foreign currency unit']];
const periodDates=[['foreign_period_start','境外税期开始日','Foreign period start'],['foreign_period_end','境外税期结束日','Foreign period end'],['payment_date','税款支付日','Tax payment date']];
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
  if(method!=='company_receipts'){
   fields.push(check(prefix+'periods_enabled',`${name}：录入经营税款的期间分摊凭证`,`${name}: include business tax period allocation evidence`));
   if(values[prefix+'periods_enabled']==='true'){
    fields.push({...field(prefix+'period_count',`${name}：分摊凭证数量`,`${name}: allocation evidence count`),integer:true,min:1,max:200});
    for(let n=0;n<periodCount(values[prefix+'period_count']);n++){
     const key=prefix+`period_${n}_`, zh=`${name}凭证${n+1}`, en=`${name} evidence ${n+1}`;
     fields.push({...field(key+'reference',`${zh}：凭证编号`,`${en}: evidence reference`),text:true},
      {key:key+'foreign_tax_base',label:[`${zh}：境外计税依据`,`${en}: foreign tax basis`],options:[['net_profit',['净利润','Net profit']],['gross_receipts',['收入总额','Gross receipts']]]});
     for(const [name,cn,english] of periodDates)fields.push({...field(key+name,`${zh}：${cn}`,`${en}: ${english}`),date:true,dateMin:'1900-01-01',dateMax:'9999-12-31'});
     for(const [name,cn,english] of periodAmounts)fields.push(field(key+name,`${zh}：${cn}`,`${en}: ${english}`));
     fields.push(check(key+'filing_known',`${zh}：已知原申报日期`,`${en}: original filing date known`));
     if(values[key+'filing_known']==='true')fields.push({...field(key+'thai_return_filed_on',`${zh}：原申报日期`,`${en}: original filing date`),date:true,dateMin:input.period_end,dateMax:'9999-12-31'});
     fields.push(check(key+'verified',`${zh}：已核实实际期间利润或收入及缴税凭证`,`${en}: actual period basis and payment evidence verified`));
    }
   }
  }
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
    const periods=[];
    if(treatment!=='company_receipts'&&basis[prefix+'periods_enabled']===true)for(let n=0;n<periodCount(basis[prefix+'period_count']);n++){
     const key=prefix+`period_${n}_`;
     const allocation:Record<string,unknown>={thai_period_start:input.period_start,thai_period_end:input.period_end,
      foreign_tax_base:basis[key+'foreign_tax_base'],thai_return_filed_on:basis[key+'filing_known']===true?basis[key+'thai_return_filed_on']:null,
      actual_period_basis_and_payment_evidence_verified:basis[key+'verified']};
     for(const [name] of [...periodDates,...periodAmounts])allocation[name]=basis[key+name];
     periods.push({evidence_reference:basis[key+'reference'],allocation});
    }
    return {basis:row,annual_allowable_expenses:basis[prefix+'annual_expenses'],foreign_tax_in_annual_expenses:basis[prefix+'deducted_tax'],business_tax_periods:periods};
   })};
 }
 for(const key of Object.keys(basis))if(key.startsWith('thfc_'))delete basis[key];
 return basis;
}
