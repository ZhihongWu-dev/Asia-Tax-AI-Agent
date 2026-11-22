import type {BasisField,IncomePolicy} from './income-assessment';
import type {IncomeTaxInput} from './income-tax';
import {japanOsakaForeignPolicy,japanOsakaForeignBasis} from './japan-osaka-foreign';

const limitChecks=[
 ['original_returns_entitlement_prior_usage_and_continuous_filings_verified','已核实原申报、历史限额资格、已用金额和连续申报','Original returns, statutory entitlement, prior usage and continuous filings verified'],
 ['no_foreign_tax_expense_elections_reductions_groups_or_reorganizations_verified','无境外税费用扣除选择、减额、集团或重组','No foreign-tax expense elections, reductions, groups or reorganizations'],
] as const;
const levyChecks=[
 ['original_local_returns_prior_usage_and_continuous_filings_verified','已核实原地方申报、未抵免余额、已用金额及连续申报','Original local returns, shortfalls, prior usage and continuous filings verified'],
 ['single_unchanged_prefecture_and_municipality_verified','历史至今为同一府及市，申报辖区未变化','Same single prefecture and municipality throughout history'],
 ['no_amended_return_credit_adjustments_groups_or_reorganizations_verified','无更正申报抵免调整、集团或重组','No amended-return credit adjustments, groups or reorganizations'],
] as const;
const localCheck='no_other_local_credits_additions_losses_or_treaty_amendments_verified';
const nationalCheck='no_other_tax_credits_or_additions_verified';
function count(value:unknown):number {
 const n=Number(value);if(!Number.isInteger(n)||n<0||n>200)throw new Error('Invalid history count');return n;
}

export function japanOsakaForeignHistoryPolicy(input:IncomeTaxInput,values:Record<string,string>):IncomePolicy {
 const old=japanOsakaForeignPolicy(input,values);
 const removed=new Set(['no_other_local_credits_additions_history_losses_or_treaty_amendments_verified','no_other_tax_credits_additions_or_history_verified']);
 const fields:BasisField[]=old.fields.filter(f=>!removed.has(f.key));
 fields.push({key:'jph_limit_count',label:['历史限额／超限台账期间数（无则0）','Statutory history period count (0 if none)'],integer:true,min:0,max:200},
  {key:'jph_levy_count',label:['地方税未抵免台账期间数（无则0）','Local shortfall period count (0 if none)'],integer:true,min:0,max:200});
 for(const kind of ['limit','levy'] as const){
  let size=0;try{size=count(values[`jph_${kind}_count`]||'0');}catch{/* Submission validates the count. */}
  for(let n=0;n<size;n++){
   const key=`jph_${kind}_${n}_`,zh=kind==='limit'?`限额历史${n+1}`:`地方未抵免历史${n+1}`,en=kind==='limit'?`Statutory history ${n+1}`:`Local shortfall ${n+1}`;
   fields.push({key:key+'id',label:[zh+'：编号',en+': reference'],text:true});
   for(const [suffix,z,e] of [['start','期间开始','period start'],['end','期间结束','period end']])fields.push({key:key+suffix,label:[zh+'：'+z,en+': '+e],date:true,dateMin:'1900-01-01',dateMax:input.period_start});
   const amounts=kind==='limit'?[['national','国税未用限额','national capacity'],['prefectural','府民税未用限额','prefectural capacity'],['municipal','市民税未用限额','municipal capacity'],['excess','超限税额','excess foreign tax']]:[['prefectural','府民税未抵免额','prefectural shortfall'],['municipal','市民税未抵免额','municipal shortfall']];
   for(const [suffix,z,e] of amounts)fields.push({key:key+suffix,label:[zh+'：'+z,en+': '+e]});
  }
 }
 for(const [key,zh,en] of [...limitChecks,...levyChecks,
  [localCheck,'无其他地方抵免、加算、亏损或协定更正','No other local credits, additions, losses or treaty amendments'],
  [nationalCheck,'无其他国税抵免或加算','No other national credits or additions']])fields.push({key,label:[zh,en],boolean:true});
 return {id:'jp_osaka_company_foreign_history_starting_2026',label:['日本大阪企业境外抵免及历史余额（2026年开始）','Japan Osaka foreign credits with history (starting 2026)'],fields,
  notice:['全年全部办公室在大阪市、历史申报辖区未变化的普通企业。分别填写历史限额／超限税额和地方税未抵免余额，均为扣除以前已使用金额后的期初余额。旧期间优先；过期余额另列。九项税费补退分别结算。',
   'Ordinary full-year Osaka-city offices with unchanged historical filing jurisdictions. Enter statutory capacity/excess and local levy shortfalls separately, as opening balances after prior usage. Older periods apply first; expired balances remain separate. Nine taxes settle payments and refunds separately.']};
}

export function japanOsakaForeignHistoryBasis(flat:Record<string,unknown>,input:IncomeTaxInput):Record<string,unknown> {
 const basis=japanOsakaForeignBasis(flat,input);
 delete basis.no_other_tax_credits_additions_or_history_verified;
 basis[nationalCheck]=flat[nationalCheck];
 const local=basis.local_workpaper as Record<string,unknown>;
 delete local.no_other_local_credits_additions_history_losses_or_treaty_amendments_verified;
 local[localCheck]=flat[localCheck];
 const periods=(kind:'limit'|'levy')=>Array.from({length:count(flat[`jph_${kind}_count`])},(_,n)=>{
  const key=`jph_${kind}_${n}_`;
  const origin={identifier:flat[key+'id'],period_start:flat[key+'start'],period_end:flat[key+'end']};
  return kind==='limit'?{...origin,unused_capacity:{national:flat[key+'national'],prefectural:flat[key+'prefectural'],municipal:flat[key+'municipal']},excess_foreign_tax:flat[key+'excess']}:
   {...origin,prefectural:flat[key+'prefectural'],municipal:flat[key+'municipal']};
 });
 basis.limit_history={periods:periods('limit'),...Object.fromEntries(limitChecks.map(([key])=>[key,flat[key]]))};
 basis.levy_history={periods:periods('levy'),prefectural_filing_id:'Osaka prefecture',municipal_filing_id:'Osaka city',...Object.fromEntries(levyChecks.map(([key])=>[key,flat[key]]))};
 return basis;
}
