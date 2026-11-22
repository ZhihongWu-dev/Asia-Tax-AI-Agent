export default function VietnamForeignResult({result,index}:{result:Record<string,unknown>;index:number}) {
 const say=(zh:string,en:string)=>index?en:zh;
 const rows=result.source_credits as Array<Record<string,string>>;
 const methods:Record<string,string[]>={domestic:['境内','Domestic'],treaty_direct_paid:['协定实缴税','Treaty paid tax'],singapore_deemed_floor:['新加坡视同税下限','Singapore deemed floor'],indonesia_deemed_replacement:['印尼视同税','Indonesia deemed replacement']};
 return <section aria-label={say('越南境外抵免明细','Vietnam foreign credit details')}>
  <h4>{say('越南境外抵免明细','Vietnam foreign credit details')}</h4>
  <p>{say('视同税与实缴税分开列示，抵免不超过同项越南税额。超限额不自动批准结转。金额为申报取整前值。','Deemed and paid taxes are separate; credit is capped at Vietnamese tax on the same income. Excess does not automatically establish a carryforward. Before filing rounding.')}</p>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['来源|Source','国家|Country','方法|Method','净所得|Net income','实缴税|Paid tax','抵免依据|Credit basis','限额|Limit','已用抵免|Credit used'].map(label=><th key={label}>{label.split('|')[index]}</th>)}</tr></thead><tbody>
   {rows.map(row=><tr key={row.source_id}>{['source_id','country','method','net_taxable_income','foreign_tax_paid','credit_basis','vietnam_same_income_limit','allowed_credit'].map(key=><td key={key}>{key==='method'?methods[row.method]?.[index]||row.method:row[key]}</td>)}</tr>)}
  </tbody></table></div>
  <p>{say('境外抵免合计：','Total foreign credit: ')}{String(result.allowed_foreign_tax_credit)}</p>
 </section>;
}
