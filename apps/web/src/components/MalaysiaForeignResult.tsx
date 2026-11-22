export default function MalaysiaForeignResult({result,index}:{result:Record<string,unknown>;index:number}){
 const say=(zh:string,en:string)=>index?en:zh;
 const rows=result.source_credits as Array<Record<string,string>>;
 return <section aria-label={say('马来西亚境外抵免明细','Malaysia foreign credit details')}>
  <h4>{say('马来西亚境外抵免明细','Malaysia foreign credit details')}</h4>
  <p>{say('逐项抵免尚未应用总税额上限；总额调减另列。单边抵免另受境外税额一半限制。未抵免余额不结转，金额为申报取整前值。','Source credits precede the overall tax cap; its reduction is shown separately. Unilateral credit is also capped at half the foreign tax. Unrelieved balances do not carry forward. Values precede filing rounding.')}</p>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['来源|Source','征税国家|Taxing country','方法|Method','法定所得|Statutory income','本国税上限|Malaysian tax limit','总额限制前抵免|Credit before overall cap'].map(label=><th key={label}>{label.split('|')[index]}</th>)}</tr></thead><tbody>
  {rows.map(row=><tr key={`${row.source_id}-${row.taxing_country}`}><td>{row.source_id}</td><td>{row.taxing_country.toUpperCase()}</td><td>{row.method==='bilateral'?say('双边','Bilateral'):say('单边','Unilateral')}</td>{['allocated_statutory_income','malaysian_tax_limit','credit_before_overall_cap'].map(key=><td key={key}>{row[key]}</td>)}</tr>)}
  </tbody></table></div>
  <p>{say('总税额上限调减：','Overall cap reduction: ')}{String(result.overall_cap_reduction)}</p>
  <p>{say('境外抵免合计：','Total foreign credit: ')}{String(result.allowed_foreign_tax_credit)}</p>
  <p>{say('未获抵免境外税额：','Unrelieved foreign tax: ')}{String(result.unrelieved_foreign_tax)}</p>
 </section>;
}
