import type { IncomeTaxInput } from './income-tax';

export type IncomeRun = {
  id: string; input_revision: number; created_at: string; status: string; snapshot_hash: string;
  result: Record<string, unknown>;
};
type Label = [string, string];
export type BasisField = { key: string; label: Label; options?: [string, Label][]; boolean?: boolean };
const money = (key: string, zh: string, en: string): BasisField => ({key, label:[zh,en]});
const confirm = (key: string, zh: string, en: string): BasisField => ({key,label:[zh,en],boolean:true});
const prepaid = money('prepaid_tax','归属本期的预缴税额','Prepaid tax for this period');
const hkPrepaid = money('prepaid_final_tax','归属本期最终评税的已缴税额','Prepaid final tax for this assessment');
const ordinary = confirm('ordinary_regime_confirmed','已核对适用普通税制及其排除条件','Ordinary regime and exclusions checked');
export type IncomePolicy = { id: string; label: Label; notice: Label; fields: BasisField[] };

export function policies(input: IncomeTaxInput): IncomePolicy[] {
  const company = input.subject === 'company';
  const period = input.period_start + '/' + input.period_end;
  if (input.jurisdiction === 'th' && period === '2026-01-01/2026-12-31') {
    const shared = [confirm('ordinary_treatment_confirmed','已核对普通年度税制及排除条件','Ordinary annual treatment and exclusions checked'),
      money('allowed_tax_credits','核定可抵免税额','Allowed tax credits'),prepaid];
    return company ? [{id:'th_company_2026',label:['泰国企业（2026）','Thailand company (2026)'],
      notice:['以已完成纳税调整的净利润为基础。普通税率20%；小企业须核实期末实缴资本不超过500万泰铢、销售及服务收入不超过3000万泰铢，并满足法令规定的连续期间条件。不含投资促进优惠、石油、收入总额计税及最低补足税。',
        'Use net profit after verified tax adjustments. Ordinary rate: 20%. SME rates require period-end paid-up capital up to THB 5m, sales/service revenue up to THB 30m and the decree’s continuous-period conditions. Excludes investment incentives, petroleum, gross-receipt and top-up tax regimes.'],
      fields:[money('net_taxable_profit','核定应税净利润','Established net taxable profit'),...shared,
        {key:'scheme',label:['企业税率制度','Company rate scheme'],options:[['ordinary',['普通20%税率','Ordinary 20% rate']],['sme',['符合条件的小企业分级税率','Eligible SME tiered rates']]]},
        confirm('sme_eligibility_confirmed','已核实全部小企业条件及连续期间资格','All SME and continuous-period conditions verified')]}]
      : [{id:'th_resident_2026',label:['泰国居民个人（2026）','Thailand resident individual (2026)'],
        notice:['仅限境内普通年度合并计税收入。净应税所得须先核定费用及扣除；非工资应税总收入从已保存明细汇总。比较累进税额与0.5%最低税额，最低税额不超过5000泰铢时豁免该方法。不含境外所得、股息利息单独税制、终止雇佣一次性收入、不动产处置及联合评税。',
          'Domestic ordinary annual income only. Establish expenses and allowances before entering net taxable income. Saved non-employment gross income determines the 0.5% minimum-tax comparison; that method is exempt when its tax does not exceed THB 5,000. Excludes foreign income, separate dividend/interest regimes, termination lump sums, property disposals and joint assessment.'],
        fields:[money('net_taxable_income','核定净应税所得','Established net taxable income'),...shared,
          confirm('assessable_income_classification_confirmed','已按第40条核实工资及非工资收入分类','Section 40 employment and non-employment classification verified')]}];
  }
  if (input.jurisdiction === 'my' && period === '2026-01-01/2026-12-31') {
    const fields = [money('chargeable_income','核定应课税收入','Established chargeable income'),
      confirm('ordinary_treatment_confirmed','已核对普通税制及排除条件','Ordinary treatment and exclusions checked'),
      money('allowed_rebates','核定可用税额回扣','Allowed tax rebates'),
      money('allowed_tax_credits','核定可抵免税额','Allowed tax credits'),prepaid];
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
    return company ? [{id:'cn_company_2026',label:['中国企业普通税率（2026）','China ordinary company tax (2026)'],
      notice:['仅限境内普通25%税率；排除优惠税制、非居民扣缴及境外所得处理。计税基础须已完成纳税调整和亏损抵扣。',
        'Domestic ordinary 25% regime only. Excludes concessions, non-resident withholding and foreign-income treatment. Establish the tax base after adjustments and allowable losses.'],
      fields:[money('taxable_income','核定应纳税所得额','Established taxable income'),confirm('normal_rate_confirmed','已核对普通税率适用条件','Normal rate eligibility checked'),money('allowed_tax_credits','核定可抵免税额','Allowed tax credits'),prepaid]}]
    : [{id:'cn_comprehensive_2026',label:['中国居民综合所得（2026）','China resident comprehensive income (2026)'],
      notice:['仅限境内工资、劳务报酬、稿酬及特许权使用费，收入总额取自已保存资料。不含单独计税奖金、股权激励或其他所得。',
        'Domestic wages, services, author remuneration and royalties only; gross amounts come from saved facts. Separate bonuses, equity schemes and other income are excluded.'],
      fields:[money('allowed_special_deductions','核定专项扣除','Allowed special deductions'),money('allowed_additional_deductions','核定专项附加扣除','Allowed additional deductions'),money('allowed_other_deductions','核定其他扣除','Allowed other deductions'),money('allowed_donations','核定捐赠扣除','Allowed donations'),money('allowed_tax_reductions','核定减免税额','Allowed tax reductions'),prepaid,confirm('domestic_normal_treatment_confirmed','已核对境内居民综合所得普通处理','Domestic resident comprehensive treatment checked')]}];
  }
  if (input.jurisdiction === 'sg' && period === '2025-01-01/2025-12-31') {
    return company ? [{id:'sg_company_ya2026',label:['新加坡企业（课税年2026）','Singapore company (YA 2026)'],
      notice:['仅限普通税率收入；须先核对税基、减免资格及可用抵免。现金补助单独列示，不重复扣税。',
        'Normal-rate income only. Establish the tax base, exemption eligibility and allowed credits first. The cash grant is separate from tax payable.'],
      fields:[money('normal_chargeable_income','普通税率应课税收入','Normal-rate chargeable income'),ordinary,
        {key:'exemption_scheme',label:['减免制度','Exemption scheme'],options:[['partial',['部分减免','Partial exemption']],['startup',['初创企业减免','Start-up exemption']],['none',['不适用减免','None']]]},
        confirm('startup_eligibility_confirmed','符合初创企业减免条件','Eligible for start-up exemption'),confirm('cash_grant_eligible','符合本课税年现金补助条件','Eligible for this YA cash grant'),money('allowed_tax_setoff','核定可抵免税额','Allowed tax set-off')]}]
      : [{id:'sg_resident_ya2026',label:['新加坡居民个人（课税年2026）','Singapore resident individual (YA 2026)'],
        notice:['输入扣除及个人减免后核定的应课税收入。结果仅为居民税率表计算，尚未计入抵免、预缴或评税舍入。',
          'Enter established chargeable income after deductions and personal reliefs. This is the resident rate calculation before credits, prepayments and assessment rounding.'],
        fields:[money('chargeable_income','核定应课税收入','Established chargeable income')]}];
  }
  if (input.jurisdiction === 'hk' && period === '2025-04-01/2026-03-31') {
    const profits: IncomePolicy = {id:'hk_profits_2025_26',label:['香港利得税（2025/26）','Hong Kong profits tax (2025/26)'],
      notice:['仅限普通公司或独资业务。须核对两级制资格、关联实体选择及排除条件；不包含合伙分配、个人入息课税或境外抵免。',
        'Ordinary corporation or sole proprietor only. Verify two-tier eligibility, connected-entity nomination and exclusions. Excludes partnerships, personal assessment and foreign credits.'],
      fields:[money('assessable_profits','核定应评税利润','Established assessable profits'),{key:'business_form',label:['业务形式','Business form'],options: company ? [['corporation',['公司','Corporation']]] : [['sole_proprietor',['独资','Sole proprietor']]]},confirm('two_tier_eligible','符合两级制资格','Eligible for two-tier rates'),ordinary,hkPrepaid]};
    return company ? [profits] : [{id:'hk_salaries_2025_26',label:['香港薪俸税（2025/26）','Hong Kong salaries tax (2025/26)'],
      notice:['仅限单独评税的薪俸所得，不比较合并或个人入息课税。已缴税额须归属本期最终评税，不含下期暂缴税。',
        'Separate salaries assessment only; joint and personal assessment are not compared. Prepayments must belong to this final assessment, not the next provisional assessment.'],
      fields:[money('net_income','扣除后、免税额前的入息净额','Net income before allowances'),money('allowed_allowances','核定免税额','Allowed allowances'),hkPrepaid,confirm('ordinary_separate_assessment_confirmed','已核对普通单独薪俸评税适用条件','Ordinary separate salaries assessment checked')]},profits];
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
  net_taxable_profit:['应税净利润','Net taxable profit'],net_taxable_income:['净应税所得','Net taxable income'],
  nonemployment_assessable_gross:['非工资应税总收入','Non-employment assessable gross income'],
  progressive_tax:['累进税额','Progressive tax'],minimum_tax_before_exemption:['豁免前最低税额','Minimum tax before exemption'],
  minimum_tax:['适用最低税额','Applicable minimum tax'],
  allowed_rebates:['核定税额回扣','Allowed tax rebates'],allowed_tax_credits:['核定抵免税额','Allowed tax credits'],
  gross_tax:['减免和抵免前税额','Tax before reductions and credits'], annual_liability:['本期税额','Annual liability'],
  final_tax:['本期税额','Tax for this assessment'], net_tax:['减免后税额','Tax after relief'],balance_due:['尚应缴金额（负数表示多缴）','Balance due (negative means overpaid)'],
  taxable_income:['应纳税所得额','Taxable income'],chargeable_income:['应课税收入','Chargeable income'],
  tax_reduction:['税额减免','Tax reduction'],cit_rebate:['企业税回扣','Corporate tax rebate'],cash_grant_separate:['单独列示的现金补助','Cash grant, separate from tax'],
  prepaid_tax:['本期预缴税额','Prepaid tax for this period'],prepaid_final_tax:['本期最终评税已缴税额','Prepaid final tax'],
};
