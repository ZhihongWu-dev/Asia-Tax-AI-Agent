import {taxJurisdictions,type TaxJurisdiction} from '../income-tax';
export default function PersonalForeignResult({result,index}:{result:Record<string,unknown>;index:number}){
 const say=(zh:string,en:string)=>index?en:zh;
 return <section aria-label={say('个人境外抵免明细','Personal foreign credit details')}><h4>{say('个人境外抵免明细','Personal foreign credit details')}</h4>
 <p>{say('分国抵免；先用当年税额，再用同国最早到期历史余额。本年到期未用金额不得结转。','Per-country credits: current tax first, then oldest eligible same-country excess. Unused amounts expiring this year cannot carry forward.')}</p>
 {(result.country_limits as Record<string,unknown>[]).map(row=><section key={String(row.country)}><h5>{taxJurisdictions[row.country as TaxJurisdiction][index]}</h5><dl>
 {([['comprehensive_credit_limit','综合所得限额','Comprehensive credit limit'],['business_credit_limit','经营所得限额','Business credit limit'],['other_category_credit_limit','其他分类所得限额','Other category credit limit'],['credit_limit','国别限额合计','Country credit limit'],['allowed_credit','本期抵免','Credit allowed'],['current_excess','当年超限额','Current excess']] as const).map(([key,zh,en])=><div key={key}><dt>{say(zh,en)}</dt><dd>{String(row[key])}</dd></div>)}
 </dl>{(row.carryforward_history as Record<string,unknown>[]).map(h=><div key={String(h.origin_year)}><h6>{String(h.origin_year)}</h6><dl>{([['credit_used','本期使用','Used this year'],['expired_amount','本期前已失效','Previously expired'],['expires_after_current_year','本期结束失效','Expires after current year'],['next_year_carryforward','可带入下一年','Next-year carryforward']] as const).map(([k,zh,en])=><div key={k}><dt>{say(zh,en)}</dt><dd>{String(h[k])}</dd></div>)}</dl></div>)}</section>)}
 </section>;
}
