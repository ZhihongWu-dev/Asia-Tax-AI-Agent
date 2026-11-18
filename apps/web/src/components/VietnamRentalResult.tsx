export default function VietnamRentalResult({result,index}:{result:Record<string,unknown>;index:number}) {
  const say=(zh:string,en:string)=>index?en:zh;
  const rows=Array.isArray(result.contracts)?result.contracts as Record<string,unknown>[]:[];
  const labels:[string,string][]=[
    ['revenue',say('已保存年度租金','Saved annual rental revenue')],
    ['allocated_revenue_deduction',say('分配的年度扣除','Allocated annual deduction')],
    ['taxable_revenue',say('计税租金','Taxable rental revenue')],
    ['tax_before_relief',say('减税前税额','Tax before relief')],
    ['annual_reduction',say('年度减税','Annual reduction')],
    ['final_tax',say('合同本期税额','Contract tax for this period')],
    ['prepaid_tax',say('实际已缴税额','Actual tax paid')],
    ['balance_due',say('合同余额（负数表示多缴）','Contract balance (negative means overpaid)')],
  ];
  return <section aria-label={say('房产出租计算明细','Property-rental calculation details')}>
    <p>{say('逐合同列示；汇总余额不代表可跨合同直接抵扣或已获退税。不含增值税。','Shown per contract; aggregate balances do not authorize cross-contract offsets or refunds. VAT excluded.')}</p>
    {rows.map((row,n)=><section key={n} aria-label={say(`租赁合同 ${n+1}`,`Rental contract ${n+1}`)}>
      <h5>{String(row.contract_id)}</h5>
      <p>{row.tenant_files===true?say('由承租人申报代缴','Tenant files and pays on behalf'):say('出租人负责申报','Landlord responsible for filing')}</p>
      <dl>{labels.map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String(row[key])}</dd></div>)}</dl>
    </section>)}
  </section>;
}
