import type { BasisField, IncomePolicy } from './income-assessment';
const field=(key:string,zh:string,en:string):BasisField=>({key,label:[zh,en]});
const check=(key:string,zh:string,en:string):BasisField=>({...field(key,zh,en),boolean:true});
export function koreaSalaryPolicy(values:Record<string,string>):IncomePolicy {
  const fields:BasisField[]=[check('female_taxpayer','纳税人为女性','Taxpayer is female'),
    check('has_spouse','法定判断日有配偶','Has spouse at statutory assessment date'),
    check('household_head','纳税人为户主','Taxpayer is household head'),
    field('public_pension_paid','核定公共养老金实缴金额','Verified public pension paid'),
    {...field('person_count','人员数量（包括本人）','Number of people including taxpayer'),integer:true,min:1,max:1000}];
  const count=/^\d+$/.test(values.person_count||'')?Math.min(1000,Number(values.person_count)):1;
  for(let i=0;i<count;i++) {
    const p=`person_${i}_`,zh=`人员 ${i+1}：`,en=`Person ${i+1}: `,relation=values[p+'relationship'];
    fields.push({key:p+'relationship',label:[zh+'关系',en+'relationship'],options:[
      ['self',['本人','Taxpayer']],['spouse',['配偶','Spouse']],['ascendant',['直系尊亲属','Ascendant']],
      ['descendant',['直系卑亲属','Descendant']],['adopted_child',['收养子女','Adopted child']],
      ['sibling',['兄弟姐妹','Sibling']],['welfare_recipient',['合资格福利受助人','Eligible welfare recipient']],
      ['foster_child',['寄养子女','Foster child']],['disabled_descendant_spouse',['合资格残疾卑亲属配偶','Eligible disabled descendant spouse']]]},
      check(p+'basic_eligible',zh+'符合基本扣除条件并归属本申报人',en+'basic deduction eligible and allocated to this claimant'),
      check(p+'senior_70_at_statutory_date',zh+'法定判断日已满70岁',en+'age 70 or above at statutory date'),
      check(p+'statutory_disability',zh+'符合税法残疾定义',en+'statutory disability'));
    if(['descendant','adopted_child','foster_child'].includes(relation)) {
      fields.push({...field(p+'birth_date',zh+'出生日期',en+'birth date'),date:true,dateMin:'1800-01-01'});
      if(relation==='descendant')fields.push({key:p+'child_relationship',label:[zh+'子女抵免关系',en+'child-credit relationship'],options:[['child',['子女','Child']],['grandchild',['孙子女','Grandchild']]]});
      if(relation==='adopted_child'||(relation==='descendant'&&values[p+'child_relationship']==='child')) {
        fields.push(check(p+'current_event',zh+'2026年出生或登记收养且申请相应抵免',en+'claim verified 2026 birth or registered adoption credit'),
          {...field(p+'event_order',zh+'核定出生／收养顺序',en+'verified birth/adoption order'),integer:true,min:1,max:1000,showWhen:[p+'current_event','true']});
      }
    }
  }
  fields.push(...([
    ['current_employer_withheld','现任雇主已扣国税','Current employer national withholding'],
    ['former_employer_settled_tax','前任雇主国税结算税额','Former employer settled national tax'],
    ['local_current_employer_withheld','现任雇主已扣地方税','Current employer local withholding'],
    ['local_former_employer_settled_tax','前任雇主地方税结算税额','Former employer settled local tax'],
  ] as const).map(([key,zh,en])=>field(key,zh,en)),
    check('ordinary_salary_and_standard_credit_verified','已核实普通工资、标准抵免选择及排除条件','Ordinary salary, standard-credit election and exclusions verified'),
    check('family_eligibility_and_allocation_verified','已核对家庭收入、扶养、年龄、法定日期和唯一申报人，已提交扣除资料','Family income, support, age, statutory dates, unique claimant and submitted documents verified'),
    check('pension_eligibility_verified','已核实公共养老金扣除资格和缴款凭证','Public pension deduction eligibility and receipts verified'),
    check('decision_and_employer_records_verified','已核对雇主结算凭证，无未反映退款、递延、更正或罚款','Employer receipts reconciled; no unreflected refunds, deferrals, amended settlements or penalties'),
    check('employer_special_collection_verified','已核实雇主年终特别征收，非税务机关通知书征收；不分期','Employer year-end special collection verified; no municipal assessment notice or installments'));
  return {id:'kr_salary_standard_payroll_2026',label:['韩国居民工资年终结算（2026，标准抵免）','Korea resident salary year-end settlement (2026, standard credit)'],
    notice:['保存的收入须为各雇主合计普通境内工资，已排除免税工资和日薪所得。保存的扣除金额仅填核定公共养老金；工资及家庭扣除由系统另算。家庭名单包括且仅包括一个本人；核实收入限额、扶养、死亡／残疾恢复等法定日期和重复申报。子女抵免按出生日期及2026过渡条款判断，2017年出生者不享受过渡优惠。此入口选择标准抵免，不含特别扣除、租金抵免、养老金账户抵免、特殊就业减免、其他所得或优惠；不分期。前任雇主填写结算后的税额，不填退款前累计扣款。',
      'Saved income must aggregate ordinary domestic salary from all employers, excluding exempt and daily-worker pay. Saved deductions contain only verified public pension; salary and family deductions are calculated separately. Include exactly one taxpayer and verify income limits, support, statutory dates including death/disability recovery, and duplicate claims. Child credit uses birth dates and the 2026 transition, excluding the 2017 birth cohort. Standard-credit election only: excludes special deductions, rent or pension-account credits, special employment reductions, other income and concessions; no installments. Former-employer amounts are settled taxes, not cumulative withholding before refunds.'],fields};
}

export function koreaSalaryBasis(flat:Record<string,unknown>):Record<string,unknown> {
  const people:Record<string,unknown>[]=[],children:Record<string,unknown>[]=[];
  for(let i=0;i<Number(flat.person_count);i++) {
    const p=`person_${i}_`,identifier=`person_${i+1}`,relationship=flat[p+'relationship'];
    people.push({identifier,...Object.fromEntries(['relationship','basic_eligible','senior_70_at_statutory_date','statutory_disability'].map(key=>[key,flat[p+key]]))});
    if(['descendant','adopted_child','foster_child'].includes(String(relationship)))children.push({identifier,
      relationship:relationship==='descendant'?flat[p+'child_relationship']:relationship,
      birth_date:flat[p+'birth_date'],basic_deduction_eligible:flat[p+'basic_eligible'],
      current_year_birth_adoption_order:flat[p+'current_event']===true?flat[p+'event_order']:null});
  }
  return {...Object.fromEntries(Object.entries(flat).filter(([key])=>!key.startsWith('person_'))),people,children,installment:false};
}
