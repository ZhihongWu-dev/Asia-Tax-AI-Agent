export default function IndiaForeignResult({result,index}:{result:Record<string,unknown>;index:number}){
 const say=(zh:string,en:string)=>index?en:zh;
 const credit=result.foreign_credit as {source_credits:Array<Record<string,string|null>>};
 return <section aria-label={say('印度企业境外抵免明细','Indian company foreign credit details')}>
  <h4>{say('印度企业境外抵免明细','Indian company foreign credit details')}</h4>
  <p>{say('按核定来源税额分别计算普通税制及最低税额抵免；实际采用的抵免额另列。余额尚未加入利息及费用。','Normal and MAT credits use verified source tax attribution; the credit actually applied is shown separately. The balance excludes interest and fees.')}</p>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['来源|Source','国家|Country','境外已缴税|Foreign tax paid','排除争议税|Disputed tax excluded','普通抵免|Normal credit','最低税额抵免|Section206 credit'].map(label=><th key={label}>{label.split('|')[index]}</th>)}</tr></thead><tbody>
   {credit.source_credits.map(row=><tr key={row.source_id}>{['source_id','country','foreign_tax_paid_inr','disputed_tax_excluded_inr','normal_credit','section206_credit'].map(key=><td key={key}>{row[key]??say('不适用','Not applicable')}</td>)}</tr>)}
  </tbody></table></div>
  <p>{say('本次适用抵免','Foreign credit applied')}: {String(result.allowed_foreign_tax_credit)}</p>
  <p>{say('适用最低税额','MAT applies')}: {result.mat_applies?say('是','Yes'):say('否','No')}</p>
 </section>;
}
