type Balances=Record<string,string>;
type LimitRow={identifier:string;period_start:string;capacity_matched_to_current_excess:Balances;excess_matched_to_current_capacity:Balances;expired_capacity:Balances;next_period_capacity:Balances;expired_excess:string;next_period_excess:string};
type LevyRow={identifier:string;period_start:string;opening:Balances;used:Balances;expired:Balances;next_period:Balances};
export default function JapanOsakaHistoryResult({result,index}:{result:Record<string,unknown>;index:number}) {
 const say=(zh:string,en:string)=>index?en:zh;
 const rows=result.settlements as Record<string,Record<string,string>>;
 const labels:Record<string,string[]>={corporation:['法人税','Corporation tax'],local_corporation:['地方法人税','Local corporation tax'],defence:['防卫特别法人税','Defence corporation tax'],enterprise:['事业税','Enterprise tax'],special_enterprise:['特别法人事业税','Special enterprise tax'],prefectural_inhabitant:['府民税法人税割','Prefectural corporation levy'],city_inhabitant:['市民税法人税割','City corporation levy'],prefectural_capitation:['府民税均等割','Prefectural capitation'],city_capitation:['市民税均等割','City capitation']};
 const matching=result.history_matching as {periods:LimitRow[];current_capacity_remaining:Balances;current_excess_remaining:string};
 const levies=result.local_levy_history as LevyRow[];
 const fresh=result.current_period_levy_shortfall as {balances:Balances};
 const next=result.next_period_levy_shortfall as Balances;
 const triple=(b:Balances)=>['national','prefectural','municipal'].map(k=>b[k]).join(' / ');
 const pair=(b:Balances)=>['prefectural','municipal'].map(k=>b[k]).join(' / ');
 return <section aria-label={say('日本大阪历史抵免年度结算','Japan Osaka annual settlement with historical credits')}>
  <h4>{say('日本大阪历史抵免年度结算','Japan Osaka annual settlement with historical credits')}</h4>
  <p>{say('按已确认的历史申报和期初余额计算。限额与地方税未抵免额分别记账；各项补税和退款不互相冲抵。','Calculated from confirmed historical returns and opening balances. Statutory limits and local levy shortfalls have separate ledgers; payments and refunds remain separate.')}</p>
  <p>{say('年度税费合计：','Total annual liability: ')}{String(result.total_annual_liability)} · {say('应补合计：','Total payable: ')}{String(result.total_payable)} · {say('应退合计：','Total refundable: ')}{String(result.total_refundable)}</p>
  <p>{say('合资格抵免不足额退款：','Eligible credit refund: ')}{String(result.total_foreign_credit_refund)} · {say('预缴退款：','Interim refund: ')}{String(result.total_interim_refund)}</p>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['税费|Tax','年度税额|Annual liability','实际抵减税额|Credit applied to tax','预缴|Interim','应补|Payable','应退|Refundable'].map(t=><th key={t}>{t.split('|')[index]}</th>)}</tr></thead><tbody>
   {Object.entries(rows).map(([key,row])=><tr key={key}><td>{labels[key]?.[index]||key}</td><td>{row.annual_liability}</td><td>{row.foreign_credit_applied_to_tax??row.total_foreign_credit_applied??'—'}</td>{['interim_return_liability','payable','refundable'].map(k=><td key={k}>{row[k]}</td>)}</tr>)}
  </tbody></table></div>
  <h5>{say('历史限额与超限税额（国税／府民税／市民税）','Historical capacity and excess (national / prefectural / municipal)')}</h5>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['编号／开始日|Reference / start','历史限额已用|Historical capacity used','历史超限税额已用|Historical excess used','限额到期|Capacity expired','限额下期|Next capacity','超限税额到期／下期|Excess expired / next'].map(t=><th key={t}>{t.split('|')[index]}</th>)}</tr></thead><tbody>
   {matching.periods.map(row=><tr key={row.identifier}><td>{row.identifier} / {row.period_start}</td><td>{triple(row.capacity_matched_to_current_excess)}</td><td>{triple(row.excess_matched_to_current_capacity)}</td><td>{triple(row.expired_capacity)}</td><td>{triple(row.next_period_capacity)}</td><td>{row.expired_excess} / {row.next_period_excess}</td></tr>)}
  </tbody></table></div>
  <p>{say('本期剩余限额：','Remaining current capacity: ')}{triple(matching.current_capacity_remaining)}</p>
  <p>{say('本期剩余超限税额：','Remaining current excess foreign tax: ')}{matching.current_excess_remaining}</p>
  <h5>{say('地方税未抵免台账（府民税／市民税）','Local levy-shortfall ledger (prefectural / municipal)')}</h5>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['编号／开始日|Reference / start','期初|Opening','已用|Used','到期|Expired','下期|Next period'].map(t=><th key={t}>{t.split('|')[index]}</th>)}</tr></thead><tbody>
   {levies.map(row=><tr key={row.identifier}><td>{row.identifier} / {row.period_start}</td>{[row.opening,row.used,row.expired,row.next_period].map((v,n)=><td key={n}>{pair(v)}</td>)}</tr>)}
  </tbody></table></div>
  <p>{say('本期新增未抵免额：','New current levy shortfall: ')}{pair(fresh.balances)}</p>
  <p>{say('下期未抵免余额合计：','Total next-period levy shortfall: ')}{pair(next)}</p>
 </section>;
}
