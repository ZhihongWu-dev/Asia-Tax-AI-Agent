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
  {name:'Singapore corporate partial exemption',country:'sg',subject:'company',category:'business',start:'2025-01-01',end:'2025-12-31',gross:'100000',policy:'sg_company_ya2026',
    money:[['Normal-rate chargeable income','100000'],['Allowed tax set-off','0']],choices:[['Ordinary regime and exclusions checked','true'],['Exemption scheme','partial'],['Eligible for start-up exemption','false'],['Eligible for this YA cash grant','false']],
    resultLabel:'Tax after relief',expected:'4037.5'},
  ...(['company','individual'] as const).map(subject=>({name:`Hong Kong ${subject} profits`,country:'hk',subject,category:'business',start:'2025-04-01',end:'2026-03-31',gross:'1000000',policy:'hk_profits_2025_26',
    money:[['Established assessable profits','1000000'],['Prepaid final tax for this assessment','0']] as [string,string][],
    choices:[['Business form',subject==='company'?'corporation':'sole_proprietor'],['Eligible for two-tier rates','true'],['Ordinary regime and exclusions checked','true']] as [string,string][],
    resultLabel:'Tax for this assessment',expected:subject==='company'?'79500':'72000'})),
  {name:'Hong Kong salaries final prepayment',country:'hk',subject:'individual',category:'employment',start:'2025-04-01',end:'2026-03-31',gross:'380000',policy:'hk_salaries_2025_26',
    money:[['Net income before allowances','380000'],['Allowed allowances','132000'],['Prepaid final tax for this assessment','10000']],
    choices:[['Ordinary separate salaries assessment checked','true']],resultLabel:'Balance due (negative means overpaid)',expected:'11160'},
  ...(['company','individual'] as const).map(subject=>({name:`UAE ${subject} ordinary business`,country:'ae',subject,category:'business',start:'2026-01-01',end:'2026-12-31',gross:subject==='company'?'1000000':'3600000',policy:'ae_ordinary_2026',
    money:[['Established taxable income',subject==='company'?'1000000':'1800000'],['Allowed foreign tax credit by source','0'],['Prepaid tax for this period','0'],
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
  await calc.getByRole('combobox',{name:'Applicable regime',exact:true}).selectOption(s.policy);
  for(const [name,value] of s.money)await calc.getByLabel(name,{exact:true}).fill(value);
  for(const [name,value] of s.choices)await calc.getByRole('combobox',{name,exact:true}).selectOption(value);
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Verified applicable year, ordinary regime, tax basis, deductions and period payment evidence.');
  await calc.getByRole('checkbox').check();await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  const amount=report.locator('dl > div').filter({has:page.locator('dt',{hasText:s.resultLabel})}).locator('dd');
  const trailingZeros=s.expected.includes('.')?'0*':'(?:\\.0+)?';
  const expectedAmount=new RegExp(`^${s.expected.replace('.','\\.')}${trailingZeros}$`);
  await expect(amount).toHaveText(expectedAmount);
  await expect(report.getByRole('link').first()).toHaveAttribute('href',/^https:\/\//);
  await open(page);
  await expect(amount).toHaveText(expectedAmount);
});
