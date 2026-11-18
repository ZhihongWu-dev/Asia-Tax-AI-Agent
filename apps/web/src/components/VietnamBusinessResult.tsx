import { businessCategories } from '../vietnam-business-assessment';

export default function VietnamBusinessResult({result,index}:{result:Record<string,unknown>;index:number}) {
  const say=(zh:string,en:string)=>index?en:zh;
  const rows=Array.isArray(result.activities)?result.activities as Record<string,unknown>[]:[];
  return <section aria-label={say('经营所得计算明细','Business-income calculation details')}>
    <p>{result.method==='profit'?say('利润法','Profit method'):say('收入比例法','Revenue percentage method')}
      {say('；仅含居民境内普通经营所得税，不含房产出租和增值税。','; resident ordinary domestic business PIT only, excluding property rent and VAT.')}</p>
    {result.next_year_profit_method_required===true&&<p role="status">{say('本年收入超过30亿越南盾，次年须转入利润法。','Annual revenue exceeded VND 3bn; profit method is required next year.')}</p>}
    {result.method_continuity_review_required===true&&<p>{say('后续年度须继续核对利润法两年延续要求。','Check the two-year profit-method continuity requirement for subsequent years.')}</p>}
    <dl>{[
      ['annual_business_revenue',say('全年经营收入','Annual business revenue')],
      ['tax_before_relief',say('年度减税前税额','Tax before annual relief')],
      ['unused_revenue_deduction',say('未分配的年度收入扣除','Unallocated annual revenue deduction')],
    ].filter(([key])=>result[key]!==null&&result[key]!==undefined).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String(result[key])}</dd></div>)}</dl>
    {rows.map((row,n)=><section key={n} aria-label={say(`经营项目 ${n+1}`,`Business activity ${n+1}`)}>
      <h5>{businessCategories.find(([key])=>key===row.category)?.[1][index]}</h5>
      <dl>{[
        ['revenue',say('已保存收入','Saved revenue')],
        ['allocated_revenue_deduction',say('分配的收入扣除','Allocated revenue deduction')],
        ['taxable_revenue',say('计税收入','Taxable revenue')],
        ['tax_before_relief',say('减税前税额','Tax before relief')],
      ].filter(([key])=>row[key]!==undefined).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String(row[key])}</dd></div>)}</dl>
    </section>)}
  </section>;
}
