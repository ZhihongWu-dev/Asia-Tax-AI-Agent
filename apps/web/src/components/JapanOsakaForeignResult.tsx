export default function JapanOsakaForeignResult({result,index}:{result:Record<string,unknown>;index:number}) {
 const say=(zh:string,en:string)=>index?en:zh;
 const rows=result.settlements as Record<string,Record<string,string>>;
 const labels:Record<string,string[]>={corporation:['法人税','Corporation tax'],local_corporation:['地方法人税','Local corporation tax'],defence:['防卫特别法人税','Defence corporation tax'],enterprise:['事业税','Enterprise tax'],special_enterprise:['特别法人事业税','Special enterprise tax'],prefectural_inhabitant:['府民税法人税割','Prefectural corporation levy'],city_inhabitant:['市民税法人税割','City corporation levy'],prefectural_capitation:['府民税均等割','Prefectural capitation'],city_capitation:['市民税均等割','City capitation']};
 const credit=result.current_foreign_credit as {foreign_tax_above_all_current_limits:string;prefectural:Record<string,string>;municipal:Record<string,string>;current_unused_capacity_before_history?:Record<string,string>;unused_national_limits_not_in_carry_capacity?:string};
 return <section aria-label={say('日本大阪跨境企业结算','Japan Osaka cross-border company settlement')}>
  <h4>{say('日本大阪跨境企业结算','Japan Osaka cross-border company settlement')}</h4>
  <p>{say('各项补退税分别结算；本期标准限额，不包含历史结转或其他优惠。','Each tax settles separately; current standard limits, excluding history and competing reliefs.')}</p>
  <p>{say('本期税费合计：','Total annual liability: ')}{String(result.total_annual_liability)} · {say('分别应补合计：','Total payable: ')}{String(result.total_payable)} · {say('分别应退合计：','Total refundable: ')}{String(result.total_refundable)}</p>
  <div style={{overflowX:'auto'}}><table><thead><tr>{['税费|Tax','本期税额|Annual liability','抵免|Credit','预缴|Interim liability','应补|Payable','应退|Refundable'].map(t=><th key={t}>{t.split('|')[index]}</th>)}</tr></thead><tbody>
   {Object.entries(rows).map(([key,row])=><tr key={key}><td>{labels[key]?.[index]||key}</td>{['annual_liability','current_foreign_credit','interim_return_liability','payable','refundable'].map(k=><td key={k}>{row[k]??'—'}</td>)}</tr>)}
  </tbody></table></div>
  <p>{say('超过本期全部限额（未批准结转）：','Above all current limits (carryforward not approved): ')}{credit.foreign_tax_above_all_current_limits}</p>
  {(['prefectural','municipal'] as const).map(key=><p key={key}>{key==='prefectural'?say('府民税','Prefectural'):say('市民税','Municipal')}{say('税额不足未抵免／分摊舍入余额：',' levy shortfall / allocation rounding residual: ')}{credit[key].unrelieved_due_to_levy_shortfall} / {credit[key].unallocated_rounding_residual}</p>)}
  {credit.current_unused_capacity_before_history&&<>
   <h5>{say('本期未用限额（结转资格待核验）','Current unused capacity (carryforward eligibility unverified)')}</h5>
   <p>{say('国税／府民税／市民税：','National / prefectural / municipal: ')}{['national','prefectural','municipal'].map(k=>credit.current_unused_capacity_before_history![k]).join(' / ')}</p>
   <p>{say('未纳入国税结转限额的地方法人税及防卫税余额：','Unused local-corporation and defence limits excluded from national carry capacity: ')}{credit.unused_national_limits_not_in_carry_capacity}</p>
  </>}
 </section>;
}
