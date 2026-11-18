import {test,expect,type Page} from '@playwright/test';

async function open(page:Page) {
  await page.goto('/');
  await expect(page.getByRole('button',{name:/Switch to English|切换为中文/})).toBeVisible();
  const english=page.getByRole('button',{name:'Switch to English'});
  if(await english.isVisible())await english.click();
  await page.getByRole('button',{name:'Open case details',exact:true}).click();
  const form=page.locator('.income-tax-facts');
  if(!await form.getByRole('combobox',{name:'Taxpayer',exact:true}).isVisible())await form.locator('summary').click();
  return form;
}

type Scenario={name:string;country:string;subject:string;category:string;start:string;end:string;
  gross:string;policy:string;deductions?:string;money:[string,string][];choices:[string,string][];resultLabel:string;expected:string};
const scenarios:Scenario[]=[
  {name:'China company reconciled excluded income',country:'cn',subject:'company',category:'business',start:'2026-01-01',end:'2026-12-31',gross:'1000000',policy:'cn_company_2026',deductions:'200000',
    money:[['Established taxable income','650000'],['Established non-taxable income included in total income','50000'],['Established exempt income included in total income','100000'],['Allowed tax credits','0'],['Prepaid tax for this period','10000']],
    choices:[['Normal rate eligibility checked','true']],resultLabel:'Annual liability',expected:'162500'},
  {name:'Singapore employment IRAS PTR carryforward',country:'sg',subject:'individual',category:'employment',start:'2025-01-01',end:'2025-12-31',gross:'80000',policy:'sg_employment_ya2026',deductions:'28000',
    money:[['Date of birth','1990-01-01'],['Allowed employment expenses','0'],['Usable donation deduction after verified multiplier','0'],['Allowed employee CPF relief','16000'],['Other allowed personal reliefs excluding items above','12000'],['Verified available PTR balance','2500'],['Prepaid tax for this period','100']],
    choices:[['Eligible for disability earned income relief','false'],['YA 2026 eligibility, individual limits, allocation and PTR balance verified','true']],
    resultLabel:'PTR carried forward (not refundable)',expected:'1180'},
  {name:'Singapore employment relief cap and donation',country:'sg',subject:'individual',category:'employment',start:'2025-01-01',end:'2025-12-31',gross:'150000',policy:'sg_employment_ya2026',deductions:'100400',
    money:[['Date of birth','1990-01-01'],['Allowed employment expenses','0'],['Usable donation deduction after verified multiplier','10000'],['Allowed employee CPF relief','20400'],['Other allowed personal reliefs excluding items above','70000'],['Verified available PTR balance','0'],['Prepaid tax for this period','3000']],
    choices:[['Eligible for disability earned income relief','false'],['YA 2026 eligibility, individual limits, allocation and PTR balance verified','true']],
    resultLabel:'Annual liability',expected:'1950'},
  {name:'China small-low-profit company at all thresholds',country:'cn',subject:'company',category:'business',start:'2026-01-01',end:'2026-12-31',gross:'4000000',policy:'cn_small_company_2026',deductions:'1000000',
    money:[['Established taxable income','3000000'],['Statutory annual quarterly-average employees','300'],['Statutory annual quarterly-average assets (CNY)','50000000'],['Allowed tax credits','10000'],['Prepaid tax for this period','200000']],
    choices:[['Non-restricted and non-prohibited industry verified','true'],['Statutory averages, residence and preference eligibility verified','true']],
    resultLabel:'Annual liability',expected:'140000'},
  ...(['individual_operator','other_business'] as const).map(kind=>({name:`China business ${kind}`,country:'cn',subject:'individual',category:'business',start:'2026-01-01',end:'2026-12-31',gross:'3000000',policy:'cn_business_2026',deductions:'600000',
    money:[['Established taxable income','2400000'],['Allowed other tax reductions','6000'],['Prepaid tax for this period','500000']] as [string,string][],
    choices:[['Verified business classification',kind],['Annual business aggregation and classification verified','true'],['Deductions, losses and no duplicate claims verified','true']] as [string,string][],
    resultLabel:'Annual liability',expected:kind==='individual_operator'?'453750':'768500'})),
  {name:'China comprehensive individual',country:'cn',subject:'individual',category:'employment',start:'2026-01-01',end:'2026-12-31',gross:'1000000',policy:'cn_comprehensive_2026',
    money:[['Allowed special deductions','0'],['Allowed additional deductions','0'],['Allowed other deductions','0'],['Allowed donations','0'],['Allowed tax reductions','0'],['Prepaid tax for this period','0']],
    choices:[['Domestic resident comprehensive treatment checked','true']],resultLabel:'Annual liability',expected:'243080'},
  {name:'China comprehensive reconciled deductions',country:'cn',subject:'individual',category:'employment',start:'2026-01-01',end:'2026-12-31',gross:'1000000',policy:'cn_comprehensive_2026',deductions:'43000',
    money:[['Allowed special deductions','20000'],['Allowed additional deductions','12000'],['Allowed other deductions','6000'],['Allowed donations','5000'],['Allowed tax reductions','1000'],['Prepaid tax for this period','200000']],
    choices:[['Domestic resident comprehensive treatment checked','true']],resultLabel:'Annual liability',expected:'227030'},
  {name:'Singapore corporate partial exemption',country:'sg',subject:'company',category:'business',start:'2025-01-01',end:'2025-12-31',gross:'1000000',deductions:'900000',policy:'sg_company_ya2026',
    money:[['Normal-rate chargeable income','100000'],['Allowed tax set-off','0']],choices:[['Ordinary regime and exclusions checked','true'],['Exemption scheme','partial'],['Eligible for start-up exemption','false'],['Eligible for this YA cash grant','false']],
    resultLabel:'Tax after relief',expected:'4037.5'},
  ...(['company','individual'] as const).map(subject=>({name:`Hong Kong ${subject} profits`,country:'hk',subject,category:'business',start:'2025-04-01',end:'2026-03-31',gross:'1500000',deductions:'500000',policy:'hk_profits_2025_26',
    money:[['Established net taxable profits after loss relief','1000000'],['Taxable additions not included in saved income','0'],['Established exclusions included in income','0'],['Prepaid final tax for this assessment','0']] as [string,string][],
    choices:[['Business form',subject==='company'?'corporation':'sole_proprietor'],['Eligible for two-tier rates','true'],['Ordinary regime and exclusions checked','true']] as [string,string][],
    resultLabel:'Tax for this assessment',expected:subject==='company'?'79500':'72000'})),
  {name:'Hong Kong property separate assessment',country:'hk',subject:'individual',category:'rental',start:'2025-04-01',end:'2026-03-31',gross:'300000',policy:'hk_property_2025_26',deductions:'30000',
    money:[['Property 1: irrecoverable rent after deposit offset','20000'],['Property 1: rates borne and paid by owner','10000'],['Prepaid final tax for this assessment','35000']],
    choices:[['Sole ownership and separate property assessment verified','true'],['Complete rental consideration and deduction evidence verified','true']],
    resultLabel:'Balance due (negative means overpaid)',expected:'-2600'},
  {name:'Hong Kong salaries final prepayment',country:'hk',subject:'individual',category:'employment',start:'2025-04-01',end:'2026-03-31',gross:'400000',deductions:'20000',policy:'hk_salaries_2025_26',
    money:[['Net income before allowances','380000'],['Allowed allowances','132000'],['Prepaid final tax for this assessment','10000']],
    choices:[['Ordinary separate salaries assessment checked','true']],resultLabel:'Balance due (negative means overpaid)',expected:'11160'},
  ...(['company','individual'] as const).map(subject=>({name:`UAE ${subject} ordinary business`,country:'ae',subject,category:'business',start:'2026-01-01',end:'2026-12-31',gross:subject==='company'?'1000000':'3600000',policy:'ae_ordinary_2026',
    money:[['Established taxable income',subject==='company'?'1000000':'1800000'],['Taxable additions not included in saved income','0'],['Established exempt income included in business income','0'],['Allowed foreign tax credit by source','0'],['Prepaid tax for this period','0'],
      ...(subject==='individual'?[['Total in-scope personal business turnover','3600000']]:[])] as [string,string][],
    choices:[['Ordinary regime and exclusions checked','true'],['Confirmed no small-business or other relief election','true'],
      ...(subject==='individual'?[['Statutory business and excluded-income classification checked','true']]:[])] as [string,string][],
    resultLabel:'Tax for this assessment',expected:subject==='company'?'56250':'128250'})),
];

for(const s of scenarios)test(`${s.name} saves and reopens a sourced result`,async({page})=>{
  const form=await open(page);
  for(const [name,value] of [['Taxpayer',s.subject],['Filing jurisdiction',s.country],['Tax residency','resident'],['Income category',s.category],['Income source jurisdiction',s.country]])
    await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start',s.start],['Period end',s.end],['Gross income',s.gross],['Income description','Verified ordinary domestic income'],['Claimed deductions (blank if unknown)',s.deductions??(s.country==='ae'&&s.subject==='individual'?'1800000':'0')],['Carried losses (blank if unknown)','0']])
    await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('checkbox').check();await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  if(s.country==='hk' && s.subject==='individual') {
    const wrong=s.category==='employment'?'Hong Kong profits tax (2025/26)':'Hong Kong salaries tax (2025/26)';
    await expect(calc.getByRole('option',{name:wrong,exact:true})).toHaveCount(0);
  }
  await calc.getByRole('combobox',{name:'Applicable regime',exact:true}).selectOption(s.policy);
  if(['cn_company_2026','cn_small_company_2026'].includes(s.policy)) {
    await calc.getByLabel('Established non-taxable income included in total income',{exact:true}).fill('0');
    await calc.getByLabel('Established exempt income included in total income',{exact:true}).fill('0');
  }
  if(s.policy==='hk_salaries_2025_26') {
    for(const label of ['Machinery balancing charge','Established employment expenses','Established machinery allowances','Established self-education deduction','Established Part 4A deductions'])
      await calc.getByLabel(label,{exact:true}).fill(label==='Established Part 4A deductions'?'20000':'0');
    await calc.getByRole('combobox',{name:'Deduction limits and salary-loss eligibility verified',exact:true}).selectOption('true');
  }
  for(const [name,value] of s.money)await calc.getByLabel(name,{exact:true}).fill(value);
  for(const [name,value] of s.choices)await calc.getByRole('combobox',{name,exact:true}).selectOption(value);
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Verified applicable year, ordinary regime, tax basis, deductions and period payment evidence.');
  await calc.getByRole('checkbox').check();await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  const amount=report.locator('dl > div').filter({has:page.locator('dt',{hasText:s.resultLabel})}).locator('dd');
  const trailingZeros=s.expected.includes('.')?'0*':'(?:\\.0+)?';
  const expectedAmount=new RegExp(`^${s.expected.replace('.','\\.')}${trailingZeros}$`);
  await expect(amount).toHaveText(expectedAmount);
  if(s.policy==='hk_salaries_2025_26') await expect(report.getByRole('region',{name:'Hong Kong salaries reconciliation'})).toContainText('20000');
  if(s.policy==='ae_ordinary_2026') await expect(report.getByRole('region',{name:'UAE corporate tax basis reconciliation'})).toBeVisible();
  if(s.policy==='hk_profits_2025_26') await expect(report.getByRole('region',{name:'Hong Kong profits basis reconciliation'})).toContainText('1000000');
  if(s.policy==='sg_company_ya2026') await expect(report.getByRole('region',{name:'Singapore pre-exemption basis reconciliation'})).toContainText('900000');
  if(s.policy==='hk_property_2025_26') {
    await expect(report.getByRole('region',{name:'Per-property results'})).toContainText('216000');
    await expect(calc.getByRole('option',{name:'Hong Kong profits tax (2025/26)',exact:true})).toHaveCount(0);
  }
  await expect(report.getByRole('link').first()).toHaveAttribute('href',s.policy==='cn_company_2026'
    ?'http://www.npc.gov.cn/zgrdw/npc/xinwen/2019-01/07/content_2070260.htm':/^https:\/\//);
  if(['cn_company_2026','cn_small_company_2026'].includes(s.policy))
    await expect(report.getByRole('region',{name:'Company basis reconciliation',exact:true})).toBeVisible();
  await open(page);
  await expect(amount).toHaveText(expectedAmount);
});
