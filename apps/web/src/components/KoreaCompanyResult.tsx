type Cash = {payable:string;refundable:string};
type Filing = {allocated_gross_tax:string;withholding_credit:string;settlement:Cash};
export default function KoreaCompanyResult({result,index}:{result:Record<string,unknown>;index:number}) {
  const national=result.national as {gross_tax:string;tax_after_reliefs:string;payment_credits:string;settlement:Cash};
  const local=result.local as {filings:Record<string,Filing>};
  const say=(zh:string,en:string)=>index?en:zh;
  const cash=(value:Cash)=><><div><dt>{say('应缴金额','Payable')}</dt><dd>{value.payable}</dd></div><div><dt>{say('预计应退金额','Calculated refundable')}</dt><dd>{value.refundable}</dd></div></>;
  return <section aria-label={say('韩国分机关结算','Korean settlement by authority')}>
    <p>{say('国税和各地方申报单位分别结算；应退金额不自动抵扣其他机关应缴款。此结果不含特殊税负、更正申报或分期缴纳。','National and local authorities settle separately; refunds do not automatically offset another authority’s payment. Excludes special taxes, amended returns and installments.')}</p>
    <dl><div><dt>{say('应缴合计（不减退款）','Total payable (before refunds)')}</dt><dd>{String(result.total_payable)}</dd></div>
      <div><dt>{say('预计应退合计','Total calculated refundable')}</dt><dd>{String(result.total_refundable)}</dd></div></dl>
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
