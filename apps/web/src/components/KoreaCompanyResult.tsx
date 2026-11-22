type Cash = {payable:string;refundable:string};
type Filing = {allocated_gross_tax:string;withholding_credit:string;settlement:Cash};
export default function KoreaCompanyResult({result,index}:{result:Record<string,unknown>;index:number}) {
  const national=result.national as {gross_tax:string;tax_after_reliefs:string;payment_credits:string;settlement:Cash};
  const local=result.local as {filings:Record<string,Filing>};
  const foreign=result.foreign_credit as {country_credits:Array<Record<string,string>>}|undefined;
  const localBasis=result.local_basis as Record<string,string>|undefined;
  const history=result.historical_foreign_credit as {historical_credit_used:string;historical_lots:Array<Record<string,string|boolean>>}|undefined;
  const say=(zh:string,en:string)=>index?en:zh;
  const cash=(value:Cash)=><><div><dt>{say('应缴金额','Payable')}</dt><dd>{value.payable}</dd></div><div><dt>{say('预计应退金额','Calculated refundable')}</dt><dd>{value.refundable}</dd></div></>;
  return <section aria-label={say('韩国分机关结算','Korean settlement by authority')}>
    <p>{say('国税和各地方申报单位分别结算；应退金额不自动抵扣其他机关应缴款。此结果不含特殊税负、更正申报或分期缴纳。','National and local authorities settle separately; refunds do not automatically offset another authority’s payment. Excludes special taxes, amended returns and installments.')}</p>
    <dl><div><dt>{say('应缴合计（不减退款）','Total payable (before refunds)')}</dt><dd>{String(result.total_payable)}</dd></div>
      <div><dt>{say('预计应退合计','Total calculated refundable')}</dt><dd>{String(result.total_refundable)}</dd></div></dl>
    {foreign&&<section aria-label={say('韩国分国境外抵免','Korean foreign credits by country')}>
      <h5>{say('分国境外抵免','Foreign credits by country')}</h5>
      {foreign.country_credits.map(row=><section key={row.country}><h6>{row.country.toUpperCase()}</h6><dl>
        {([['income_for_credit_limit','限额所得','Income for credit limit'],['credit_limit','抵免限额','Credit limit'],
          ['current_foreign_tax_credit','本期抵免','Current credit'],['expense_related_excess_not_carried','费用对应超限额（不作普通结转）','Expense-related excess (not ordinary carry)'],
          ['eligible_current_year_carryforward','普通抵免结转','Ordinary credit carryforward']] as const).map(([key,zh,en])=><div key={key}><dt>{say(zh,en)}</dt><dd>{row[key]}</dd></div>)}
      </dl></section>)}
      {localBasis&&<dl>{([['current_local_foreign_tax_deduction','地方税税基境外税扣除','Foreign-tax deduction from local base'],
        ['local_taxable_base','地方税税基（取整前）','Local taxable base before rounding'],
        ['excess_current_local_deduction','地方税扣除结转余额','Local deduction carryforward']] as const).map(([key,zh,en])=><div key={key}><dt>{say(zh,en)}</dt><dd>{localBasis[key]}</dd></div>)}</dl>}
    </section>}
    {history&&<section aria-label={say('韩国历史国税抵免','Korean historical national credits')}>
      <h5>{say('历史国税抵免','Historical national credits')}</h5>
      <p>{say('本期使用合计：','Total used this period: ')}{history.historical_credit_used}</p>
      <p>{say('余额已按来源国及核实顺序分配；年末到期未用余额不保证以后可用，不再次扣减地方税税基。','Balances are allocated by source country in verified order. Unused amounts expiring at year-end may not be usable later and do not reduce the local base again.')}</p>
      {history.historical_lots.map(row=><section key={String(row.identifier)}><h6>{String(row.identifier)}</h6><dl>
        {([['country','国家','Country'],['expiry_date','核实到期日','Verified expiry'],['used','本期使用','Used this period'],['remaining','本期使用后未用余额','Unused after current allocation']] as const).map(([key,zh,en])=><div key={key}><dt>{say(zh,en)}</dt><dd>{String(row[key])}</dd></div>)}
      </dl></section>)}
    </section>}
    <section aria-label={say('韩国国税','Korean national tax')}><h5>{say('国税','National tax')}</h5><dl>
      <div><dt>{say('减免前税额','Gross tax')}</dt><dd>{national.gross_tax}</dd></div>
      <div><dt>{say('减免后税额','Tax after reliefs')}</dt><dd>{national.tax_after_reliefs}</dd></div>
      <div><dt>{say('已缴款抵扣','Payment credits')}</dt><dd>{national.payment_credits}</dd></div>{cash(national.settlement)}</dl></section>
    {Object.entries(local.filings).map(([name,row])=><section key={name} aria-label={`${say('地方申报单位','Local authority')}: ${name}`}>
      <h5>{name}</h5><dl><div><dt>{say('分摊税额','Allocated gross tax')}</dt><dd>{row.allocated_gross_tax}</dd></div>
        <div><dt>{say('扣缴税款抵扣','Withholding credit')}</dt><dd>{row.withholding_credit}</dd></div>{cash(row.settlement)}</dl>
    </section>)}
  </section>;
}
