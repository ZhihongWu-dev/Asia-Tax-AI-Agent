export default function SingaporeForeignResult({result,index}:{result:Record<string,unknown>;index:number}){
 const say=(zh:string,en:string)=>index?en:zh;
 const credit=result.foreign_credit as {sources:Array<{source_id:string;country:string;singapore_tax_limit:string;eligible_foreign_tax:string;pool_elected:boolean;individual_credit:string|null}>;pooled_credit:string;pooled_singapore_tax_limit:string};
 return <section aria-label={say('新加坡境外抵免明细','Singapore foreign credit details')}>
  <h4>{say('新加坡境外抵免明细','Singapore foreign credit details')}</h4>
  <p>{say('先抵免，再计算企业税回扣；现金补助单独列示，不重复冲减余额。金额为申报取整前值。','Credit precedes the CIT rebate. The separate cash grant is not deducted again from the balance. Values precede filing rounding.')}</p>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['来源|Source','国家|Country','限额|Limit','境外税|Foreign tax','抵免|Credit'].map(s=><th key={s}>{s.split('|')[index]}</th>)}</tr></thead><tbody>
  {credit.sources.map((row,n)=><tr key={n}><td>{row.source_id}</td><td>{row.country.toUpperCase()}</td><td>{row.singapore_tax_limit}</td><td>{row.eligible_foreign_tax}</td><td>{row.pool_elected?say('计入汇总','Included in pool'):row.individual_credit}</td></tr>)}
  </tbody></table></div>
  <dl>{[['汇总限额','Pooled limit',credit.pooled_singapore_tax_limit],['汇总抵免','Pooled credit',credit.pooled_credit],['企业税回扣','CIT rebate',result.cit_rebate],['单列现金补助','Separate cash grant',result.cash_grant_separate]].map(([zh,en,value])=><div key={String(en)}><dt>{say(String(zh),String(en))}</dt><dd>{String(value)}</dd></div>)}</dl>
 </section>;
}
