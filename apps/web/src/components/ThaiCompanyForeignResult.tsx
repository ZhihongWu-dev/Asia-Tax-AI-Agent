export default function ThaiCompanyForeignResult({result,index}:{result:Record<string,unknown>;index:number}){
 const say=(zh:string,en:string)=>index?en:zh;
 const reconciliation=result.foreign_credit_reconciliation as {country_reconciliation:Array<Record<string,string>>};
 return <section aria-label={say('泰国企业境外抵免核对','Thai company foreign credit reconciliation')}>
  <h4>{say('泰国企业境外抵免核对','Thai company foreign credit reconciliation')}</h4>
  <p>{say('采用已确认的最终费用与第300号法令口径。抵免部分不得同时作为费用扣除；费用资格并未自动认定。','Uses confirmed final expenses and the RD300 election. Credited tax cannot also be deducted; expense eligibility is not inferred.')}</p>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['国家|Country','境外已缴税|Foreign tax paid','年度费用|Annual expenses','费用中的境外税|Foreign tax in expenses','抵免额|Exemption','未抵免未扣除税额|Uncredited and undeducted tax'].map(label=><th key={label}>{label.split('|')[index]}</th>)}</tr></thead><tbody>
   {reconciliation.country_reconciliation.map(row=><tr key={row.country}>{['country','foreign_tax_paid','annual_allowable_expenses','foreign_tax_in_annual_expenses','rd300_exemption','uncredited_and_undeducted_foreign_tax'].map(key=><td key={key}>{row[key]}</td>)}</tr>)}
  </tbody></table></div>
 </section>;
}
