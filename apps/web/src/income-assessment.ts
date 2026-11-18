import type { IncomeTaxInput } from './income-tax';
import { koreaPolicy } from './korea-assessment';
import { koreaSalaryPolicy } from './korea-salary-assessment';
import { thaiDividendPolicy } from './thailand-dividend-assessment';
import { thaiForeignPolicy } from './thailand-foreign-assessment';
import { vietnamBusinessPolicy } from './vietnam-business-assessment';
import { vietnamRentalPolicy } from './vietnam-rental-assessment';

export type IncomeRun = {
  id: string; input_revision: number; created_at: string; status: string; snapshot_hash: string;
  result: Record<string, unknown>;
};
type Label = [string, string];
export type BasisField = { key: string; label: Label; options?: [string, Label][]; boolean?: boolean; monthsList?: boolean; text?: boolean; min?: number; max?: number; date?: boolean; dateMin?: string; integer?: boolean; showWhen?: [string,string] };
const money = (key: string, zh: string, en: string): BasisField => ({key, label:[zh,en]});
const confirm = (key: string, zh: string, en: string): BasisField => ({key,label:[zh,en],boolean:true});
const prepaid = money('prepaid_tax','归属本期的预缴税额','Prepaid tax for this period');
const hkPrepaid = money('prepaid_final_tax','归属本期最终评税的已缴税额','Prepaid final tax for this assessment');
const cnCompanyExclusions = [money('non_taxable_income','收入总额中核定的不征税收入','Established non-taxable income included in total income'),
  money('exempt_income','收入总额中核定的免税收入','Established exempt income included in total income')];
const ordinary = confirm('ordinary_regime_confirmed','已核对适用普通税制及其排除条件','Ordinary regime and exclusions checked');
export type IncomePolicy = { id: string; label: Label; notice: Label; fields: BasisField[] };

export function policies(input: IncomeTaxInput, values:Record<string,string>={}): IncomePolicy[] {
  const company = input.subject === 'company';
  const period = input.period_start + '/' + input.period_end;
  if(input.jurisdiction==='vn' && !company && input.residency==='resident' && period==='2026-01-01/2026-12-31' && input.incomes.length && input.incomes.every(i=>i.category==='rental'&&i.source_jurisdiction==='vn'))return [vietnamRentalPolicy(input)];
  if(input.jurisdiction==='vn' && !company && input.residency==='resident' && period==='2026-01-01/2026-12-31' && input.incomes.length && input.incomes.every(i=>i.category==='business'&&i.source_jurisdiction==='vn'))return [vietnamBusinessPolicy(input)];
  if(input.jurisdiction==='th' && !company && input.residency==='resident' && period==='2026-01-01/2026-12-31' && input.incomes.some(i=>i.source_jurisdiction!=='th') && input.incomes.every(i=>(i.source_jurisdiction==='th'?['employment','business','service_remuneration','author_remuneration','royalty','rental']:['employment','business','service_remuneration','author_remuneration','royalty','rental','dividend','interest']).includes(i.category)))return [thaiForeignPolicy(input,values)];
  if(input.jurisdiction==='th' && !company && input.residency==='resident' && period==='2026-01-01/2026-12-31' && input.incomes.some(i=>i.category==='dividend') && input.incomes.every(i=>i.source_jurisdiction==='th'&&['dividend','employment','business','service_remuneration','author_remuneration','royalty','rental'].includes(i.category)))return [thaiDividendPolicy(input,values)];
  if(input.jurisdiction==='kr' && !company && input.residency==='resident' && period==='2026-01-01/2026-12-31' && input.incomes.every(i=>i.source_jurisdiction==='kr'&&i.category==='employment'))return [koreaSalaryPolicy(values)];
  if(input.jurisdiction==='kr' && company && input.residency==='resident' && period==='2026-01-01/2026-12-31' && input.incomes.every(i=>i.source_jurisdiction==='kr'&&['business','interest','rental','royalty'].includes(i.category))) return [koreaPolicy(values)];
  if(input.jurisdiction==='in' && input.residency==='resident' && period==='2026-04-01/2027-03-31' && input.incomes.every(i=>i.source_jurisdiction==='in'&&['business','employment','service_remuneration','author_remuneration','interest','rental','royalty'].includes(i.category))) {
    const primary: IncomePolicy = {id:company?'in_company_section200_ty2026_27':'in_personal_new_ty2026_27',
      label:company?['印度境内企业第200条税制（TY 2026–27）','India domestic company section 200 (TY 2026–27)']:['印度居民个人新税制（TY 2026–27）','India resident individual new regime (TY 2026–27)'],
      notice:['适用于2026年4月1日至2027年3月31日的Tax Year，不是AY 2026–27。计算年度税额、附加税及健康教育费，不是扣除已缴款后的补退金额，不含利息或罚款。个人须适用第202条新税制；企业须已按时有效选择第200条并核实扣除、亏损及折旧限制。输入税基须与保存的收入减去核定扣除及可抵扣亏损一致；工资标准扣除等须已核定计入保存扣除，不自动另算。不含特殊税率所得、股息、资本利得、农业所得合并、境外所得或抵免、IFSC优惠及其他税额调整。',
        'Uses Tax Year 1 April 2026–31 March 2027, not AY 2026–27. Calculates annual liability including surcharge and health/education cess, before payment credits, interest and penalties. Individuals must use section 202; domestic companies require a valid timely section 200 option and verified deduction, loss and depreciation restrictions. The established base must equal saved income less verified deductions and eligible losses. Include verified salary standard deductions in saved deductions; they are not calculated again. Excludes special-rate income, dividends, capital gains, agricultural aggregation, foreign income or relief, IFSC concessions and other tax adjustments.'],
      fields:[money('taxable_income_before_rounding','核定取整前应税所得','Established taxable income before rounding'),
        confirm('regime_and_base_verified','已核实税制选择、资格、扣除及亏损限制','Regime election, eligibility, deductions and loss restrictions verified'),
        confirm('ordinary_domestic_scope_confirmed','已核实境内普通所得及全部排除条件','Ordinary domestic income and all exclusions verified'),
        confirm('settlement_requested','另算本次普通申报补退税额','Also calculate the ordinary return balance'),
        {...money('tds_tcs_credit','核定本期可用扣缴／代收税额','Verified current-period TDS/TCS credit'),showWhen:['settlement_requested','true']},
        {...money('advance_tax_paid','本期实际已缴预缴税额','Advance tax actually paid for this period'),showWhen:['settlement_requested','true']},
        {...money('self_assessment_paid','本期实际已缴自评税款总额（含已缴利息和费用）','Total self-assessment payments including paid interest and fees'),showWhen:['settlement_requested','true']},
        {...money('total_interest_due','核定累计应计利息（含已缴部分，无则填0）','Verified cumulative interest including amounts already paid (0 if none)'),showWhen:['settlement_requested','true']},
        {...money('total_fee_due','核定累计应计费用（含已缴部分，无则填0）','Verified cumulative fees including amounts already paid (0 if none)'),showWhen:['settlement_requested','true']},
        {...confirm('settlement_verified','已核对税款归属及凭证、累计利息费用和缴款抵扣顺序；无先前退税、更新申报、ESOP递延、罚款或额外追缴','Credits, evidence, cumulative interest/fees and payment allocation verified; no prior refunds, updated return, ESOP deferral, penalties or additional demands'),showWhen:['settlement_requested','true']}]};
    if(company)return [primary,{...primary,id:'in_company_normal_ty2026_27',
      label:['印度境内企业普通税制与MAT（TY 2026–27）','India domestic company normal tax and MAT (TY 2026–27)'],
      notice:['适用于2026年4月至2027年3月、未选择第200／201条的境内普通企业。25%／30%税率依据2024–25年法定营业额／总收入是否超过40亿卢比判断，不使用当前收入。普通应税所得与第206条调整后账面利润须分别核定，不能直接以会计净利润代替MAT税基；无正账面利润填0。分别计算普通税与14% MAT的附加税、边界减免及健康教育费后取高。该普通税制不抵扣历史MAT抵免，2026年起缴纳MAT不新增抵免。不含IFSC、寿险、航运、特殊税率、境外所得或其他税额调整。历史期间不存在或资料未知时不能随意填0取得25%税率，须先核实分类。',
        'Ordinary domestic companies outside sections 200/201 for April 2026–March 2027. The 25%/30% rate depends on statutory turnover/gross receipts in 2024–25 against INR4 billion, not current income. Establish ordinary taxable income and section 206 adjusted book profit separately; accounting net profit is not the MAT base. Enter 0 if there is no positive adjusted book profit. Compare normal tax and 14% MAT after their respective surcharge, marginal relief and cess. This ordinary regime does not use legacy MAT credit; MAT paid from April 2026 creates no new credit. Excludes IFSC, life insurance, shipping, special-rate/foreign income and other tax adjustments. An absent or unknown historical period must not be entered as zero to obtain 25%; verify classification first.'],
      fields:[...primary.fields,
        money('turnover_2024_25','核定2024–25年法定营业额／总收入','Verified statutory turnover/gross receipts for 2024–25'),
        money('mat_book_profit_before_rounding','核定取整前MAT正账面利润（无则填0）','Verified positive MAT book profit before rounding (0 if none)'),
        confirm('turnover_and_mat_adjustments_verified','已核实历史收入分类、MAT调整和普通税制适用条件','Historical turnover classification, MAT adjustments and ordinary regime verified')]}];
    return [primary,{...primary,id:'in_personal_old_ty2026_27',
      label:['印度居民个人旧税制（TY 2026–27）','India resident individual old regime (TY 2026–27)'],
      notice:['适用于2026年4月至2027年3月的居民个人普通所得。须核实第202(4)条旧税制选择有效，经营所得须核对选择期限、历史选择和撤回限制。年龄按本税年内达到的最高年龄档；不能把60岁与80岁档重叠使用。税基扣除须按旧税制重新核定并与保存资料一致，不能沿用新税制扣除。此入口要求已核实不适用第206(2)条AMT，且无AMT结转抵免。计算含附加税和健康教育费，结算须另选。不含特殊税率所得、农业合并、境外所得或抵免、IFSC、其他税额抵免及调整。',
        'Resident ordinary income for April 2026–March 2027. Verify a valid section 202(4) old-regime election, including business-income deadlines and prior election/withdrawal restrictions. Use the highest age band attained during the tax year. Re-establish old-regime deductions and reconcile saved facts; do not reuse new-regime deductions unchanged. Requires verified non-applicability of section 206(2) AMT and no carried AMT credit. Includes surcharge and cess; settlement is optional. Excludes special-rate income, agricultural aggregation, foreign income or relief, IFSC, other tax credits and adjustments.'],
      fields:[...primary.fields,
        {key:'resident_age_band',label:['本税年内达到的最高年龄档','Highest age band attained during this tax year'],options:[['under60',['未满60岁','Under 60']],['60_to79',['60至79岁','60 to 79']],['80_plus',['80岁及以上','80 or above']]]},
        confirm('amt_not_applicable_verified','已核实不适用AMT，且无AMT结转抵免','AMT non-applicability and absence of carried AMT credit verified')]}];
  }
  if (input.jurisdiction==='jp' && company && input.residency==='resident' && /^2026-\d{2}-\d{2}$/.test(input.period_start)) {
    const [,month,day]=input.period_start.split('-').map(Number);
    const annualEnd=new Date(Date.UTC(2027,month-1,day)-86400000).toISOString().slice(0,10);
    if(input.period_end===annualEnd)return [{id:'jp_company_starting_2026',label:['日本普通企业国家税（2026年开始的完整年度）','Japan ordinary company national taxes (full year starting 2026)'],
      notice:['分别计算法人税、地方法人税（国税）及适用时的防卫特别法人税，不含地方住民税、事业税或最低补足税。税基须已完成纳税调整及亏损处理。仅限无税额抵免、扣缴抵免、税额加算或留保金附加税的境内普通企业，不含通算集团及特殊主体。小企业须核对期末资本和大法人控制等排除条件；适用除外事业者须核对前三年法定年均所得超过15亿日元等调整。符合特例时，年所得超过10亿日元时首800万部分适用17%；超过门槛但千日元取整后未超过的情形须人工复核。防卫税按开始日判断，4月1日起即使税额为0也须申报。中间申告金额填应纳义务，不论实缴；各税种补退分别处理，不自动互抵。',
        'Separately calculates corporation tax, local corporation tax (a national tax) and applicable defence tax; excludes prefectural/municipal inhabitant, enterprise and minimum top-up taxes. Establish taxable income after adjustments and losses. Ordinary domestic companies without tax credits, withholding credits, tax additions or retained-profit surtax only; no tax groups or special entities. Verify SME year-end capital and large-company control exclusions. Excluded-business classification uses the statutory prior-three-year average above JPY 1.5bn and its adjustments. Eligible reduced-rate companies with current income above JPY 1bn use 17% on the first JPY 8m; cases above the threshold only before JPY 1,000 truncation require manual review. Defence tax applies by start date from 1 April, including zero-tax returns. Interim amounts are liabilities regardless of payment; settle each tax separately without automatic offsets.'],
      fields:[money('taxable_income_before_rounding','已核定千日元取整前应税所得','Established taxable income before JPY 1,000 truncation'),
        {key:'rate_regime',label:['已核实的法人税率分类','Verified corporation-rate classification'],options:[
          ['ordinary',['普通23.2%','Ordinary 23.2%']],['sme_reduced',['小企业15%／17%特例','SME 15% / 17% special rate']],['sme_excluded',['小企业适用除外事业者19%','SME excluded business: 19%']]]},
        money('corporation_interim_liability','法人税中间申告应纳义务','Corporation interim-return liability'),
        money('local_corporation_interim_liability','地方法人税中间申告应纳义务','Local corporation interim-return liability'),
        confirm('rate_classification_verified','已核实资本、控制关系及适用除外事业者分类','Capital, control exclusions and excluded-business classification verified'),
        confirm('ordinary_no_adjustments_confirmed','已核实普通境内企业税基，无抵免、加算、留保金附加税或集团税制','Ordinary domestic tax base verified; no credits, additions, retained-profit surtax or group regime')]}];
  }
  if (input.jurisdiction === 'jp' && !company && input.residency === 'resident' && period === '2026-01-01/2026-12-31' && input.incomes.every(i=>i.source_jurisdiction==='jp'&&['employment','business'].includes(i.category))) {
    return [{id:'jp_resident_ordinary_2026',label:['日本居民普通所得国家税（2026）','Japan resident ordinary national tax (2026)'],
      notice:['计算2026全年境内工资及无亏损普通经营所得的国家所得税和复兴特别所得税，不含住民税、事业税。使用12月1日起适用的年度扣除，不用于此前预扣、死亡或出境提前申报，也不是雇主年末调整。已保存扣除额应为经营费用与其他所得扣除之和；工资扣除、符合条件的工资所得调整扣除和基本扣除由系统另算。不得重复计入，不含特定支出、青色申告优惠、年金、境外所得、分离课税、结转亏损或超过3.3亿日元的高所得最低税。抵免须先核定限额，不含境外抵免。予定纳税额填有效通知核定金额（扣除已批准减额），并非实际缴款；未缴欠税仍需另行处理。',
        'Calculates 2026 domestic salary and non-loss-making ordinary business national income and reconstruction tax, excluding local inhabitant and enterprise taxes. Uses annual deductions effective 1 December; not earlier withholding, early death/departure returns or employer year-end adjustment. Saved deductions must equal business expenses plus other income deductions. Salary deductions, eligible salary adjustment and basic deduction are calculated separately; do not count them twice. Excludes specific employment expenses, blue-return relief, pensions, foreign or separate-rate income, carried losses and the high-income minimum tax above JPY 330m. Verify credit limits; foreign credits are excluded. Estimated tax is the effective notified liability after approved reductions, not actual payments; unpaid arrears remain separate.'],
      fields:[money('business_expenses','核定经营费用（无则填0）','Verified business expenses (0 if none)'),
        money('other_income_deductions','其他所得扣除（不含自动计算项目）','Other income deductions (excluding automatic deductions)'),
        money('income_tax_credits','核定国家所得税抵免（限额内）','Verified national income-tax credits within limits'),
        confirm('salary_adjustment_eligible','符合23岁以下受抚养人或特别障碍者等工资所得调整资格','Eligible for salary adjustment for under-23 dependents or special disability'),
        money('withheld_tax','本年度源泉扣缴税额','Tax withheld for this year'),
        money('estimated_tax','有效通知核定予定纳税额（不是实际缴款）','Effective notified estimated-tax liability (not cash paid)'),
        confirm('annual_domestic_ordinary_scope_confirmed','已核实全年居民境内普通所得及排除条件，工资按源泉徴収票应税支払金额填报','Full-year resident domestic ordinary scope verified; salary uses taxable withholding-statement receipts'),
        confirm('deductions_and_credits_verified','已核实扣除、调整资格、抵免限额及予定纳税通知','Deductions, adjustment eligibility, credit limits and estimated-tax notice verified')]}];
  }
  if (input.jurisdiction === 'vn' && !company && input.residency !== 'undetermined' && period === '2026-01-01/2026-12-31' && input.incomes.length && input.incomes.every(i=>i.category==='capital_gain')) {
    const fields: BasisField[] = input.incomes.flatMap((_item,n)=>{
      const prefix=`transfer_${n}_`, label=(zh:string,en:string):Label=>[`${n+1}. ${zh}`,`${n+1}. ${en}`];
      return [
        {key:prefix+'recognition_date',label:label('法定收入确认日期','Statutory recognition date'),date:true},
        {key:prefix+'method',label:label('核定资产与成本分类','Verified asset and cost classification'),options:[
          ['capital_known',['资本权益：成本已核实','Capital interest: costs established']],
          ['capital_unknown',['资本权益：无法确定成本','Capital interest: costs cannot be established']],
          ['security',['证券（含未上市股份公司股票）','Securities (including unlisted joint-stock shares)']]]},
        {...money(prefix+'purchase_cost',...label('取得成本','Acquisition cost')),showWhen:[prefix+'method','capital_known']},
        {...money(prefix+'transfer_costs',...label('合理转让费用','Reasonable transfer costs')),showWhen:[prefix+'method','capital_known']},
        money(prefix+'prepaid_tax',...label('此笔交易已缴税额','Tax prepaid for this transaction')),
        confirm(prefix+'ordinary_sale_confirmed',...label('确认普通应税出售，不含出资递延或房地产关联整体出售','Ordinary taxable sale; no deferred contribution or property-linked whole-business sale')),
        confirm(prefix+'classification_valuation_and_scope_verified',...label('已核对分类、法定价格、地域范围及无免税或协定优惠','Classification, statutory price, territorial scope and absence of exemption/treaty relief verified')),
      ] as BasisField[];
    });
    return [{id:'vn_personal_transfer_2026',label:['越南个人转让所得（2026年7月至12月）','Vietnam personal transfers (July–December 2026)'],
      notice:['逐笔使用已保存的转让价款，不是净收益。取得成本和转让费用合计必须等于已保存扣除额；各笔亏损不能互抵。先剔除分期利息，核对法定估价与确认日期。出资、撤资、解散、衍生品、房地产关联整体出售及优惠另行处理。',
      'Each saved amount must be statutory transfer proceeds, not net gain. Total acquisition and transfer costs must match saved deductions; losses cannot offset other transactions. Exclude installment interest and verify statutory valuation and recognition dates. Contributions, withdrawals, dissolution, derivatives, property-linked whole-business sales and relief need separate treatment.'],fields}];
  }
  if (input.jurisdiction === 'vn' && company && input.residency === 'resident' && period === '2026-01-01/2026-12-31') {
    return [{id:'vn_company_2026',label:['越南普通企业所得税（2026）','Vietnam ordinary company tax (2026)'],
      notice:['仅限越南设立企业的境内普通所得。须先核定税基、亏损及纳税调整，排除第23(9)条所得、特殊行业及优惠税率。已保存明细须覆盖未扣收入减项的销售服务、财务和其他法定收入。本期收入决定年度减税；上期收入及经营月份决定普通税率和小额收入免税，新设企业使用本期实际收入。两项关联企业排除条件须分别核对。其他优惠先扣，年度减税后扣，预缴税款最后抵减；结果尚未进行申报取整。',
        'Vietnam-established enterprises with ordinary domestic income only. Establish the tax base after losses and adjustments, excluding article 23(9) income, special industries and preferential rates. Saved receipts must include sales/services before revenue deductions, financial and other statutory revenue. Current revenue determines annual relief; prior revenue and active months determine ordinary rates and small-revenue exemption, except new enterprises use current actual revenue. Check the two related-enterprise exclusions separately. Other incentives precede annual relief; prepayments follow. Before return rounding.'],
      fields:[money('taxable_income','核定应税所得额','Established taxable income'),
        confirm('vietnam_established','企业在越南设立','Enterprise established in Vietnam'),
        confirm('new_in_current_period','企业在本期新设立','Enterprise newly established in this period'),
        {...money('previous_period_revenue','上期完整法定收入','Complete prior-period statutory revenue'),showWhen:['new_in_current_period','false']},
        {key:'previous_active_months',label:['上期法定经营月份','Prior-period statutory active months'],integer:true,showWhen:['new_in_current_period','false'],options:Array.from({length:12},(_,i)=>[String(i+1),[String(i+1),String(i+1)]])},
        confirm('exemption_related_enterprise_disqualified','存在不符合小额收入免税条件的关联企业','Related enterprise disqualifies small-revenue exemption'),
        confirm('reduced_rate_related_enterprise_disqualified','存在不符合15%或17%税率条件的关联企业','Related enterprise disqualifies reduced rates'),
        confirm('formed_by_split_after_resolution','属于决议后分拆设立的企业','Enterprise formed by a split after the resolution'),
        {...money('all_split_entities_revenue','全部分拆企业合计法定收入（含本企业）','Combined statutory revenue of all split entities (including this enterprise)'),showWhen:['formed_by_split_after_resolution','true']},
        money('other_incentive_reduction','核定其他税额优惠（年度减税前）','Verified other incentives before annual relief'),prepaid,
        confirm('ordinary_domestic_income_confirmed','已核实境内普通所得及全部排除条件','Ordinary domestic income and all exclusions verified'),
        confirm('statutory_revenue_scope_confirmed','已核实全部法定收入范围及期间','Complete statutory revenue scope and periods verified'),
        confirm('other_incentives_verified','已核实其他优惠金额及适用资格','Other incentive amount and eligibility verified')]}];
  }
  if (input.jurisdiction === 'vn' && !company && input.residency === 'resident' && period === '2026-01-01/2026-12-31') {
    return [{id:'vn_employment_2026',label:['越南居民工资薪金（2026）','Vietnam resident employment (2026)'],
      notice:['仅限全年居民境内工资薪金。输入已剔除免税收入、尚未扣除个人扣除的应税工资；保险及第11条扣除须已核实限额和凭证。系统扣除本人全年1.86亿越南盾及每名受抚养人每月620万；同一受抚养月份不得重复申报。不适用经营所得减税，不含境外抵免、非居民或特殊减免。结果尚未进行申报取整。',
        'Full-calendar-year resident domestic employment only. Enter chargeable pay after exemptions, before personal deductions. Verify insurance and article 11 deduction limits and evidence. The calculation deducts VND 186m for the taxpayer and VND 6.2m per eligible dependent-month; do not duplicate claims. Business-income relief does not apply. Foreign credits, nonresidents and special relief need separate treatment. Result is before return rounding.'],
      fields:[money('chargeable_employment_income','个人扣除前应税工资','Chargeable pay before personal deductions'),
        {key:'dependent_months',label:['每名受抚养人的合资格月份（逗号分隔，无则填0）','Eligible months per dependent (comma-separated; enter 0 for none)'],monthsList:true},
        money('deductible_insurance','核定可扣除保险','Verified deductible insurance'),money('article11_deductions','核定第11条扣除','Verified article 11 deductions'),prepaid,
        confirm('full_calendar_year_confirmed','已核实全年居民年度评税资格','Full calendar-year resident assessment verified'),
        confirm('income_and_deductions_verified','已核实工资分类、扣除资格及受抚养月份无重复申报','Pay classification, deductions and nonduplicated dependent-month claims verified')]}];
  }
  if (input.jurisdiction === 'id' && period === '2026-01-01/2026-12-31') {
    const common = [confirm('ordinary_annual_treatment_confirmed','已核对全年居民普通税制及最终税制等排除条件','Full-year resident ordinary treatment and final/special-regime exclusions checked'),
      money('prepaid_tax','核定本期扣缴及预缴税款','Verified withholding and instalments for this period')];
    return company ? [{id:'id_company_2026',label:['印尼居民企业（2026）','Indonesia resident company (2026)'],
      notice:['仅限以印尼盾申报的境内普通收入，不含上市公司优惠、最终税制、免税收入、境外收入和其他特殊优惠。已核定应税所得按千印尼盾向下取整；第31E条收入总额从已保存明细汇总。全年总额不超过500亿时，自动对归属48亿收入部分的税基适用11%，其余22%。须确认收入完整、已扣退货及销售折扣，未扣费用。',
        'Domestic ordinary income in IDR only; excludes listed-company concessions, final/exempt/foreign income and other special incentives. Established taxable income is rounded down to thousands of rupiah. Saved gross receipts determine article 31E: at total receipts up to IDR 50bn, the rounded base attributable to the first IDR 4.8bn uses 11%; the remainder uses 22%. Confirm all receipts after returns and sales discounts, before expenses.'],
      fields:[money('taxable_income_before_rounding','核定应税所得（千元取整前）','Established taxable income before thousand rounding'),...common,
        confirm('gross_receipts_scope_confirmed','已核实第31E条全部收入范围，且无遗漏的最终计税或免税收入','Complete article 31E receipts checked, with no omitted final or exempt receipts')]}]
      : [{id:'id_resident_2026',label:['印尼居民个人（2026）','Indonesia resident individual (2026)'],
        notice:['仅限全年居民境内普通收入。净所得须已扣核准费用、亏损及宗教捐款；系统扣除按年初资格核定的PTKP，再按千印尼盾向下取整。TK/K表示是否有权使用婚姻附加免税额，0至3表示合资格受抚养人数；不得仅按婚姻登记推定资格。不含夫妻所得合并或分摊、部分年度、最终计税、免税或境外收入；须核对PP20/2026过渡规则。',
          'Full-year resident domestic ordinary income only. Net income must already reflect verified expenses, losses and religious gifts. The system deducts confirmed start-of-year PTKP, then rounds down to thousands of rupiah. TK/K indicates entitlement to the marriage allowance; 0–3 is the qualifying dependent count. Do not infer entitlement from marital registration alone. Excludes combined/spouse allocation, part-year, final, exempt and foreign income; check PP20/2026 transitions.'],
        fields:[money('net_income_before_ptkp','核定净所得（PTKP前）','Established net income before PTKP'),
          {key:'ptkp_status',label:['核定PTKP资格代码','Verified PTKP entitlement code'],options:(['TK/0','TK/1','TK/2','TK/3','K/0','K/1','K/2','K/3'] as const).map(code=>[code,[code,code]])},
          confirm('ptkp_entitlement_confirmed','已核实年初PTKP及受抚养资格','Start-of-year PTKP and dependent entitlement verified'),...common]}];
  }
  if (input.jurisdiction === 'th' && period === '2026-01-01/2026-12-31') {
    const shared = [confirm('ordinary_treatment_confirmed','已核对普通年度税制及排除条件','Ordinary annual treatment and exclusions checked'),
      money('allowed_tax_credits','核定可抵免税额','Allowed tax credits'),prepaid];
    return company ? [{id:'th_company_2026',label:['泰国企业（2026）','Thailand company (2026)'],
      notice:['保存收入须含法定估值调整；核定扣除仅填可扣费用，免税收入另填且不得重复扣除，以前年度亏损须先核实可用年度及金额。系统核对三者与净利润，未使用亏损不代表准予结转。普通税率20%；小企业须核实期末实缴资本不超过500万泰铢、销售及服务收入不超过3000万泰铢，并满足法令规定的连续期间条件。不含投资促进优惠、石油、收入总额计税及最低补足税。',
        'Saved income must include statutory valuation adjustments. Enter only allowed expenses as deductions and exempt income separately without duplication. Verify prior-loss vintages and usable amounts first. The system reconciles net profit; unused losses do not establish carryforward entitlement. Ordinary rate: 20%. SME rates require period-end paid-up capital up to THB 5m, sales/service revenue up to THB 30m and the decree’s continuous-period conditions. Excludes investment incentives, petroleum, gross-receipt and top-up tax regimes.'],
      fields:[money('net_taxable_profit','核定应税净利润','Established net taxable profit'),money('exempt_income','核定免税收入（已含于保存收入）','Verified exempt income included in saved income'),...shared,
        {key:'scheme',label:['企业税率制度','Company rate scheme'],options:[['ordinary',['普通20%税率','Ordinary 20% rate']],['sme',['符合条件的小企业分级税率','Eligible SME tiered rates']]]},
        confirm('sme_eligibility_confirmed','已核实全部小企业条件及连续期间资格','All SME and continuous-period conditions verified')]}]
      : [{id:'th_resident_2026',label:['泰国居民个人（2026）','Thailand resident individual (2026)'],
        notice:['仅限境内普通年度合并计税收入。净应税所得须先核定费用及扣除；非工资应税总收入从已保存明细汇总。比较累进税额与0.5%最低税额，最低税额不超过5000泰铢时豁免该方法。不含境外所得、股息利息单独税制、终止雇佣一次性收入、不动产处置及联合评税。',
          'Domestic ordinary annual income only. Establish expenses and allowances before entering net taxable income. Saved non-employment gross income determines the 0.5% minimum-tax comparison; that method is exempt when its tax does not exceed THB 5,000. Excludes foreign income, separate dividend/interest regimes, termination lump sums, property disposals and joint assessment.'],
        fields:[money('net_taxable_income','核定净应税所得','Established net taxable income'),...shared,
          confirm('assessable_income_classification_confirmed','已按第40条核实工资及非工资收入分类','Section 40 employment and non-employment classification verified')]}];
  }
  if (input.jurisdiction === 'my' && period === '2026-01-01/2026-12-31') {
    if(!company && input.incomes.some(i=>i.category==='dividend')) {
      if(!input.incomes.every(i=>i.source_jurisdiction==='my' && ['dividend','employment','business','rental','interest','royalty','service_remuneration','author_remuneration'].includes(i.category)))return [];
      return [{id:'my_dividend_2026',label:['马来西亚个人股息及普通所得（2026）','Malaysia individual dividends and ordinary income (2026)'],
        notice:['适用于单独评税的境内股息及普通所得。先核定股息与其他所得各自的法定收入、费用和免税项目；股息全年10万令吉门槛由系统合计扣除一次，不要提前扣除，也不要计入案件的扣除额。应课税收入须已扣除该门槛及核定减免；案件扣除额包括费用、排除额与减免。股息计税所得按比例分配并适用2%，其余适用居民累进或非居民30%税率。需核实抵减资格及限额；非居民不得使用居民回扣。联合评税、境外所得、结转亏损和特殊税率收入另行处理。结果为申报取整前金额。',
          'Separate assessment of domestic dividends and ordinary income. Establish statutory income, expenses and exemptions for each source first. The annual MYR100,000 dividend threshold is deducted once automatically: do not subtract it from the dividend input or include it in saved deductions. Chargeable income must reflect that threshold and established reliefs; saved deductions include expenses, exclusions and reliefs. Dividend chargeable income is allocated proportionately and taxed at 2%; the remainder uses resident bands or the nonresident 30% rate. Verify rebate/credit eligibility and caps; no resident rebates for nonresidents. Joint assessment, foreign income, carried losses and special-rate income need separate treatment. Results precede assessment rounding.'],
        fields:[money('dividend_statutory_before_threshold','股息法定收入（未减年度10万门槛）','Dividend statutory income before annual MYR100,000 threshold'),
          money('ordinary_statutory_income','其他普通所得的法定收入','Other ordinary statutory income'),
          money('chargeable_income','扣除门槛及减免后的应课税收入','Chargeable income after threshold and reliefs'),
          money('allowed_rebates','核定可用税额回扣','Allowed tax rebates'),
          money('allowed_tax_credits','核定可抵免税额','Allowed tax credits'),prepaid,
          confirm('separate_domestic_assessment_verified','已核实单独评税、境内普通所得及排除条件','Separate domestic assessment and ordinary-income exclusions verified'),
          confirm('dividend_scope_verified','已核实全年所有股息、费用和免税范围','All annual dividends, expenses and exemptions verified'),
          confirm('bases_verified','已核实法定收入、扣除与减免资格及计税基础','Statutory income, deduction and relief eligibility, and tax bases verified'),
          confirm('settlement_inputs_verified','已核实回扣、抵免限额及预缴归属','Rebate eligibility, credit limits and prepayments verified')]}];
    }
    const fields = [money('chargeable_income','核定应课税收入','Established chargeable income'),
      confirm('ordinary_treatment_confirmed','已核对普通税制及排除条件','Ordinary treatment and exclusions checked'),
      money('allowed_rebates','核定可用税额回扣','Allowed tax rebates'),
      money('allowed_tax_credits','核定可抵免税额','Allowed tax credits'),prepaid];
    if (!company && input.residency==='resident') {
      input.incomes.forEach((_item,n)=>{
        const prefix=`my_source_${n}_`;
        for (const [key,zh,label] of [['additions','核定加回','Verified additions'],['deductions','核定费用扣除','Allowed source deductions'],['statutory_charges','法定加计','Statutory charges'],['statutory_allowances','资本免税额','Statutory allowances']])
          fields.push(money(prefix+key,`收入${n+1}：${zh}`,`Source ${n+1}: ${label}`));
      });
      fields.push(money('my_schedule4_additions','附表4加计','Schedule 4 additions'),
        money('my_total_deductions','按法定顺序核定的总所得扣除','Verified total-income deductions'),
        money('my_personal_reliefs','核定个人减免','Allowed personal reliefs'),
        confirm('my_eligibility','已核验来源调整、亏损年度和扣除限额','Source adjustments and deduction eligibility verified'),
        confirm('my_separate','已核验单独评税','Separate assessment verified'));
    }
    return company ? [{id:'my_company_2026',label:['马来西亚企业（2026）','Malaysia company (2026)'],
      notice:['仅限普通公司；不含纳闽、再保险、特殊优惠或最低补足税。小企业税率须符合马来西亚注册及居民身份、期初普通股实缴资本不超过250万、营业总收入不超过5000万令吉，并核对关联公司及超过20%境外公司或非公民持股的排除条件。',
        'Ordinary companies only; excludes Labuan, reinsurance, special incentives and minimum top-up tax. SME rates require Malaysian incorporation/residence, ordinary paid-up capital up to MYR 2.5m and business gross income up to MYR 50m. Check related-company exclusions and the exclusion for more than 20% foreign-company or non-citizen ownership.'],
      fields:[...fields,{key:'scheme',label:['企业税率制度','Company rate scheme'],options:[['ordinary',['普通24%税率','Ordinary 24% rate']],['sme',['符合条件的小企业分级税率','Eligible SME tiered rates']]]},
        confirm('sme_eligibility_confirmed','已核实符合全部小企业税率条件','All SME rate conditions verified')]}]
      : [{id:'my_individual_2026',label:['马来西亚个人（2026）','Malaysia individual (2026)'],
        notice:['按已保存居民身份适用普通累进或非居民30%税率。须先核定可扣除项目及减免，不含个人股息单独税制、资本利得、合并评税或特殊收入税率；非居民不得使用居民税额回扣。',
          'Uses saved residency for ordinary progressive rates or the non-resident 30% rate. Establish deductions and reliefs first. Excludes separate dividend taxation, capital gains, joint assessment and special-rate income. Non-residents cannot use resident rebates.'],fields}];
  }
  if (input.jurisdiction === 'cn' && period === '2026-01-01/2026-12-31') {
    if(!company && input.incomes.every(item=>item.category==='business'))return [{id:'cn_business_2026',
      label:['中国居民个人经营所得（2026）','China resident business income (2026)'],
      notice:['按同一纳税人全年境内经营所得汇总计算。应税所得须与已保存收入减核定扣除、可用亏损一致。基本减除费用、专项等个人扣除如分配至经营所得，须已计入保存的扣除且不得在综合所得重复使用；系统不再自动扣6万元。个体工商户的200万元减半额度按年度合并，不按店铺重复计算；个人独资、合伙等其他经营主体不能直接选择个体工商户优惠。混合优惠资格所得须另行核定分配，本入口不处理。结果为申报取整前金额。',
        'Aggregate the same taxpayer’s full-year domestic business income. Taxable income must reconcile to saved income less established deductions and eligible losses. Include any personal deductions allocated to business income in saved deductions without duplicating comprehensive-income claims; no automatic CNY60,000 deduction. The individual-operator CNY2m half-relief cap applies once across the year, not per shop. Sole proprietorships and partnerships do not automatically qualify as individual operators. Mixed eligible/ineligible income requires separate allocation. Results are before assessment rounding.'],
      fields:[money('taxable_income','核定应纳税所得额','Established taxable income'),
        {key:'business_form',label:['核实后的经营主体分类','Verified business classification'],options:[['individual_operator',['全部为符合条件的个体工商户经营所得','All income qualifies as individual-operator business']],['other_business',['其他经营所得（不适用个体工商户减半）','Other business income (no individual-operator half relief)']]]},
        money('allowed_other_tax_reductions','其他政策核定减免税额','Allowed other tax reductions'),prepaid,
        confirm('annual_aggregation_and_classification_verified','已核实全年多处经营汇总及主体资格','Annual business aggregation and classification verified'),
        confirm('deductions_losses_and_no_double_claim_verified','已核实扣除、亏损资格且未重复扣除','Deductions, losses and no duplicate claims verified')]}];
    return company ? [{id:'cn_company_2026',label:['中国企业普通税率（2026）','China ordinary company tax (2026)'],
      notice:['仅限境内普通25%税率；排除优惠税制、非居民扣缴及境外所得处理。计税基础须已完成纳税调整和亏损抵扣。',
        'Domestic ordinary 25% regime only. Excludes concessions, non-resident withholding and foreign-income treatment. Establish the tax base after adjustments and allowable losses.'],
      fields:[money('taxable_income','核定应纳税所得额','Established taxable income'),...cnCompanyExclusions,confirm('normal_rate_confirmed','已核对普通税率适用条件','Normal rate eligibility checked'),money('allowed_tax_credits','核定可抵免税额','Allowed tax credits'),prepaid]},
      {id:'cn_small_company_2026',label:['中国小型微利企业（2026）','China small-low-profit company (2026)'],
      notice:['境内居民企业须从事国家非限制和禁止行业，全年应纳税所得额不超过300万元、从业人数不超过300人、资产不超过5000万元，三项须同时满足。人数含劳务派遣；人数及资产填法定全年季度平均值，不能填年末值。季度平均为季初、季末之和除2，全年取四季平均；年中开业或终止须按实际经营期核定。应税所得须与保存的收入减核定扣除和可用亏损一致。按25%计入税基、适用20%税率，未计抵免前实际税负5%。不含境外所得及其他特殊优惠叠加。',
        'Domestic resident enterprise in a non-restricted, non-prohibited industry. Annual taxable income must not exceed CNY3m, employees300 and assets CNY50m; all conditions must hold. Include dispatched workers. Enter verified statutory annual quarterly averages, not year-end figures: each quarter averages opening and closing values, then average all four quarters; verify actual operating-period rules for opening/closing mid-year. Taxable income must reconcile to saved income less established deductions and eligible losses. Include25% of income at a20% rate (5% before credits). Excludes foreign income and other special preference combinations.'],
      fields:[money('taxable_income','核定应纳税所得额','Established taxable income'),...cnCompanyExclusions,
        money('annual_average_employees','法定全年季度平均从业人数','Statutory annual quarterly-average employees'),
        money('annual_average_assets','法定全年季度平均资产总额（元）','Statutory annual quarterly-average assets (CNY)'),
        confirm('unrestricted_industry_confirmed','已核实属于非限制和非禁止行业','Non-restricted and non-prohibited industry verified'),
        confirm('statutory_averages_and_eligibility_verified','已核实法定平均值、居民资格和优惠适用条件','Statutory averages, residence and preference eligibility verified'),
        money('allowed_tax_credits','核定可抵免税额','Allowed tax credits'),prepaid]}]
    : [{id:'cn_comprehensive_2026',label:['中国居民综合所得（2026）','China resident comprehensive income (2026)'],
      notice:['仅限境内工资、劳务报酬、稿酬及特许权使用费，收入总额取自已保存资料。已保存扣除总额须等于下方专项、专项附加、其他及捐赠扣除之和；不要重复计入系统自动处理的6万元基本减除费用和收入类别费用减除。不含单独计税奖金、股权激励或其他所得；本流程不抵扣结转亏损或境外税款。',
        'Domestic wages, services, author remuneration and royalties only; gross amounts come from saved facts. Saved deductions must equal special, additional, other and donation deductions below. Do not include the automatic CNY 60,000 basic deduction or income-category expense reductions. Separate bonuses, equity schemes and other income are excluded; this workflow cannot consume carried losses or foreign tax credits.'],
      fields:[money('allowed_special_deductions','核定专项扣除','Allowed special deductions'),money('allowed_additional_deductions','核定专项附加扣除','Allowed additional deductions'),money('allowed_other_deductions','核定其他扣除','Allowed other deductions'),money('allowed_donations','核定捐赠扣除','Allowed donations'),money('allowed_tax_reductions','核定减免税额','Allowed tax reductions'),prepaid,confirm('domestic_normal_treatment_confirmed','已核对境内居民综合所得普通处理','Domestic resident comprehensive treatment checked')]}];
  }
  if (input.jurisdiction === 'sg' && period === '2025-01-01/2025-12-31') {
    const rateOnly: IncomePolicy = {id:'sg_resident_ya2026',label:['新加坡居民税率表核算（YA 2026）','Singapore resident rate schedule (YA 2026)'],
      notice:['输入扣除及个人减免后核定的应课税收入。结果仅为居民税率表计算，尚未计入抵免、预缴或评税舍入。',
        'Enter established chargeable income after deductions and personal reliefs. This is the resident rate calculation before credits, prepayments and assessment rounding.'],
      fields:[money('chargeable_income','核定应课税收入','Established chargeable income')]};
    if (!company && input.residency==='resident' && input.incomes.every(i=>i.category==='employment'&&i.source_jurisdiction==='sg')) return [{
      id:'sg_employment_ya2026',label:['新加坡居民受雇所得结算（YA 2026）','Singapore resident employment settlement (YA 2026)'],
      notice:['以已保存的2025年境内应税薪酬计算。已保存扣除额须等于费用、可用捐赠扣除、CPF及其他个人减免之和（总限额前）；不要重复计入自动计算的劳动所得减免。须核对每项资格、限额及家庭分配；其他减免不含已于YA 2026失效的课程费用减免。PTR填本人的核定可用余额，未用余额结转，不退款。仅普通受雇收入，不含税务清算、特殊股票计划、境外抵免或亏损；结果尚未作评税舍入。',
        'Uses saved 2025 domestic taxable employment income. Saved deductions equal expenses, usable donation deduction, CPF and other personal relief claims before the overall cap; exclude automatic earned income relief. Verify each entitlement, limit and family allocation; other reliefs exclude course fees, lapsed from YA 2026. PTR is your verified available balance; unused PTR carries forward and is not refunded. Ordinary employment only, excluding tax clearance, special share schemes, foreign credits and losses; before assessment rounding.'],
      fields:[{key:'birth_date',label:['出生日期','Date of birth'],date:true,dateMin:'1900-01-01'},
        confirm('disability_relief_eligible','符合劳动所得残障减免条件','Eligible for disability earned income relief'),
        money('allowed_employment_expenses','核定受雇费用扣除','Allowed employment expenses'),
        money('allowed_donation_deduction','本期可用捐赠扣除额（已核定倍数）','Usable donation deduction after verified multiplier'),
        money('allowed_cpf_relief','核定员工CPF减免','Allowed employee CPF relief'),
        money('allowed_other_personal_reliefs','其他核定个人减免（不含上述项目）','Other allowed personal reliefs excluding items above'),
        money('available_parenthood_rebate','本人核定可用PTR余额','Verified available PTR balance'),prepaid,
        confirm('eligibility_and_allocations_verified','已核对YA 2026资格、单项限额、分配及PTR余额','YA 2026 eligibility, individual limits, allocation and PTR balance verified')]},rateOnly];
    return company ? [{id:'sg_company_ya2026',label:['新加坡企业（课税年2026）','Singapore company (YA 2026)'],
      notice:['仅限普通税率收入；须先核对税基、减免资格及可用抵免。现金补助单独列示，不重复扣税。',
        'Normal-rate income only. Establish the tax base, exemption eligibility and allowed credits first. The cash grant is separate from tax payable.'],
      fields:[money('normal_chargeable_income','普通税率应课税收入','Normal-rate chargeable income'),ordinary,
        {key:'exemption_scheme',label:['减免制度','Exemption scheme'],options:[['partial',['部分减免','Partial exemption']],['startup',['初创企业减免','Start-up exemption']],['none',['不适用减免','None']]]},
        confirm('startup_eligibility_confirmed','符合初创企业减免条件','Eligible for start-up exemption'),confirm('cash_grant_eligible','符合本课税年现金补助条件','Eligible for this YA cash grant'),money('allowed_tax_setoff','核定可抵免税额','Allowed tax set-off')]}]
      : [rateOnly];
  }
  if (input.jurisdiction === 'hk' && period === '2025-04-01/2026-03-31') {
    const profits: IncomePolicy = {id:'hk_profits_2025_26',label:['香港利得税（2025/26）','Hong Kong profits tax (2025/26)'],
      notice:['仅限普通公司或独资业务。须核对两级制资格、关联实体选择及排除条件；不包含合伙分配、个人入息课税或境外抵免。',
        'Ordinary corporation or sole proprietor only. Verify two-tier eligibility, connected-entity nomination and exclusions. Excludes partnerships, personal assessment and foreign credits.'],
      fields:[money('assessable_profits','核定应评税利润','Established assessable profits'),{key:'business_form',label:['业务形式','Business form'],options: company ? [['corporation',['公司','Corporation']]] : [['sole_proprietor',['独资','Sole proprietor']]]},confirm('two_tier_eligible','符合两级制资格','Eligible for two-tier rates'),ordinary,hkPrepaid]};
    if (company) return [profits];
    if (input.incomes.every(i=>i.category==='rental' && i.source_jurisdiction==='hk')) return [{
      id:'hk_property_2025_26',label:['香港物业税（2025/26）','Hong Kong property tax (2025/26)'],
      notice:['每条租金收入对应一项单独拥有的香港物业，收入须包括应收租金、收回坏账及本期租赁溢价等应计代价。保存的扣除总额只填不可追回租金和业主已付差饷；20%法定扣除自动计算。差饷不含地租；不另扣管理费、修缮费或按揭利息。不含共同拥有、物业经营业务、个人入息课税、往年坏账追溯减免或下期暂缴税。',
        'Each rental entry represents one solely owned Hong Kong property. Include receivable rent, recovered bad debts and allocated lease premiums in saved gross consideration. Saved deductions equal irrecoverable rent plus owner-paid rates; the 20% allowance is automatic. Rates exclude government rent; management, repair costs and mortgage interest are not additional deductions. Excludes joint ownership, property business, personal assessment, prior-year bad-debt relief and next-year provisional tax.'],
      fields:[...input.incomes.flatMap((_item,n)=>[
        money(`hk_property_${n}_irrecoverable_rent`,`物业${n+1}：不可追回租金（扣除押金抵销）`,`Property ${n+1}: irrecoverable rent after deposit offset`),
        money(`hk_property_${n}_owner_rates_paid`,`物业${n+1}：业主承担且已付差饷`,`Property ${n+1}: rates borne and paid by owner`)]),
        confirm('sole_ownership_and_separate_assessment_verified','已核实单独拥有及独立物业税评税','Sole ownership and separate property assessment verified'),
        confirm('consideration_and_deductions_verified','已核实完整应计租赁代价及扣除证据','Complete rental consideration and deduction evidence verified'),hkPrepaid]}];
    if (input.incomes.some(i=>i.category==='rental')) return [];
    const salaries: IncomePolicy = {id:'hk_salaries_2025_26',label:['香港薪俸税（2025/26）','Hong Kong salaries tax (2025/26)'],
      notice:['仅限单独评税的薪俸所得，不比较合并或个人入息课税。已缴税额须归属本期最终评税，不含下期暂缴税。',
        'Separate salaries assessment only; joint and personal assessment are not compared. Prepayments must belong to this final assessment, not the next provisional assessment.'],
      fields:[money('net_income','扣除后、免税额前的入息净额','Net income before allowances'),money('allowed_allowances','核定免税额','Allowed allowances'),hkPrepaid,confirm('ordinary_separate_assessment_confirmed','已核对普通单独薪俸评税适用条件','Ordinary separate salaries assessment checked')]};
    if (input.incomes.every(i=>i.category==='employment')) return [salaries];
    if (input.incomes.some(i=>i.category==='employment')) return [];
    return [profits];
  }
  if (input.jurisdiction === 'ae' && period === '2026-01-01/2026-12-31') {
    return [{id:'ae_ordinary_2026',label:['阿联酋普通企业税（2026）','UAE ordinary corporate tax (2026)'],
      notice:['核对普通独立纳税人身份，排除豁免、合资格自由区、税务集团和最低补足税。个人须合并全部适用经营营业额；工资和符合法定定义的个人投资收入另行排除。',
        'Verify an ordinary standalone taxpayer outside exempt, qualifying free-zone, tax-group and minimum-top-up regimes. Individuals must aggregate all in-scope business turnover; statutory wage and personal-investment exclusions are separate.'],
      fields:[money('taxable_income','核定应纳税所得额','Established taxable income'),ordinary,confirm('no_relief_elected_confirmed','已确认未选择小企业等税收减免','Confirmed no small-business or other relief election'),money('allowed_foreign_tax_credit','按来源核定的境外税抵免','Allowed foreign tax credit by source'),prepaid,...(company?[]:[money('natural_person_business_turnover','个人全部适用经营营业额','Total in-scope personal business turnover'),confirm('natural_person_activity_classification_confirmed','已依法核对经营和排除收入的分类','Statutory business and excluded-income classification checked')])]}];
  }
  return [];
}

export const resultLabels: Record<string, Label> = {
  dividend_statutory_before_threshold:['门槛扣除前股息法定收入','Dividend statutory income before threshold'],
  dividend_statutory_income:['门槛扣除后股息法定收入','Dividend statutory income after threshold'],
  dividend_threshold_used:['本次使用的年度股息门槛','Annual dividend threshold used'],
  ordinary_statutory_income:['其他普通所得法定收入','Other ordinary statutory income'],
  aggregate_income:['合计收入','Aggregate income'],
  dividend_chargeable_income:['股息应课税收入','Dividend chargeable income'],
  ordinary_chargeable_income:['普通所得应课税收入','Ordinary chargeable income'],
  dividend_tax:['股息税额','Dividend tax'],
  ordinary_tax:['普通所得税额','Ordinary income tax'],
  reconciled_deductions:['与案件一致的扣除额','Deductions reconciled to case'],
  dividend_credit:['股息抵免额','Dividend tax credit'],
  refundable_dividend_credit:['超过年度税额的可退股息抵免','Refundable dividend credit exceeding annual tax'],
  separate_final_dividend_tax:['单独结清的股息最终税款','Separate final dividend tax'],
  annual_assessable_income:['年度应税总收入（含适用股息还原）','Annual assessable income including applicable dividend gross-up'],
  preferential_taxable_income:['优惠计入应税所得额','Taxable income after preferential inclusion'],
  small_company_tax_reduction:['小型微利企业优惠减免税额','Small-low-profit company tax reduction'],
  half_relief_eligible_base:['个体工商户减半优惠适用所得额','Income eligible for individual-operator half relief'],
  allowed_other_tax_reductions:['其他政策减免税额','Other policy tax reductions'],
  individual_operator_half_reduction:['个体工商户减半政策减免税额','Individual-operator half-relief amount'],
  corporation_tax:['法人税','Corporation tax'],local_corporation_tax:['地方法人税（国税）','Local corporation tax (national)'],
  defence_tax:['防卫特别法人税','Defence special corporation tax'],
  corporation_interim_liability:['法人税中间申告义务','Corporation interim-return liability'],
  local_corporation_interim_liability:['地方法人税中间申告义务','Local corporation interim-return liability'],
  corporation_balance_due:['法人税单独补／退额','Separate corporation tax balance'],
  local_corporation_balance_due:['地方法人税单独补／退额','Separate local corporation tax balance'],
  salary_income_before_adjustment:['工资所得调整前金额','Salary income before adjustment'],
  salary_income_adjustment:['工资所得调整扣除','Salary income adjustment deduction'],
  net_business_income:['经营净所得','Net business income'],total_income:['合计净所得','Total net income'],
  basic_deduction:['基本扣除','Basic deduction'],other_income_deductions:['其他所得扣除','Other income deductions'],
  reconstruction_tax:['复兴特别所得税','Reconstruction special income tax'],
  withheld_tax:['本年度源泉扣缴税额','Tax withheld for this year'],
  estimated_tax:['有效通知核定予定纳税额','Effective notified estimated-tax liability'],
  declared_tax_after_withholding:['扣缴后申告纳税额（正数取整至百日元）','Declared tax after withholding (positive amounts truncated to JPY 100)'],
  return_rounding_adjustment:['申报取整调整','Return rounding adjustment'],
  rate:['适用税率（小数）','Applicable rate (decimal)'],exempt_tax:['免征税额','Exempt tax'],
  other_incentive_reduction:['其他税额优惠','Other incentive reduction'],annual_reduction:['年度减税额','Annual tax reduction'],
  personal_deduction:['本人扣除额','Personal deduction'],dependent_deduction:['受抚养人扣除额','Dependent deduction'],
  deductible_insurance:['可扣除保险','Deductible insurance'],article11_deductions:['第11条扣除','Article 11 deductions'],
  taxable_income_before_rounding:['取整前应税所得','Taxable income before rounding'],
  gross_income_tax:['减免前所得税','Income tax before relief'],
  resident_rebate:['居民个人税额退抵','Resident individual rebate'],
  income_tax_after_rebate:['退抵后所得税','Income tax after rebate'],
  gross_surcharge:['减免前附加税','Surcharge before relief'],
  surcharge_marginal_relief:['附加税边界减免','Surcharge marginal relief'],
  surcharge:['减免后附加税','Surcharge after relief'],
  health_education_cess:['健康教育费','Health and education cess'],
  tds_tcs_credit:['本期扣缴／代收税额','Current-period TDS/TCS credit'],
  advance_tax_paid:['实缴预缴税款','Advance tax paid'],
  self_assessment_paid:['实缴自评税款总额','Total self-assessment payments'],
  total_interest_due:['累计应计利息','Cumulative interest due'],
  total_fee_due:['累计应计费用','Cumulative fees due'],
  total_payments:['可用已缴款合计','Total credited payments'],
  refund_due:['预计应退金额','Calculated refund due'],
  normal_company_rate:['普通企业税率','Normal company rate'],
  mat_book_profit:['MAT调整后账面利润','Adjusted MAT book profit'],
  normal_tax_including_surcharge_cess:['普通税额（含附加税与教育费）','Normal tax including surcharge and cess'],
  mat_tax_including_surcharge_cess:['MAT税额（含附加税与教育费）','MAT including surcharge and cess'],
  legacy_mat_credit_used:['使用历史MAT抵免','Legacy MAT credit used'],
  new_mat_credit:['本期新增MAT抵免','New MAT credit'],
  net_income_before_ptkp:['PTKP前净所得','Net income before PTKP'],ptkp_allowance:['核定PTKP免税额','Verified PTKP allowance'],
  article31e_gross_receipts:['第31E条收入总额','Article 31E gross receipts'],
  article31e_eligible_base:['第31E条优惠税基','Article 31E reduced-rate base'],article31e_other_base:['普通税率税基','Ordinary-rate base'],
  article31e_reduced_tax:['优惠税率税额','Reduced-rate tax'],ordinary_rate_tax:['普通税率税额','Ordinary-rate tax'],
  net_taxable_profit:['应税净利润','Net taxable profit'],net_taxable_income:['净应税所得','Net taxable income'],
  nonemployment_assessable_gross:['非工资应税总收入','Non-employment assessable gross income'],
  progressive_tax:['累进税额','Progressive tax'],minimum_tax_before_exemption:['豁免前最低税额','Minimum tax before exemption'],
  minimum_tax:['适用最低税额','Applicable minimum tax'],
  allowed_rebates:['核定税额回扣','Allowed tax rebates'],allowed_tax_credits:['核定抵免税额','Allowed tax credits'],
  gross_tax:['减免和抵免前税额','Tax before reductions and credits'], annual_liability:['本期税额','Annual liability'],
  earned_income_relief:['劳动所得减免','Earned income relief'], personal_reliefs_before_cap:['限额前个人减免','Personal reliefs before cap'],
  personal_reliefs_allowed:['限额后个人减免','Personal reliefs after cap'], personal_reliefs_disallowed_by_cap:['超过总限额的减免','Reliefs exceeding overall cap'],
  parenthood_rebate_used:['本期使用PTR','PTR used this year'], parenthood_rebate_carried_forward:['结转PTR余额（不退款）','PTR carried forward (not refundable)'],
  final_tax:['本期税额','Tax for this assessment'], net_tax:['减免后税额','Tax after relief'],balance_due:['尚应缴金额（负数表示多缴）','Balance due (negative means overpaid)'],
  net_assessable_value:['应评税净值','Net assessable value'],statutory_allowance:['法定扣除','Statutory allowance'],
  taxable_income:['应纳税所得额','Taxable income'],chargeable_income:['应课税收入','Chargeable income'],
  tax_reduction:['税额减免','Tax reduction'],cit_rebate:['企业税回扣','Corporate tax rebate'],cash_grant_separate:['单独列示的现金补助','Cash grant, separate from tax'],
  prepaid_tax:['本期预缴税额','Prepaid tax for this period'],prepaid_final_tax:['本期最终评税已缴税额','Prepaid final tax'],
};
