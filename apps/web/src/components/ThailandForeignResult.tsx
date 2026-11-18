type Row = Record<string,unknown>;

export default function ThailandForeignResult({result,index}:{result:Row;index:number}) {
  const say=(zh:string,en:string)=>index?en:zh;
  const credit=result.foreign_credit as {total_assessable_income:string;countries:Row[]};
  const reconciliation=result.foreign_income_reconciliation as {
    pools:Row[];remittance_reconciliation:{remitted_income:string;included_before_relief:string;excluded_from_section41_remittance:string}
  };
  const receipts=reconciliation.remittance_reconciliation;
  const values=(row:Row, fields:[string,string,string][])=>
    <dl>{fields.map(([key,zh,en])=><div key={key}><dt>{say(zh,en)}</dt><dd>{String(row[key])}</dd></div>)}</dl>;
  return <section aria-label={say('泰国境外所得核对明细','Thai foreign income reconciliation')}>
    <h5>{say('汇入与抵免明细','Remittance and credit details')}</h5>
    <p>{say('下列金额均为泰铢、申报取整前金额。抵免使用已确认的协定资格和税款依据，不代表税务机关已批准。','Amounts are THB before return rounding. Credits use the confirmed treaty entitlement and tax evidence; they are not tax-authority approval.')}</p>
    {values({...receipts,total_assessable_income:credit.total_assessable_income},[
      ['remitted_income','本年汇入收入合计','Total income remitted this year'],
      ['included_before_relief','纳入本年计税的境外收入','Foreign income included this year'],
      ['excluded_from_section41_remittance','未纳入本年计税的汇入收入','Remitted income excluded this year'],
      ['total_assessable_income','抵免上限分母：扣除前全部应评税收入','Credit-limit denominator: all assessable income before deductions']])}
    {credit.countries.map(row=><section key={String(row.country)} aria-label={`${say('来源国','Source country')} ${String(row.country).toUpperCase()}`}>
      <h6>{say('来源国','Source country')} {String(row.country).toUpperCase()}</h6>
      {values(row,[['remitted_assessable_income','该国纳入计税的汇入收入','Included remitted income from this country'],
        ['eligible_attributable_tax','归属于汇入收入的合资格境外税','Eligible foreign tax attributable to remitted income'],
        ['credit_limit','该国抵免上限','Country credit limit'],
        ['allowable_foreign_credit','该国可用抵免','Allowable credit for this country'],
        ['unused_foreign_tax','超过上限未使用的境外税','Foreign tax unused above the limit']])}
    </section>)}
    {reconciliation.pools.map(row=><section key={String(row.pool_id)} aria-label={`${say('收入批次','Income pool')} ${String(row.pool_id)}`}>
      <h6>{say('收入批次','Income pool')} {String(row.pool_id)}</h6>
      <p>{say('已保存收入','Saved income')} {Number(row.income_index)+1} · {String(row.country).toUpperCase()}</p>
      {values(row,[['original_foreign_income','原始境外收入','Original foreign earnings'],
        ['original_foreign_tax_paid','原始收入已缴境外税','Foreign tax paid on original earnings'],
        ['previously_remitted_income','以前年度已汇入','Remitted in prior years'],
        ['current_remitted_income','本年汇入','Remitted this year'],
        ['included_assessable_income','本批次纳入计税收入','Included assessable income from this pool'],
        ['remaining_income','尚未汇入余额','Income not yet remitted'],
        ['attributable_paid_tax','按纳入收入分摊的已缴税','Paid tax attributed to included income'],
        ['eligible_attributable_tax','本批次合资格分摊税额','Eligible attributed tax from this pool']])}
      <p>{say('核验依据：','Verified basis: ')}{String(row.entitlement_and_fx_explanation)}</p>
    </section>)}
  </section>;
}
