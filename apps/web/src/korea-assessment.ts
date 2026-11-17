import type { BasisField, IncomePolicy } from './income-assessment';

const field = (key:string, zh:string, en:string):BasisField => ({key,label:[zh,en]});
const check = (key:string, zh:string, en:string):BasisField => ({...field(key,zh,en),boolean:true});
const count = (value:string|undefined, fallback:number) => /^\d+$/.test(value||'') ? Math.min(1000,Number(value)) : fallback;
export const localAmounts = [
  ['relief','减免税额','Relief'],['penalty','罚款','Penalty'],['additional_tax','加算税额','Additional tax'],
  ['other_payments','其他已缴款','Other payments'],['rate_adjustment_increase','地方税率调增','Municipal rate increase'],
  ['rate_adjustment_decrease','地方税率调减','Municipal rate decrease'],
] as const;
export function koreaPolicy(values:Record<string,string>):IncomePolicy {
  const fields:BasisField[] = [field('national_taxable_base','国税核定应税所得','Established national taxable base'),
    field('local_taxable_base','独立核定地方税税基','Independently established local taxable base'),
    {key:'n_minimum_regime',label:['最低税分类','Minimum-tax classification'],options:[
      ['general',['一般企业','General']],['sme',['中小企业','SME']],
      ['graduated_first_three_years',['退出中小企业后前三年','First three years after SME graduation']],
      ['graduated_next_two_years',['随后两年','Following two years']]]},
    check('n_article60_2_1_1_company','属于第60-2(1)(1)条特定企业','Company falls under article 60-2(1)(1)'),
    check('n_annual_standard_schedule_confirmed','已核实完整年度税率适用条件','Full-year schedule applicability verified'),
    check('n_minimum_regime_verified','已核实最低税分类','Minimum-tax classification verified'),
    check('n_eligibility_caps_and_expiry_verified','已核实各项减免资格、限额和到期年度','Relief eligibility, caps and expiry verified'),
    check('n_no_base_changing_incentives','无改变税基的优惠项目','No base-changing incentives'),
    check('n_additions_and_payments_verified','已核实国税加算及缴款凭证和归属','National additions and payment evidence verified'),
    ...([['penalty_tax','国税罚款','National penalty'],['relief_recapture','国税优惠追缴','National relief recapture'],
      ['interim_tax','国税中期缴款','National interim payment'],['occasional_assessment_tax','国税临时评税缴款','National occasional assessment payment'],
      ['withheld_tax','国税扣缴税款','National withholding']] as const).map(([key,zh,en])=>field('n_'+key,zh,en)),
    {...field('relief_count','国税减免明细条数（无则填0）','Number of national relief entries (0 if none)'),integer:true,max:1000},
  ];
  for(let i=0;i<count(values.relief_count,0);i++) {
    const p=`r${i}_`, zh=`减免 ${i+1}：`, en=`Relief ${i+1}: `;
    fields.push({...field(p+'identifier',zh+'名称／凭证编号',en+'name or reference'),text:true},
      field(p+'value',zh+'核定金额',en+'verified amount'),
      {key:p+'category',label:[zh+'法定类别',en+'statutory category'],options:[
        ['reduction',['税额减免','Tax reduction']],['noncarry_credit',['不可结转抵免','Non-carrying credit']],
        ['carry_credit',['可结转抵免','Carrying credit']],['article58_3_credit',['第58-3条抵免','Article 58-3 credit']]]},
      {...field(p+'origin_year',zh+'发生年度',en+'origin year'),integer:true,min:1900,max:2026},
      check(p+'minimum_tax_subject',zh+'受最低税限制',en+'subject to minimum tax'));
  }
  fields.push({...field('filing_count','地方申报单位数量','Number of local filing authorities'),integer:true,min:1,max:1000},
    {...field('head_office','总部所属申报单位名称','Head-office filing authority name'),text:true},
    field('l_total_withheld','地方税扣缴总额','Total local withholding'),
    check('l_initial_return_and_filing_groups_verified','已核实初次申报、城市归并和最终分摊比例','Initial return, city grouping and final ratios verified'),
    check('l_relief_caps_rate_adjustments_and_payments_verified','已核实地方减免限额、税率调整及缴款','Local relief caps, rate adjustments and payments verified'));
  for(let i=0;i<count(values.filing_count,1);i++) {
    const p=`f${i}_`, zh=`地方 ${i+1}：`, en=`Local ${i+1}: `;
    fields.push({...field(p+'name',zh+'申报单位名称',en+'filing authority name'),text:true},
      {...field(p+'ratio',zh+'核定最终分摊比例（0至1，最多8位小数）',en+'verified final ratio (0–1, up to 8 decimals)'),text:true},
      ...localAmounts.map(([key,a,b])=>field(p+key,zh+a,en+b)));
  }
  fields.push(check('ordinary_domestic_scope_confirmed','已核实境内普通企业，无农村特别税、土地转让税、留存所得特别税及其他单独税负；非更正申报或分期缴纳','Ordinary domestic company verified; no rural-special, land-transfer, retained-income or other separate taxes, amended return or installments'));
  return {id:'kr_company_ordinary_2026',label:['韩国企业国税及地方税（2026）','Korea company national and local tax (2026)'],
    notice:['适用于2026完整历年境内普通居民企业。国税税基须与已保存收入、扣除及可抵扣亏损一致；地方税税基须独立核定。减免须按法定类别逐项录入。地方申报单位须先完成城市归并，录入经核定的最终比例（合计1），总部名称须与其中一项一致。金额无则明确填0。分别列示各机关应缴和应退，不自动互抵。尚不含境外所得、特殊税负、更正申报或分期缴纳。',
      'For ordinary domestic resident companies for calendar 2026. Reconcile the national base to saved income, deductions and eligible losses; establish the local base independently. Enter each relief by statutory category. Establish city filing groups and verified final ratios totaling 1; the head-office name must match one group. Enter 0 explicitly for absent amounts. Payments and refunds remain separate by authority. Excludes foreign income, special taxes, amended returns and installments.'],fields};
}

export function koreaBasis(flat:Record<string,unknown>):Record<string,unknown> {
  const national:Record<string,unknown>={installment:false}, local:Record<string,unknown>={installment:false};
  for(const [key,value] of Object.entries(flat)) {
    if(key.startsWith('n_'))national[key.slice(2)]=value;
    if(key.startsWith('l_'))local[key.slice(2)]=value;
  }
  national.reliefs=Array.from({length:Number(flat.relief_count)},(_,i)=>Object.fromEntries(
    ['identifier','value','category','origin_year','minimum_tax_subject'].map(key=>[key,flat[`r${i}_${key}`]])));
  const ratios:Record<string,unknown>=Object.create(null), adjustments:Record<string,unknown>=Object.create(null);
  for(let i=0;i<Number(flat.filing_count);i++) {
    const name=String(flat[`f${i}_name`]).trim();
    if(!name || Object.hasOwn(ratios,name))throw new Error('Local filing names must be nonempty and unique.');
    ratios[name]=flat[`f${i}_ratio`];
    adjustments[name]=Object.fromEntries(localAmounts.map(([key])=>[key,flat[`f${i}_${key}`]]));
  }
  local.filing_ratios=ratios;local.adjustments=adjustments;local.head_office=String(flat.head_office).trim();
  return {...Object.fromEntries(['policy','basis_confirmed','basis_explanation','national_taxable_base',
    'local_taxable_base','ordinary_domestic_scope_confirmed'].map(key=>[key,flat[key]])),national_inputs:national,local_inputs:local};
}
