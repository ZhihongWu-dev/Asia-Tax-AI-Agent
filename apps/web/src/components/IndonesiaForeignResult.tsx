export default function IndonesiaForeignResult({result,index}:{result:Record<string,unknown>;index:number}){
 const say=(zh:string,en:string)=>index?en:zh;
 const rows=result.source_credits as Array<Record<string,string|null>>;
 return <section aria-label={say('印尼境外抵免明细','Indonesia foreign credit details')}>
  <h4>{say('印尼境外抵免明细','Indonesia foreign credit details')}</h4>
  <p>{say('按国家和所得类别限额；逐项抵免尚未应用总税额上限。未获抵免税款不得作为费用或申请退税。以前已抵免税款的补回另列。','Limits apply by country and income type; source credits precede the overall cap. Unrelieved foreign tax cannot become an expense deduction or refund. Recapture of previously credited tax is separate.')}</p>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['国家|Country','所得类别|Income type','境外净所得|Foreign net income','条约上限|Treaty ceiling','本国税上限|Indonesian tax limit','总额限制前抵免|Credit before overall cap'].map(label=><th key={label}>{label.split('|')[index]}</th>)}</tr></thead><tbody>
  {rows.map(row=><tr key={`${row.country}-${row.category}`}>{['country','category','net_taxable_income','treaty_permitted_tax','indonesian_tax_limit','credit_before_overall_cap'].map(key=><td key={key}>{row[key]??say('不适用','Not applicable')}</td>)}</tr>)}
  </tbody></table></div>
  {([['allowed_foreign_tax_credit','境外抵免合计','Total foreign credit'],['overall_cap_reduction','总额限制调减','Overall cap reduction'],['prior_credit_recapture','以前抵免补回','Prior-credit recapture']] as const).map(([key,zh,en])=><p key={key}>{say(zh,en)}: {String(result[key])}</p>)}
 </section>;
}
