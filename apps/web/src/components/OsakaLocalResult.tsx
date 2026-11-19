export default function OsakaLocalResult({result,index}:{result:Record<string,unknown>;index:number}) {
 const say=(zh:string,en:string)=>index?en:zh;
 const local=result.osaka_local as Record<string,unknown>;
 const taxes=local.local_tax_components as Record<string,unknown>,interim=local.local_interim_liabilities as Record<string,unknown>,balances=local.local_balances as Record<string,unknown>;
 const reconciliation=local.local_income_reconciliation as Record<string,unknown>;
 const wards=(local.capitation as Record<string,unknown>).wards as Record<string,unknown>[];
 const names=[['enterprise','事业税','Enterprise tax'],['special_enterprise','特别法人事业税','Special enterprise tax'],['prefectural_inhabitant','府法人税割','Prefectural inhabitant levy'],['city_inhabitant','市法人税割','City inhabitant levy'],['prefectural_capitation','府均等割','Prefectural per-capita levy'],['city_capitation','市均等割','City per-capita levy']] as const;
 return <section aria-label={say('大阪地方税明细','Osaka local tax details')}><h4>{say('大阪地方税明细','Osaka local tax details')}</h4>
 <p>{say('仅限全部办公地点全年位于大阪市的普通内国法人，各税种补退分别处理，不自动互抵；不含其他地区、外形标准课税或特殊税制。','Full-year ordinary domestic company with all offices in Osaka city. Component balances remain separate without automatic offsets. Other locations, size-based and special regimes are excluded.')}</p>
 <p>{say('上方应缴及应退合计仅为国家税，地方税补退另列如下。','Payable and refundable totals above cover national taxes only; local payments and refunds are listed separately below.')}</p>
 <p>{say('防卫特别法人税申报：','Defence tax return: ')}{result.defence_return_required?say('需要，包括零税额申报。','Required, including zero-tax returns.'):say('本会计年度开始日尚不适用。','Not applicable for this accounting-period start date.')}</p>
 <dl><div><dt>{say('国家税合计','National tax total')}</dt><dd>{String(result.national_final_tax)}</dd></div><div><dt>{say('本场景国家税与地方税合计','National and local tax total for this scope')}</dt><dd>{String(result.final_tax)}</dd></div></dl>
 {names.map(([key,zh,en])=><section key={key} aria-label={say(zh,en)}><h5>{say(zh,en)}</h5><dl>
 <div><dt>{say('年度税额','Annual tax')}</dt><dd>{String(taxes[key])}</dd></div><div><dt>{say('中间申告义务','Interim liability')}</dt><dd>{String(interim[key])}</dd></div><div><dt>{say('应补／退额','Payment or refund balance')}</dt><dd>{String(balances[key])}</dd></div></dl></section>)}
 <dl>{([['local_amounts_payable','地方税应补合计','Local amounts payable'],['local_refunds','地方税退款合计','Local refund amounts']] as const).map(([key,zh,en])=><div key={key}><dt>{say(zh,en)}</dt><dd>{String(local[key])}</dd></div>)}</dl>
 <h5>{say('地方税税基核对','Local basis reconciliation')}</h5><dl>{([
 ['national_income_before_losses','国税抵亏前所得','National income before losses'],['enterprise_additions','事业税调增','Enterprise additions'],['enterprise_deductions','事业税调减','Enterprise deductions'],
 ['enterprise_income_before_losses','事业税抵亏前所得','Enterprise income before losses'],['enterprise_prior_losses_used','使用事业税旧亏损','Enterprise prior losses used'],['enterprise_prior_losses_unused','未用事业税旧亏损','Enterprise prior losses unused'],
 ['enterprise_taxable_income','事业税应税所得','Enterprise taxable income'],['capital_for_per_capita_band','均等割适用资本额','Capital for per-capita band'],
 ] as const).map(([key,zh,en])=><div key={key}><dt>{say(zh,en)}</dt><dd>{String(reconciliation[key])}</dd></div>)}</dl>
 <h5>{say('逐区均等割','Per-capita levy by ward')}</h5>{wards.map(ward=><p key={String(ward.ward_name)}>{String(ward.ward_name)}: {say('员工','Employees')} {String(ward.employees)}; {say('税额','Tax')} {String(ward.annual_city_capitation)}</p>)}
 </section>;
}
