export default function ThaiCompanyForeignResult({result,index}:{result:Record<string,unknown>;index:number}){
 const say=(zh:string,en:string)=>index?en:zh;
 const reconciliation=result.foreign_credit_reconciliation as {country_reconciliation:Array<Record<string,unknown>&{country:string;business_tax_period_allocations?:Array<{evidence_reference:string;payment_date:string;thai_period_end:string;allocated_tax_before_credit_limits:string;amendment_required:boolean|null}>}>};
 const allocations=reconciliation.country_reconciliation.flatMap(row=>(row.business_tax_period_allocations||[]).map(entry=>({country:row.country,...entry})));
 return <section aria-label={say('泰国企业境外抵免核对','Thai company foreign credit reconciliation')}>
  <h4>{say('泰国企业境外抵免核对','Thai company foreign credit reconciliation')}</h4>
  <p>{say('采用已确认的最终费用与第300号法令口径。抵免部分不得同时作为费用扣除；费用资格并未自动认定。','Uses confirmed final expenses and the RD300 election. Credited tax cannot also be deducted; expense eligibility is not inferred.')}</p>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['国家|Country','境外已缴税|Foreign tax paid','年度费用|Annual expenses','费用中的境外税|Foreign tax in expenses','抵免额|Exemption','未抵免未扣除税额|Uncredited and undeducted tax'].map(label=><th key={label}>{label.split('|')[index]}</th>)}</tr></thead><tbody>
   {reconciliation.country_reconciliation.map(row=><tr key={row.country}>{['country','foreign_tax_paid','annual_allowable_expenses','foreign_tax_in_annual_expenses','rd300_exemption','uncredited_and_undeducted_foreign_tax'].map(key=><td key={key}>{String(row[key])}</td>)}</tr>)}
  </tbody></table></div>
  {allocations.length>0&&<section aria-label={say('经营税款期间分摊','Business tax period allocations')}>
   <h5>{say('经营税款期间分摊','Business tax period allocations')}</h5>
   {allocations.map(entry=><p key={`${entry.country}-${entry.evidence_reference}`}>
    {entry.country.toUpperCase()} / {entry.evidence_reference}: {entry.allocated_tax_before_credit_limits}; {say('所得期间结束日','Income period end')}: {entry.thai_period_end}; {say('税款支付日','Tax payment date')}: {entry.payment_date}; {say('需更正原申报','Original return amendment required')}: {entry.amendment_required===null?say('待确认原申报日期','Original filing date unknown'):entry.amendment_required?say('是','Yes'):say('否','No')}
   </p>)}
  </section>}
 </section>;
}
