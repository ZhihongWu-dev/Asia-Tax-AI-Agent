type Cash={payable:string;refundable:string};
export default function KoreaSalaryResult({result,index}:{result:Record<string,unknown>;index:number}) {
  const say=(zh:string,en:string)=>index?en:zh;
  const annual=result.annual as {national_taxable_base:string;gross_tax:string;decision_tax:string;
    child_credit:{regular_child_credit:string;birth_adoption_credit:string;children:{identifier:string;birth_2017_transition_excluded:boolean}[]}};
  const national=result.national_settlement as {settlement:Cash;small_balance_not_collected:string};
  const local=result.local_settlement as {settlement:Cash;local_decision_tax:string};
  return <section aria-label={say('韩国工资结算','Korean salary settlement')}>
    <p>{say('普通居民工资、标准抵免的雇主年终结算。国税和地方税分别补退，不自动互抵；这不是其他个人所得的综合申报。','Employer year-end settlement for ordinary resident salary with standard credit. National and local payments/refunds remain separate; this is not a comprehensive return for other personal income.')}</p>
    <dl>{([
      [say('国税税基','National taxable base'),annual.national_taxable_base],
      [say('国税决定税额','National decision tax'),annual.decision_tax],
      [say('地方税决定税额','Local decision tax'),local.local_decision_tax],
      [say('普通子女抵免参考额','Regular child credit reference'),annual.child_credit.regular_child_credit],
      [say('出生／收养抵免参考额','Birth/adoption credit reference'),annual.child_credit.birth_adoption_credit],
      [say('应缴合计（不减退款）','Total payable (before refunds)'),String(result.total_payable)],
      [say('预计应退合计','Total calculated refundable'),String(result.total_refundable)],
    ]).map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    {annual.child_credit.children.some(child=>child.birth_2017_transition_excluded)&&<p>{say('已应用2017年出生子女不享受年龄过渡优惠的例外；基本扣除资格另行判断。','Applied the 2017 birth-cohort exception to transitional child credit; basic deduction eligibility is assessed separately.')}</p>}
    {([['国税','National tax',national.settlement],['地方税','Local tax',local.settlement]] as const).map(([zh,en,cash])=><section key={en} aria-label={say(zh,en)}><h5>{say(zh,en)}</h5><dl>
      <div><dt>{say('应缴金额','Payable')}</dt><dd>{cash.payable}</dd></div>
      <div><dt>{say('预计应退金额','Calculated refundable')}</dt><dd>{cash.refundable}</dd></div>
    </dl></section>)}
    <p>{say('国税小额免征：','National small-balance noncollection: ')}{national.small_balance_not_collected}</p>
  </section>;
}
