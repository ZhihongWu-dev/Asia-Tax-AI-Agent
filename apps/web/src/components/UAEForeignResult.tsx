export default function UAEForeignResult({result,index}:{result:Record<string,unknown>;index:number}){
 const say=(zh:string,en:string)=>index?en:zh;
 const rows=result.source_credits as Array<Record<string,string>>;
 return <section aria-label={say('阿联酋境外抵免明细','UAE foreign credit details')}>
  <h4>{say('阿联酋境外抵免明细','UAE foreign credit details')}</h4>
  <p>{say('每项所得分别限额；未用境外税额不可跨来源互抵或结转，也不可作为费用扣除。金额为申报取整前值。','Each income has its own limit. Unused foreign tax cannot offset another source, carry forward/back or become an expense deduction. Values precede filing rounding.')}</p>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['来源|Source','国家|Country','净所得|Net income','限额|Limit','已用抵免|Credit used','不可结转|Forfeited'].map(label=><th key={label}>{label.split('|')[index]}</th>)}</tr></thead><tbody>
  {rows.map(row=><tr key={row.source_id}>{['source_id','country','net_taxable_income','credit_limit','credit_used','forfeited_excess'].map(key=><td key={key}>{row[key]}</td>)}</tr>)}
  </tbody></table></div>
  <p>{say('不可结转余额合计：','Total forfeited excess: ')}{String(result.forfeited_excess)}</p>
 </section>;
}
