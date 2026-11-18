import {taxJurisdictions,type TaxJurisdiction} from '../income-tax';
export default function ChinaForeignResult({result,index}:{result:Record<string,unknown>;index:number}){
 const say=(zh:string,en:string)=>index?en:zh;
 const name=(code:unknown)=>taxJurisdictions[code as TaxJurisdiction]?.[index]??String(code);
 const pools=result.pools as Record<string,unknown>[];
 return <section aria-label={say('境外抵免明细','Foreign credit details')}><h4>{say('境外抵免明细','Foreign credit details')}</h4>
 <p>{say('仅普通直接抵免；历史余额先抵最早到期年度。当年到期未用余额不能带入下一年。','Ordinary direct credit only. Oldest eligible excess is used first. Unused amounts expiring this year cannot carry into next year.')}</p>
 <p>{say('采用方式：','Method: ')}{result.method==='pooled'?say('综合抵免','Pooled foreign income'):say('分国抵免','Per country')}</p>
 {pools.map(pool=><section key={String(pool.pool)} aria-label={pool.pool==='all_foreign'?say('综合抵免池','Pooled credit'):name(pool.pool)}><h5>{pool.pool==='all_foreign'?say('综合抵免池','Pooled credit'):name(pool.pool)}</h5><dl>
 {([['taxable_income','应税所得','Taxable income'],['credit_limit','抵免限额','Credit limit'],['current_credit_used','使用当年税额','Current credit used'],['current_excess','当年超限额余额','Current excess'],['prior_credit_used','使用历史余额','Prior credit used'],['allowed_credit','本期抵免合计','Total credit allowed'],['remaining_credit_capacity','剩余抵免空间','Remaining credit capacity']] as const).map(([key,zh,en])=><div key={key}><dt>{say(zh,en)}</dt><dd>{String(pool[key])}</dd></div>)}
 </dl><p>{say('当年新增余额最后可用年度：','New excess last usable year: ')}{String(pool.current_excess_last_usable_year)}</p>
 {(pool.carryforward_history as Record<string,unknown>[]).map(row=><div key={String(row.country)+String(row.origin_year)}><h6>{name(row.country)} {String(row.origin_year)}</h6><dl>
 {([['credit_used','本期使用','Used this year'],['expired_amount','本期前已失效','Previously expired'],['expires_after_current_year','本期结束失效','Expires after current year'],['next_year_carryforward','可带入下一年','Next-year carryforward']] as const).map(([key,zh,en])=><div key={key}><dt>{say(zh,en)}</dt><dd>{String(row[key])}</dd></div>)}
 </dl></div>)}
 </section>)}
 <h5>{say('逐国税基核对','Country basis reconciliation')}</h5>
 {(result.country_basis_reconciliation as Record<string,unknown>[]).map(row=><p key={String(row.country)}>{name(row.country)}: {say('税基','Taxable income')} {String(row.taxable_income)}; {say('已缴境外税额','Foreign tax paid')} {String(row.foreign_tax_paid)}; {say('核定直接税额','Eligible direct tax')} {String(row.eligible_direct_tax)}</p>)}
 </section>;
}
