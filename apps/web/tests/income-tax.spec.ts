import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

for(const route of [
  {country:'id',category:'dividend',gross:'1000',tax:'50',credit:'150',underlying:false},
  {country:'sg',category:'royalty',gross:'1000',tax:'50',credit:'100',underlying:false},
  {country:'hk',category:'dividend',gross:'80',tax:'0',credit:'20',underlying:true},
  {country:'sg',category:'dividend',gross:'80',tax:'0',credit:'20',underlying:true},
]) test(`Vietnam saved credit history ${route.country} ${route.category} survives reload and marks changed income`,async({page})=>{
  test.setTimeout(60000);
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','company'],['Filing jurisdiction','vn'],['Tax residency','resident']])await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Claimed deductions (blank if unknown)','0'],['Carried losses (blank if unknown)','0']])await form.getByLabel(name,{exact:true}).fill(value);
  const income=form.getByRole('group',{name:'Income 1',exact:true});
  await income.getByRole('combobox',{name:'Income category',exact:true}).selectOption(route.category);
  await income.getByRole('combobox',{name:'Income source jurisdiction',exact:true}).selectOption(route.country);
  for(const [name,value] of [['Gross income',route.gross],['Foreign tax paid (blank if unknown)',route.tax],['Income description','Reviewed foreign income']])await income.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('checkbox').check();
  const saved=page.waitForResponse(r=>r.url().endsWith('/income-tax')&&r.request().method()==='PUT');
  await form.getByRole('button',{name:'Save income-tax details'}).click();
  const response=await saved, path=new URL(response.url()).pathname;
  const headers={'X-AsiaTax-Request':'1'};
  const creditForm=page.getByRole('region',{name:'Vietnam foreign credit workpaper',exact:true});
  await creditForm.getByLabel('Include in this workpaper',{exact:true}).check();
  await creditForm.getByLabel('Vietnam tax limit for this income',{exact:true}).fill('200');
  await creditForm.getByLabel('Treaty entitlement and limit explanation (20+ characters)',{exact:true}).fill('Verified treaty entitlement and same-income Vietnam tax basis.');
  const verified=creditForm.getByLabel('Treaty eligibility and same-income tax basis verified',{exact:true});
  await verified.check();
  await creditForm.getByLabel('Vietnam tax limit for this income',{exact:true}).fill('199');
  await expect(verified).not.toBeChecked();
  if(route.country==='sg'&&!route.underlying)await creditForm.getByLabel('Eligible Singapore tax paid',{exact:true}).fill('50');
  if(route.underlying){
    for(const [name,value] of [['Qualifying holding percentage','10'],['Distributing profit pool after tax','800'],['Corporate tax paid on the profit pool','200']])await creditForm.getByLabel(name,{exact:true}).fill(value);
    const pool=creditForm.getByLabel('Corporate recipient and homogeneous profit pool verified',{exact:true});
    await pool.check();
    await creditForm.getByLabel('Vietnam tax limit for this income',{exact:true}).fill('200');
    await expect(pool).not.toBeChecked();
    await pool.check();
  }
  await verified.check();
  await creditForm.getByLabel(route.underlying?'Indirect-credit documents':'Tax-sparing documents',{exact:true}).check();
  const missingKind=route.underlying?'Ownership legal evidence':'Foreign income tax return';
  const missingReason='Foreign authority confirmation requested; evidence is still pending.';
  await creditForm.getByLabel(`${missingKind}: missing-document explanation`,{exact:true}).fill(missingReason);
  await creditForm.getByLabel('Treaty credit application',{exact:true}).fill('case-evidence/02-HTQT');
  await creditForm.getByLabel('Treaty credit application: required form and content checked',{exact:true}).check();
  await creditForm.getByLabel('Treaty credit application',{exact:true}).fill('case-evidence/02-HTQT-revised');
  await expect(creditForm.getByLabel('Treaty credit application: required form and content checked',{exact:true})).not.toBeChecked();
  await creditForm.getByLabel('Treaty credit application: required form and content checked',{exact:true}).check();
  const posted=page.waitForResponse(r=>r.url().endsWith('/credit-workpapers')&&r.request().method()==='POST');
  await creditForm.getByRole('button',{name:'Calculate and save credit workpaper',exact:true}).click();
  const created=await posted;
  expect(created.status()).toBe(200);
  await openIncome(page);
  const history=page.getByRole('region',{name:'Credit workpaper history',exact:true});
  await expect(history.getByText('Matches current saved income',{exact:true})).toBeVisible();
  await history.getByRole('button',{name:/View workpaper/}).click();
  await expect(history.getByText(new RegExp(`^Reviewed credit subtotal: ${route.credit}(?:\\.0+)? VND$`))).toBeVisible();
  await expect(history.getByText('Documents missing or unchecked',{exact:true})).toBeVisible();
  await expect(history.getByRole('region',{name:'Credit workpaper details'})).toContainText(missingReason);
  const current=await (await page.request.get(path)).json();
  current.income_tax.incomes[0].gross_amount='2000';
  expect((await page.request.put(path,{headers,data:{revision:current.revision,request_id:crypto.randomUUID(),inputs:current.income_tax}})).status()).toBe(200);
  await openIncome(page);
  await expect(history.getByText('Income facts changed: historical workpaper only',{exact:true})).toBeVisible();
  await history.getByRole('button',{name:/View workpaper/}).click();
  await expect(history.getByRole('region',{name:'Credit workpaper details'})).toContainText(missingReason);
  await expect(history.getByText(new RegExp(`^Reviewed credit subtotal: ${route.credit}(?:\\.0+)? VND$`))).toBeVisible();
});

test('Thailand multiple countries and pools reconcile split remittances',async({page})=>{
  test.setTimeout(60000);
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','individual'],['Filing jurisdiction','th'],['Tax residency','resident']])await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Claimed deductions (blank if unknown)','160000'],['Carried losses (blank if unknown)','0']])await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('button',{name:'Add income',exact:true}).click();
  for(const [n,country,category,gross,tax] of [[0,'vn','employment','600000','120000'],[1,'cn','dividend','400000','40000']] as const) {
    const row=form.getByRole('group',{name:`Income ${n+1}`,exact:true});
    await row.getByRole('combobox',{name:'Income category',exact:true}).selectOption(category);
    await row.getByRole('combobox',{name:'Income source jurisdiction',exact:true}).selectOption(country);
    for(const [name,value] of [['Gross income',gross],['Foreign tax paid (blank if unknown)',tax],['Income description','Original pool tax and current-year traced receipts']])await row.getByLabel(name,{exact:true}).fill(value);
  }
  await form.getByRole('checkbox').check();await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calc.getByLabel('Applicable regime').selectOption('th_foreign_income_2026');
  for(const [name,value] of [['Verified net taxable income after excluded receipts and saved deductions','840000'],['Thai period prepayments (exclude foreign tax)','0'],['Income 1: original earnings pool count','2'],['Income 2: original earnings pool count','1']])await calc.getByLabel(name,{exact:true}).fill(value);
  for(const [n,j,id,original,tax,receipts] of [[1,1,'VN-A','300000','60000',['150000','150000']],[1,2,'VN-B','300000','60000',['300000']],[2,1,'CN-A','800000','40000',['400000']]] as const) {
    const prefix=`Income ${n}, pool ${j}: `;
    for(const [name,value] of [['unique evidence / earnings pool ID',id],['total original foreign earnings',original],['foreign income tax paid on original earnings',tax],['tax eligible under verified treaty taxing rights and source caps',tax],['income remitted in prior years','0'],['treaty eligibility, tax evidence and consistent THB valuation basis (20+ characters)','Verified distinct source tax certificate, treaty rights and consistent THB valuation'],['current-year remittance count',String(receipts.length)]])await calc.getByLabel(prefix+name,{exact:true}).fill(value);
    for(let k=0;k<receipts.length;k++)for(const [name,value] of [['income amount (exclude capital)',receipts[k]],['original earnings date','2024-06-01'],['remittance date',k===0?'2026-06-01':'2026-07-01'],['days in Thailand in the earnings year','180']])await calc.getByLabel(prefix+`remittance ${k+1}: `+name,{exact:true}).fill(value);
  }
  for(const name of ['Ordinary annual treatment and special-regime exclusions verified','Section40 income types, expenses and deductions verified','Disjoint pools, remittance tracing, FX and treaty credit eligibility verified','Saved foreign tax is the original pool tax before remittance apportionment'])await calc.getByRole('combobox',{name,exact:true}).selectOption('true');
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Verified all country totals, distinct earnings pools, prior remittances and tax evidence.');
  await calc.getByLabel('Income 1, pool 2: unique evidence / earnings pool ID',{exact:true}).fill('VN-A');
  await calc.getByRole('checkbox').check();await calc.getByRole('button',{name:'Calculate and save result'}).click();
  await expect(calc.getByRole('alert')).toContainText('unique pool IDs');
  await calc.getByLabel('Income 1, pool 2: unique evidence / earnings pool ID',{exact:true}).fill('VN-B');
  await calc.getByRole('checkbox').check();
  const response=page.waitForResponse(r=>r.url().includes('/income-tax/runs')&&r.request().method()==='POST');
  await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const saved=await response;expect(saved.status()).toBe(200);
  const payload=await saved.json();expect(payload.basis.pools).toHaveLength(3);expect(payload.basis.pools[0].remittances).toHaveLength(2);
  const report=page.getByRole('article',{name:'Saved calculation result'});
  await expect(report.locator('dl > div').filter({hasText:/^Allowed tax credits/}).locator('dd')).toHaveText(/^69800(?:\.0+)?$/);
  await expect(report.locator('dl > div').filter({hasText:/^Tax for this assessment/}).locator('dd')).toHaveText(/^13200(?:\.0+)?$/);
  await expect(report.getByRole('region',{name:'Source country VN',exact:true})).toContainText('49800');
  await expect(report.getByRole('region',{name:'Source country CN',exact:true})).toContainText('20000');
  await openIncome(page);
  await expect(page.getByRole('region',{name:'Income pool VN-B',exact:true})).toBeVisible();
});

for(const earned of ['2024-06-01','2023-06-01'])test(`Thailand foreign remittance saves and reopens ${earned}`,async({page})=>{
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','individual'],['Filing jurisdiction','th'],['Tax residency','resident'],['Income category','employment'],['Income source jurisdiction','vn']])await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Gross income','500000'],['Foreign tax paid (blank if unknown)','150000'],['Income description','Remitted salary, original income pool tax'],['Claimed deductions (blank if unknown)','160000'],['Carried losses (blank if unknown)','0']])await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('checkbox').check();await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calc.getByLabel('Applicable regime').selectOption('th_foreign_income_2026');
  for(const [name,value] of [
    ['Verified net taxable income after excluded receipts and saved deductions',earned.startsWith('2024')?'340000':'0'],
    ['Thai period prepayments (exclude foreign tax)','0'],['Income 1: original earnings pool count','1'],
    ['Income 1, pool 1: unique evidence / earnings pool ID','VN-salary-1'],
    ['Income 1, pool 1: total original foreign earnings','500000'],
    ['Income 1, pool 1: foreign income tax paid on original earnings','150000'],
    ['Income 1, pool 1: tax eligible under verified treaty taxing rights and source caps','150000'],
    ['Income 1, pool 1: income remitted in prior years','0'],
    ['Income 1, pool 1: treaty eligibility, tax evidence and consistent THB valuation basis (20+ characters)','Verified salary tax certificate and treaty entitlement with consistent THB conversion'],
    ['Income 1, pool 1: current-year remittance count','1'],
    ['Income 1, pool 1: remittance 1: income amount (exclude capital)','500000'],
    ['Income 1, pool 1: remittance 1: original earnings date',earned],
    ['Income 1, pool 1: remittance 1: remittance date','2026-06-01'],
    ['Income 1, pool 1: remittance 1: days in Thailand in the earnings year','180']])await calc.getByLabel(name,{exact:true}).fill(value);
  for(const name of ['Ordinary annual treatment and special-regime exclusions verified','Section40 income types, expenses and deductions verified','Disjoint pools, remittance tracing, FX and treaty credit eligibility verified','Saved foreign tax is the original pool tax before remittance apportionment'])await calc.getByRole('combobox',{name,exact:true}).selectOption('true');
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Confirmed remittance year, earnings-year residence, treaty evidence and verified deductions.');
  await calc.getByRole('checkbox').check();await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  await expect(report.locator('dl > div').filter({hasText:/^Tax before reductions and credits/}).locator('dd')).toHaveText(earned.startsWith('2024')?/^11500(?:\.0+)?$/:/^0(?:\.0+)?$/);
  await expect(report.locator('dl > div').filter({hasText:/^Allowed tax credits/}).locator('dd')).toHaveText(earned.startsWith('2024')?/^11500(?:\.0+)?$/:/^0(?:\.0+)?$/);
  await expect(report.getByRole('link',{name:'Revenue Department foreign tax credit manual (TH), November 2025',exact:true})).toHaveAttribute('href','https://www.rd.go.th/fileadmin/user_upload/porphor/GuideTaxFromAbroad_TH.pdf');
  const breakdown=report.getByRole('region',{name:'Thai foreign income reconciliation',exact:true});
  await expect(breakdown.getByRole('region',{name:'Source country VN',exact:true})).toBeVisible();
  await expect(breakdown.getByRole('region',{name:'Income pool VN-salary-1',exact:true})).toContainText('Verified salary tax certificate');
  await expect(breakdown.locator('dl > div').filter({hasText:/^Remitted income excluded this year/}).locator('dd')).toHaveText(earned.startsWith('2024')?'0':'500000');
  await openIncome(page);await expect(page.getByRole('article',{name:'Saved calculation result'})).toBeVisible();
});

for(const residency of ['resident','nonresident'])test(`Malaysia dividends save and reopen ${residency}`,async({page})=>{
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','individual'],['Filing jurisdiction','my'],['Tax residency',residency],['Income category','dividend'],['Income source jurisdiction','my']])await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Gross income','150000'],['Income description','Annual domestic dividend income'],['Claimed deductions (blank if unknown)',residency==='resident'?'9000':'0'],['Carried losses (blank if unknown)','0']])await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('checkbox').check();await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calc.getByLabel('Applicable regime').selectOption('my_dividend_2026');
  for(const [name,value] of [['Dividend statutory income before annual MYR100,000 threshold','150000'],['Other ordinary statutory income','0'],['Chargeable income after threshold and reliefs',residency==='resident'?'41000':'50000'],['Allowed tax rebates','0'],['Allowed tax credits','0'],['Prepaid tax for this period',residency==='resident'?'1000':'0']])await calc.getByLabel(name,{exact:true}).fill(value);
  for(const name of ['Separate domestic assessment and ordinary-income exclusions verified','All annual dividends, expenses and exemptions verified','Statutory income, deduction and relief eligibility, and tax bases verified','Rebate eligibility, credit limits and prepayments verified'])await calc.getByRole('combobox',{name,exact:true}).selectOption('true');
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Verified all annual domestic dividends and separate assessment deductions and payments.');
  await calc.getByRole('checkbox').check();await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  await expect(report.locator('dl > div').filter({hasText:/^Dividend tax/}).locator('dd')).toHaveText(residency==='resident'?/^820(?:\.0+)?$/:/^1000(?:\.0+)?$/);
  await expect(report.locator('dl > div').filter({hasText:'Annual dividend threshold used'}).locator('dd')).toHaveText(/^100000(?:\.0+)?$/);
  await expect(report.getByRole('link').filter({hasText:/my.pua148/})).toHaveAttribute('href',/parlimen.gov.my/);
  await openIncome(page);await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText('my-dividend-ya2026');
});

for(const election of ['aggregate','final_withholding'])test(`Thailand dividends save and reopen ${election}`,async({page})=>{
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','individual'],['Filing jurisdiction','th'],['Tax residency','resident'],['Income category','dividend'],['Income source jurisdiction','th']])await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Gross income','80000'],['Income description','Two certified dividend tranches'],['Claimed deductions (blank if unknown)','60000'],['Carried losses (blank if unknown)','0']])await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('checkbox').check();await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calc.getByLabel('Applicable regime').selectOption('th_dividend_2026');
  await calc.getByRole('combobox',{name:'Dividend election',exact:true}).selectOption(election);
  await calc.getByLabel('Verified expenses and allowances (must match saved amount)',{exact:true}).fill('60000');
  await calc.getByLabel('Other income prepayments (exclude dividend withholding)',{exact:true}).fill('0');
  await calc.getByLabel('Income 1: certificate tranche count',{exact:true}).fill('2');
  for(const n of [1,2]) {
    await calc.getByLabel(`Income 1, tranche ${n}: dividend before withholding`,{exact:true}).fill('40000');
    await calc.getByRole('combobox',{name:`Income 1, tranche ${n}: eligible for dividend credit`,exact:true}).selectOption('true');
    await calc.getByLabel(`Income 1, tranche ${n}: certified corporate rate (%)`,{exact:true}).fill('20');
    await calc.getByLabel(`Income 1, tranche ${n}: dividend tax withheld`,{exact:true}).fill('4000');
  }
  await calc.getByRole('combobox',{name:'Income 1, tranche 2: eligible for dividend credit',exact:true}).selectOption('false');
  await expect(calc.getByLabel('Income 1, tranche 2: certified corporate rate (%)',{exact:true})).toHaveCount(0);
  for(const name of ['All certificates, tranche corporate rates and withholding verified','Recipient credit eligibility verified','All taxable domestic dividends and creditable payers included; exempt, foreign and special dividends excluded','Other income and deductions verified under ordinary annual treatment'])await calc.getByRole('combobox',{name:name,exact:true}).selectOption('true');
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Verified all domestic dividend payers, certificates, election and allowances.');
  await calc.getByRole('checkbox').check();await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  await expect(report.locator('dl > div').filter({hasText:'Calculated refund due'}).locator('dd')).toHaveText(election==='aggregate'?/^18000(?:\.0+)?$/:/^0(?:\.0+)?$/);
  await expect(report.locator('dl > div').filter({hasText:'Separate final dividend tax'}).locator('dd')).toHaveText(election==='aggregate'?/^0(?:\.0+)?$/:/^8000(?:\.0+)?$/);
  await openIncome(page);await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText('th-dividend-annual-2026');
});

for(const birth of ['2016-12-31','2017-01-01'])test(`Korea salary uses child transition ${birth} and saves separate balances`,async({page})=>{
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','individual'],['Filing jurisdiction','kr'],['Tax residency','resident'],['Income category','employment'],['Income source jurisdiction','kr']])
    await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Gross income','50000009'],['Income description','Ordinary domestic annual salary'],['Claimed deductions (blank if unknown)','0'],['Carried losses (blank if unknown)','0']])
    await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('checkbox').check();await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calc.getByLabel('Applicable regime').selectOption('kr_salary_standard_payroll_2026');
  await calc.getByLabel('Number of people including taxpayer',{exact:true}).fill('2');
  await calc.getByRole('combobox',{name:'Person 1: relationship',exact:true}).selectOption('self');
  await calc.getByRole('combobox',{name:'Person 2: relationship',exact:true}).selectOption('descendant');
  await calc.getByRole('combobox',{name:'Person 2: child-credit relationship',exact:true}).selectOption('child');
  await calc.getByLabel('Person 2: birth date',{exact:true}).fill(birth);
  for(const name of ['Taxpayer is female','Has spouse at statutory assessment date','Taxpayer is household head','Person 2: claim verified 2026 birth or registered adoption credit'])
    await calc.getByRole('combobox',{name,exact:true}).selectOption('false');
  for(const n of [1,2]) {
    await calc.getByRole('combobox',{name:`Person ${n}: basic deduction eligible and allocated to this claimant`,exact:true}).selectOption('true');
    for(const label of ['age 70 or above at statutory date','statutory disability'])
      await calc.getByRole('combobox',{name:`Person ${n}: ${label}`,exact:true}).selectOption('false');
  }
  for(const [name,value] of [['Verified public pension paid','0'],['Current employer national withholding','3400000'],
    ['Former employer settled national tax','0'],['Current employer local withholding','300000'],['Former employer settled local tax','0']])
    await calc.getByLabel(name,{exact:true}).fill(value);
  for(const name of ['Ordinary salary, standard-credit election and exclusions verified',
    'Family income, support, age, statutory dates, unique claimant and submitted documents verified',
    'Public pension deduction eligibility and receipts verified',
    'Employer receipts reconciled; no unreflected refunds, deferrals, amended settlements or penalties',
    'Employer year-end special collection verified; no municipal assessment notice or installments'])
    await calc.getByRole('combobox',{name,exact:true}).selectOption('true');
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Verified domestic salary, statutory family eligibility, birth evidence, standard credit and employer receipts.');
  await calc.getByRole('checkbox').check();await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  const result=report.getByRole('region',{name:'Korean salary settlement',exact:true});
  await expect(result.locator('dl > div').filter({hasText:'National decision tax'}).locator('dd')).toHaveText(birth.startsWith('2016')?'2762501':'3012501');
  await expect(result.locator('dl > div').filter({hasText:'Regular child credit reference'}).locator('dd')).toHaveText(birth.startsWith('2016')?'250000':'0');
  if(birth.startsWith('2017'))await expect(result).toContainText('2017 birth-cohort exception');
  await result.getByRole('region',{name:'Local tax',exact:true}).scrollIntoViewIfNeeded();
  await page.screenshot({path:`test-results/income-tax-korea-salary-${birth}.png`,fullPage:true});
  await openIncome(page);
  await expect(page.getByRole('region',{name:'Korean salary settlement',exact:true})).toContainText(birth.startsWith('2016')?'637490':'387490');
});

for(const withRelief of [false,true])test(`Korea company preserves separate authority refunds and dynamic filing rows relief=${withRelief}`,async({page})=>{
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','company'],['Filing jurisdiction','kr'],['Tax residency','resident'],['Income category','business'],['Income source jurisdiction','kr']])
    await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Gross income','100000000'],['Income description','Annual ordinary domestic business income'],['Claimed deductions (blank if unknown)','0'],['Carried losses (blank if unknown)','0']])
    await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('checkbox').check();await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calc.getByLabel('Applicable regime').selectOption('kr_company_ordinary_2026');
  await calc.getByLabel('Number of national relief entries (0 if none)',{exact:true}).fill('1');
  await calc.getByLabel('Relief 1: name or reference',{exact:true}).fill('Unused stale entry');
  await calc.getByLabel('Number of national relief entries (0 if none)',{exact:true}).fill('0');
  await expect(calc.getByLabel('Relief 1: name or reference',{exact:true})).toHaveCount(0);
  if(withRelief) {
    await calc.getByLabel('Number of national relief entries (0 if none)',{exact:true}).fill('1');
    await calc.getByLabel('Relief 1: name or reference',{exact:true}).fill('Verified exempt credit');
    await calc.getByLabel('Relief 1: verified amount',{exact:true}).fill('1000000');
    await calc.getByLabel('Relief 1: origin year',{exact:true}).fill('2026');
    await calc.getByRole('combobox',{name:'Relief 1: statutory category',exact:true}).selectOption('noncarry_credit');
    await calc.getByRole('combobox',{name:'Relief 1: subject to minimum tax',exact:true}).selectOption('false');
  }
  await calc.getByLabel('Number of local filing authorities',{exact:true}).fill('2');
  for(const [name,value] of [['Established national taxable base','100000000'],['Independently established local taxable base','200000000'],
    ['National penalty','0'],['National relief recapture','0'],['National interim payment','11000000'],['National occasional assessment payment','0'],['National withholding','0'],
    ['Head-office filing authority name','HQ'],['Total local withholding','0'],['Local 1: filing authority name','HQ'],['Local 2: filing authority name','HQ'],
    ['Local 1: verified final ratio (0–1, up to 8 decimals)','0.6'],['Local 2: verified final ratio (0–1, up to 8 decimals)','0.4']])
    await calc.getByLabel(name,{exact:true}).fill(value);
  for(const n of [1,2])for(const label of ['Relief','Penalty','Additional tax','Other payments','Municipal rate increase','Municipal rate decrease'])
    await calc.getByLabel(`Local ${n}: ${label}`,{exact:true}).fill('0');
  await calc.getByRole('combobox',{name:'Minimum-tax classification',exact:true}).selectOption('general');
  await calc.getByRole('combobox',{name:'Company falls under article 60-2(1)(1)',exact:true}).selectOption('false');
  for(const label of ['Full-year schedule applicability verified','Minimum-tax classification verified','Relief eligibility, caps and expiry verified',
    'No base-changing incentives','National additions and payment evidence verified','Initial return, city grouping and final ratios verified',
    'Local relief caps, rate adjustments and payments verified','Ordinary domestic company verified; no rural-special, land-transfer, retained-income or other separate taxes, amended return or installments'])
    await calc.getByRole('combobox',{name:label,exact:true}).selectOption('true');
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Verified national income reconciliation, independent local base, final city ratios and all payment evidence.');
  await calc.getByRole('checkbox').check();await calc.getByRole('button',{name:'Calculate and save result'}).click();
  await expect(calc.getByRole('alert')).toContainText('unique');
  await calc.getByLabel('Local 2: filing authority name',{exact:true}).fill('Branch');
  await calc.getByRole('checkbox').check();await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  const national=report.getByRole('region',{name:'Korean national tax',exact:true});
  await expect(national.locator('dl > div').filter({hasText:'Calculated refundable'}).locator('dd')).toHaveText(withRelief?'2000000':'1000000');
  await expect(report.getByRole('region',{name:'Local authority: HQ',exact:true})).toContainText('1200000');
  await expect(report.getByRole('region',{name:'Local authority: Branch',exact:true})).toContainText('800000');
  await expect(report.getByRole('link',{name:'kr.local-tax.form43.20260701',exact:true})).toHaveAttribute('href',/flSeq=164921007/);
  await report.getByRole('region',{name:'Korean national tax',exact:true}).scrollIntoViewIfNeeded();
  await page.screenshot({path:`test-results/income-tax-korea-company-${withRelief}.png`,fullPage:true});
  await openIncome(page);
  await expect(page.getByRole('region',{name:'Local authority: Branch',exact:true})).toContainText('800000');
});

for(const scenario of [
  {start:'2026-01-01',end:'2026-12-31',tax:'25589600',notice:'Not applicable for this accounting-period start date.'},
  {start:'2026-04-01',end:'2027-03-31',tax:'26317600',notice:'Required, including zero-tax returns.'},
])test(`Japan company national taxes use period start ${scenario.start}`,async({page})=>{
  const form=await openIncome(page);
  await form.getByRole('combobox',{name:'Filing jurisdiction',exact:true}).selectOption('jp');
  await form.getByLabel('Period start',{exact:true}).fill(scenario.start);
  await form.getByLabel('Period end',{exact:true}).fill(scenario.end);
  await form.getByRole('combobox',{name:'Tax residency',exact:true}).selectOption('resident');
  await form.getByRole('combobox',{name:'Income source jurisdiction',exact:true}).selectOption('jp');
  await form.getByLabel('Gross income',{exact:true}).fill('200000000');
  await form.getByLabel('Income description',{exact:true}).fill('Ordinary domestic business revenue for the full accounting year');
  await form.getByLabel('Claimed deductions (blank if unknown)',{exact:true}).fill('100000000');
  await form.getByLabel('Carried losses (blank if unknown)',{exact:true}).fill('0');
  await form.getByRole('checkbox').check();
  await form.getByRole('button',{name:'Save income-tax details'}).click();
  await expect(form.getByRole('status')).toHaveText('Income-tax details saved.');
  const assessment=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await assessment.getByRole('combobox',{name:'Applicable regime',exact:true}).selectOption('jp_company_starting_2026');
  await assessment.getByLabel('Established taxable income before JPY 1,000 truncation',{exact:true}).fill('100000000');
  await assessment.getByRole('combobox',{name:'Verified corporation-rate classification',exact:true}).selectOption('ordinary');
  await assessment.getByLabel('Corporation interim-return liability',{exact:true}).fill('24000000');
  await assessment.getByLabel('Local corporation interim-return liability',{exact:true}).fill('1000000');
  for(const label of ['Capital, control exclusions and excluded-business classification verified','Ordinary domestic tax base verified; no credits, additions, retained-profit surtax or group regime'])
    await assessment.getByRole('combobox',{name:label,exact:true}).selectOption('true');
  await assessment.getByLabel('Tax-basis adjustments and eligibility explanation',{exact:true}).fill('Full-year ordinary domestic taxable income reconciled with books; exclusions and interim liabilities checked.');
  await assessment.getByRole('checkbox').check();
  await assessment.getByRole('button',{name:'Calculate and save result'}).click();
  const result=assessment.getByRole('article',{name:'Saved calculation result'});
  await expect(result).toContainText(scenario.tax);
  await expect(result).toContainText(scenario.notice);
  await expect(result).toContainText('without automatic offsets');
  await expect(result).toContainText('-800000');
  await expect(result).toContainText('1389600');
  await expect(result.getByRole('region',{name:'Company basis reconciliation'})).toContainText('100000000');
  await expect(result.getByRole('link')).toHaveCount(8);
  if(scenario.start==='2026-04-01'){
    await result.locator('h4').scrollIntoViewIfNeeded();
    await page.screenshot({path:'test-results/japan-company-result.png',fullPage:true});
  }
  await openIncome(page);
  await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText(scenario.notice);
});

for (const scenario of [
  {name:'salary refund',category:'employment',gross:'6000000',expenses:'0',other:'960000',deductions:'960000',withheld:'176100',balance:'-34692'},
  {name:'business payment',category:'business',gross:'10000000',expenses:'7000000',other:'720000',deductions:'7720000',withheld:'0',balance:'63300'},
]) test(`Japan national annual ${scenario.name} persists with local-tax exclusion`,async({page})=>{
  const form=await openIncome(page);
  await form.getByRole('combobox',{name:'Taxpayer',exact:true}).selectOption('individual');
  await form.getByRole('combobox',{name:'Filing jurisdiction',exact:true}).selectOption('jp');
  await form.getByLabel('Period start',{exact:true}).fill('2026-01-01');
  await form.getByLabel('Period end',{exact:true}).fill('2026-12-31');
  await form.getByRole('combobox',{name:'Tax residency',exact:true}).selectOption('resident');
  await form.getByRole('combobox',{name:'Income category',exact:true}).selectOption(scenario.category);
  await form.getByRole('combobox',{name:'Income source jurisdiction',exact:true}).selectOption('jp');
  await form.getByLabel('Gross income',{exact:true}).fill(scenario.gross);
  await form.getByLabel('Income description',{exact:true}).fill('Domestic ordinary income, complete annual taxable receipts');
  await form.getByLabel('Claimed deductions (blank if unknown)',{exact:true}).fill(scenario.deductions);
  await form.getByLabel('Carried losses (blank if unknown)',{exact:true}).fill('0');
  await form.getByRole('checkbox').check();
  await form.getByRole('button',{name:'Save income-tax details'}).click();
  await expect(form.getByRole('status')).toHaveText('Income-tax details saved.');
  const assessment=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await assessment.getByRole('combobox',{name:'Applicable regime',exact:true}).selectOption('jp_resident_ordinary_2026');
  for(const [label,value] of [
    ['Verified business expenses (0 if none)',scenario.expenses],
    ['Other income deductions (excluding automatic deductions)',scenario.other],
    ['Verified national income-tax credits within limits','0'],
    ['Tax withheld for this year',scenario.withheld],
    ['Effective notified estimated-tax liability (not cash paid)','0'],
  ]) await assessment.getByLabel(label,{exact:true}).fill(value);
  for(const [label,value] of [
    ['Eligible for salary adjustment for under-23 dependents or special disability','false'],
    ['Full-year resident domestic ordinary scope verified; salary uses taxable withholding-statement receipts','true'],
    ['Deductions, adjustment eligibility, credit limits and estimated-tax notice verified','true'],
  ]) await assessment.getByRole('combobox',{name:label,exact:true}).selectOption(value);
  await assessment.getByLabel('Tax-basis adjustments and eligibility explanation',{exact:true}).fill('Annual national return checked against source documents; no foreign income or excluded relief.');
  await assessment.getByRole('checkbox').check();
  await assessment.getByRole('button',{name:'Calculate and save result'}).click();
  const result=assessment.getByRole('article',{name:'Saved calculation result'});
  await expect(result).toContainText(scenario.balance);
  await expect(result).toContainText('excluding local inhabitant and enterprise taxes');
  await expect(result.getByRole('link')).toHaveCount(9);
  if(scenario.category==='employment') {
    await result.locator('h4').scrollIntoViewIfNeeded();
    await page.screenshot({path:'test-results/japan-national-result.png',fullPage:true});
  }
  await openIncome(page);
  await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText(scenario.balance);
});

for(const kind of ['individual','company','individual_old','company_normal']) for(const settlement of [false,true]) test(`India ${kind} TY2026 ${settlement?'settlement':'annual liability'} persists`,async({page})=>{
  const old=kind==='individual_old',normal=kind==='company_normal',subject=old?'individual':normal?'company':kind;
  const form=await openIncome(page);
  await form.getByRole('combobox',{name:'Taxpayer',exact:true}).selectOption(subject);
  await form.getByRole('combobox',{name:'Filing jurisdiction',exact:true}).selectOption('in');
  await form.getByLabel('Period start',{exact:true}).fill('2026-04-01');
  await form.getByLabel('Period end',{exact:true}).fill('2027-03-31');
  await form.getByRole('combobox',{name:'Tax residency',exact:true}).selectOption('resident');
  await form.getByRole('combobox',{name:'Income category',exact:true}).selectOption('business');
  await form.getByRole('combobox',{name:'Income source jurisdiction',exact:true}).selectOption('in');
  await form.getByLabel('Gross income',{exact:true}).fill('1700000');
  await form.getByLabel('Income description',{exact:true}).fill('Domestic ordinary business income');
  await form.getByLabel('Claimed deductions (blank if unknown)',{exact:true}).fill('100000');
  await form.getByLabel('Carried losses (blank if unknown)',{exact:true}).fill('0');
  await form.getByRole('checkbox').check();
  await form.getByRole('button',{name:'Save income-tax details'}).click();
  await expect(form.getByRole('status')).toHaveText('Income-tax details saved.');
  const assessment=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await assessment.getByRole('combobox',{name:'Applicable regime',exact:true}).selectOption(normal?'in_company_normal_ty2026_27':old?'in_personal_old_ty2026_27':subject==='individual'?'in_personal_new_ty2026_27':'in_company_section200_ty2026_27');
  if(normal){
    await assessment.getByLabel('Verified statutory turnover/gross receipts for 2024–25',{exact:true}).fill('4000000000');
    await assessment.getByLabel('Verified positive MAT book profit before rounding (0 if none)',{exact:true}).fill('4000000');
    await assessment.getByRole('combobox',{name:'Historical turnover classification, MAT adjustments and ordinary regime verified',exact:true}).selectOption('true');
  }
  if(old){
    await assessment.getByRole('combobox',{name:'Highest age band attained during this tax year',exact:true}).selectOption('60_to79');
    await assessment.getByRole('combobox',{name:'AMT non-applicability and absence of carried AMT credit verified',exact:true}).selectOption('true');
  }
  await assessment.getByLabel('Established taxable income before rounding',{exact:true}).fill('1600000');
  for(const name of ['Regime election, eligibility, deductions and loss restrictions verified','Ordinary domestic income and all exclusions verified'])
    await assessment.getByRole('combobox',{name,exact:true}).selectOption('true');
  await assessment.getByRole('combobox',{name:'Also calculate the ordinary return balance',exact:true}).selectOption(String(settlement));
  if(settlement){
    await assessment.getByLabel('Verified current-period TDS/TCS credit',{exact:true}).fill(old?'310000':subject==='individual'?'130000':'410000');
    for(const name of ['Advance tax actually paid for this period','Total self-assessment payments including paid interest and fees','Verified cumulative interest including amounts already paid (0 if none)','Verified cumulative fees including amounts already paid (0 if none)'])
      await assessment.getByLabel(name,{exact:true}).fill('0');
    await assessment.getByRole('combobox',{name:'Credits, evidence, cumulative interest/fees and payment allocation verified; no prior refunds, updated return, ESOP deferral, penalties or additional demands',exact:true}).selectOption('true');
  }
  await assessment.getByLabel('Tax-basis adjustments and eligibility explanation',{exact:true}).fill('Ordinary domestic income and eligible deductions reconciled; statutory regime conditions checked.');
  await assessment.getByRole('checkbox').check();
  await assessment.getByRole('button',{name:'Calculate and save result'}).click();
  const result=assessment.getByRole('article',{name:'Saved calculation result'});
  await expect(result).toContainText(normal?'582400':old?'301600':subject==='individual'?'124800':'402690');
  if(normal)await expect(result).toContainText('applied MAT.');
  if(settlement){
    await expect(result).toContainText(normal?'172400':old?'-8400':subject==='individual'?'-5200':'-7310');
    await expect(result).toContainText('calculated refund, not approval');
  }else await expect(result).toContainText('before payment credits, interest and penalties');
  await expect(result.getByRole('link')).toHaveCount(2);
  await openIncome(page);
  await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText('not AY 2026');
});

async function openIncome(page: import('@playwright/test').Page) {
  await page.goto('/');
  await expect(page.getByRole('button', { name: /Switch to English|切换为中文/ })).toBeVisible();
  const english = page.getByRole('button', { name: 'Switch to English' });
  if (await english.isVisible()) await english.click();
  await page.getByRole('button', { name: 'Open case details', exact: true }).click();
  const details = page.locator('.income-tax-facts');
  if (!await details.getByRole('combobox', { name: 'Taxpayer', exact: true }).isVisible())
    await details.locator('summary').click();
  return details;
}

test('personal income details preserve unknown amounts and restore after reload', async ({ page }) => {
  let form = await openIncome(page);
  await form.getByRole('combobox', { name: 'Taxpayer', exact: true }).selectOption('individual');
  await form.getByRole('combobox', { name: 'Filing jurisdiction', exact: true }).selectOption('sg');
  await form.getByLabel('Period start', { exact: true }).fill('2025-01-01');
  await form.getByLabel('Period end', { exact: true }).fill('2025-12-31');
  await form.getByRole('combobox', { name: 'Tax residency', exact: true }).selectOption('resident');
  await form.getByRole('combobox', { name: 'Income category', exact: true }).selectOption('employment');
  await form.getByRole('combobox', { name: 'Income source jurisdiction', exact: true }).selectOption('sg');
  await form.getByLabel('Gross income', { exact: true }).fill('80000.25');
  await form.getByLabel('Income description', { exact: true }).fill('Annual employment earnings');
  const saved = page.waitForResponse(r => r.url().endsWith('/income-tax') && r.request().method() === 'PUT');
  await form.getByRole('button', { name: 'Save income-tax details' }).click();
  const response = await saved;
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.income_tax.claimed_deductions).toBeNull();
  expect(result.income_tax.carried_losses).toBeNull();
  expect(result.income_tax.incomes[0].gross_amount).toBe('80000.25');
  expect(result.income_tax_status).toBe('needs_information');
  await expect(form.getByRole('status')).toHaveText('Income-tax details saved.');
  await expect(form.getByRole('list')).toContainText('Claimed deductions');
  await form.locator('summary').scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'test-results/income-tax-form.png', fullPage: true });
  form = await openIncome(page);
  await expect(form.getByRole('combobox', { name: 'Taxpayer', exact: true })).toHaveValue('individual');
  await expect(form.getByLabel('Gross income', { exact: true })).toHaveValue('80000.25');
  await expect(form.getByLabel('Claimed deductions (blank if unknown)', { exact: true })).toHaveValue('');
  await expect(form).toContainText('saving does not produce a tax liability');
});

test('edits revoke confirmation and jurisdiction switch does not relabel money', async ({ page }) => {
  const form = await openIncome(page);
  await form.getByLabel('Gross income', { exact: true }).fill('123.45');
  const confirm = form.getByRole('checkbox');
  await confirm.check();
  await form.getByLabel('Income description', { exact: true }).fill('Business revenue');
  await expect(confirm).not.toBeChecked();
  const jurisdiction = form.getByRole('combobox', { name: 'Filing jurisdiction', exact: true });
  const original = await jurisdiction.inputValue();
  await jurisdiction.selectOption(original === 'sg' ? 'cn' : 'sg');
  await expect(jurisdiction).toHaveValue(original);
  await expect(form.getByRole('alert')).toContainText('not automatically converted');
  await expect(form.getByLabel('Gross income', { exact: true })).toHaveValue('123.45');
});


test('save conflict retains draft and offers an explicit reload', async ({ page }) => {
  const form = await openIncome(page);
  await form.getByLabel('Period start', { exact: true }).fill('2025-01-01');
  await form.getByLabel('Period end', { exact: true }).fill('2025-12-31');
  await form.getByLabel('Gross income', { exact: true }).fill('250000');
  await form.getByLabel('Income description', { exact: true }).fill('Company trading revenue');
  await page.route('**/api/cases/*/income-tax', route => route.fulfill({status: 409, json: {detail: 'revision_conflict'}}));
  await form.getByRole('button', { name: 'Save income-tax details' }).click();
  await expect(form.getByRole('alert')).toContainText('Your entries are retained');
  await expect(form.getByLabel('Gross income', { exact: true })).toHaveValue('250000');
  await expect(form.getByRole('button', { name: 'Discard current entries and reload saved details' })).toBeVisible();
});


test('company intake saves confirmed zero deductions without inventing a tax result', async ({ page }) => {
  const form = await openIncome(page);
  await form.getByLabel('Period start', { exact: true }).fill('2026-01-01');
  await form.getByLabel('Period end', { exact: true }).fill('2026-12-31');
  await form.getByRole('combobox', { name: 'Tax residency', exact: true }).selectOption('resident');
  await form.getByLabel('Gross income', { exact: true }).fill('1000000');
  await form.getByLabel('Income description', { exact: true }).fill('Domestic business receipts');
  await form.getByLabel('Claimed deductions (blank if unknown)', { exact: true }).fill('0');
  await form.getByLabel('Carried losses (blank if unknown)', { exact: true }).fill('0');
  await form.getByRole('checkbox').check();
  const saved = page.waitForResponse(r => r.url().endsWith('/income-tax') && r.request().method() === 'PUT');
  await form.getByRole('button', { name: 'Save income-tax details' }).click();
  const response = await saved;
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.income_tax.subject).toBe('company');
  expect(result.income_tax.claimed_deductions).toBe('0');
  expect(result.income_tax_status).toBe('awaiting_rule_validation');
  expect(result.missing_fields).toEqual([]);
  expect(result.income_tax_result).toBeNull();
  await expect(form.getByRole('status')).toHaveText('Income-tax details saved.');
});


test('income details remain usable in a phone viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const form = await openIncome(page);
  const field = form.getByRole('combobox', { name: 'Filing jurisdiction', exact: true });
  await expect(field).toBeVisible();
  const box = await field.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  await field.selectOption('jp');
  await form.getByLabel('Gross income', { exact: true }).fill('100000');
  await expect(form.getByLabel('Gross income', { exact: true })).toHaveValue('100000');
  await form.locator('summary').scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'test-results/income-tax-mobile.png', fullPage: true });
});

test('corporate calculation saves a sourced result and amendments invalidate it', async ({page}) => {
  let form = await openIncome(page);
  await form.getByLabel('Period start', {exact:true}).fill('2026-01-01');
  await form.getByLabel('Period end', {exact:true}).fill('2026-12-31');
  await form.getByRole('combobox',{name:'Tax residency',exact:true}).selectOption('resident');
  await form.getByLabel('Gross income',{exact:true}).fill('1000000');
  await form.getByLabel('Income description',{exact:true}).fill('Domestic business revenue');
  await form.getByLabel('Claimed deductions (blank if unknown)',{exact:true}).fill('0');
  await form.getByLabel('Carried losses (blank if unknown)',{exact:true}).fill('0');
  await form.getByRole('checkbox').check();
  await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calculation=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calculation.getByLabel('Applicable regime').selectOption('cn_company_2026');
  await calculation.getByLabel('Established non-taxable income included in total income',{exact:true}).fill('0');
  await calculation.getByLabel('Established exempt income included in total income',{exact:true}).fill('0');
  await calculation.getByLabel('Established taxable income',{exact:true}).fill('1000000');
  await calculation.getByLabel('Normal rate eligibility checked').selectOption('true');
  await calculation.getByLabel('Allowed tax credits',{exact:true}).fill('0');
  await calculation.getByLabel('Prepaid tax for this period',{exact:true}).fill('1000');
  await calculation.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Domestic ordinary company, no adjustments or incentives; prepayment confirmed.');
  await calculation.getByRole('checkbox').check();
  const response=page.waitForResponse(r=>r.url().endsWith('/income-tax/runs') && r.request().method()==='POST');
  await calculation.getByRole('button',{name:'Calculate and save result'}).click();
  expect((await response).status()).toBe(200);
  const report=page.getByRole('article',{name:'Saved calculation result'});
  await expect(report).toContainText('249000');
  await expect(report.getByRole('link')).toHaveCount(1);
  await page.route('**/income-tax/runs/*/report?locale=en',route=>route.fulfill({status:503,json:{detail:'storage_unavailable'}}));
  await report.getByRole('button',{name:'Download calculation record'}).click();
  await expect(report.getByRole('alert')).toContainText('saved result is unchanged');
  await page.unroute('**/income-tax/runs/*/report?locale=en');
  const downloaded=page.waitForEvent('download');
  await report.getByRole('button',{name:'Download calculation record'}).click();
  const download=await downloaded;
  expect(download.suggestedFilename()).toMatch(/^income-tax-.*-en\.md$/);
  const record=await readFile((await download.path())!,'utf8');
  expect(record).toContain('# Income-tax calculation record');
  expect(record).toContain('249000');
  expect(record).toContain('snapshot_hash');
  expect(record).toContain('basis_reconciliation');
  await expect(report.getByRole('alert')).toHaveCount(0);
  await page.screenshot({path:'test-results/income-tax-calculation.png',fullPage:true});
  form=await openIncome(page);
  await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText('249000');
  await form.getByLabel('Gross income',{exact:true}).fill('2000000');
  await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText('excludes unsaved changes');
  await form.getByRole('button',{name:'Save income-tax details'}).click();
  await expect(page.getByRole('article',{name:'Saved calculation result'})).toHaveCount(0);
});

test('resident personal rate calculation uses the saved basis period', async ({page})=>{
  const form=await openIncome(page);
  await form.getByRole('combobox',{name:'Taxpayer',exact:true}).selectOption('individual');
  await form.getByRole('combobox',{name:'Filing jurisdiction',exact:true}).selectOption('sg');
  await form.getByLabel('Period start',{exact:true}).fill('2025-01-01');
  await form.getByLabel('Period end',{exact:true}).fill('2025-12-31');
  await form.getByRole('combobox',{name:'Tax residency',exact:true}).selectOption('resident');
  await form.getByRole('combobox',{name:'Income category',exact:true}).selectOption('employment');
  await form.getByLabel('Gross income',{exact:true}).fill('80000');
  await form.getByLabel('Income description',{exact:true}).fill('Employment income for basis year 2025');
  await form.getByLabel('Claimed deductions (blank if unknown)',{exact:true}).fill('0');
  await form.getByLabel('Carried losses (blank if unknown)',{exact:true}).fill('0');
  await form.getByRole('checkbox').check();
  await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calculation=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calculation.getByLabel('Applicable regime').selectOption('sg_resident_ya2026');
  await calculation.getByLabel('Established chargeable income',{exact:true}).fill('80000');
  await calculation.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Chargeable income verified after applicable deductions and reliefs.');
  await calculation.getByRole('checkbox').check();
  await calculation.getByRole('button',{name:'Calculate and save result'}).click();
  await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText('3350');
  await expect(calculation).toContainText('before credits, prepayments and assessment rounding');
});

for (const subject of ['company','individual'] as const) {
  test(`Indonesia ${subject} annual computation reconciles sources and persists`, async ({page})=>{
    const form=await openIncome(page);
    await form.getByRole('combobox',{name:'Taxpayer',exact:true}).selectOption(subject);
    await form.getByRole('combobox',{name:'Filing jurisdiction',exact:true}).selectOption('id');
    await form.getByLabel('Period start',{exact:true}).fill('2026-01-01');
    await form.getByLabel('Period end',{exact:true}).fill('2026-12-31');
    await form.getByRole('combobox',{name:'Tax residency',exact:true}).selectOption('resident');
    await form.getByRole('combobox',{name:'Income category',exact:true}).selectOption(subject==='company'?'business':'employment');
    await form.getByLabel('Gross income',{exact:true}).fill(subject==='company'?'6000000000':'300000000');
    await form.getByLabel('Income description',{exact:true}).fill('All domestic ordinary receipts; final and exempt regimes excluded');
    await form.getByLabel('Claimed deductions (blank if unknown)',{exact:true}).fill(subject==='company'?'5390000000':'0');
    await form.getByLabel('Carried losses (blank if unknown)',{exact:true}).fill('0');
    await form.getByRole('checkbox').check();
    await form.getByRole('button',{name:'Save income-tax details'}).click();
    const calculation=page.getByRole('region',{name:'Income-tax calculation',exact:true});
    await calculation.getByLabel('Applicable regime').selectOption(subject==='company'?'id_company_2026':'id_resident_2026');
    await calculation.getByLabel('Full-year resident ordinary treatment and final/special-regime exclusions checked').selectOption('true');
    await calculation.getByLabel('Verified withholding and instalments for this period').fill(subject==='company'?'130000000':'15550000');
    if(subject==='company') {
      await calculation.getByLabel('Established taxable income before thousand rounding').fill('610000000');
      await calculation.getByLabel('Complete article 31E receipts checked, with no omitted final or exempt receipts').selectOption('true');
    } else {
      await calculation.getByLabel('Established net income before PTKP').fill('300000000');
      await calculation.getByLabel('Verified PTKP entitlement code').selectOption('K/1');
      await calculation.getByLabel('Start-of-year PTKP and dependent entitlement verified').selectOption('true');
    }
    await calculation.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Verified full-year ordinary regime, complete receipts and adjustments, confirmed start-of-year entitlement and period withholding.');
    await calculation.getByRole('checkbox').check();
    await calculation.getByRole('button',{name:'Calculate and save result'}).click();
    const report=page.getByRole('article',{name:'Saved calculation result'});
    await expect(report).toContainText(subject==='company'?'-49480000':'14000000');
    await expect(report.getByRole('link')).toHaveCount(subject==='company'?6:5);
    if(subject==='company') await expect(report).toContainText('488000000');
    else await expect(report).toContainText('63000000');
    await page.screenshot({path:`test-results/income-tax-indonesia-${subject}.png`,fullPage:true});
    await openIncome(page);
    await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText(subject==='company'?'-49480000':'14000000');
  });
  test(`Thailand ${subject} calculation persists the applicable tax comparison`, async ({page})=>{
    const form=await openIncome(page);
    await form.getByRole('combobox',{name:'Taxpayer',exact:true}).selectOption(subject);
    await form.getByRole('combobox',{name:'Filing jurisdiction',exact:true}).selectOption('th');
    await form.getByLabel('Period start',{exact:true}).fill('2026-01-01');
    await form.getByLabel('Period end',{exact:true}).fill('2026-12-31');
    await form.getByRole('combobox',{name:'Tax residency',exact:true}).selectOption('resident');
    await form.getByRole('combobox',{name:'Income category',exact:true}).selectOption('business');
    await form.getByLabel('Gross income',{exact:true}).fill('4000000');
    await form.getByLabel('Income description',{exact:true}).fill('Domestic ordinary business income');
    await form.getByLabel('Claimed deductions (blank if unknown)',{exact:true}).fill(subject==='company'?'0':'3850000');
    await form.getByLabel('Carried losses (blank if unknown)',{exact:true}).fill('0');
    await form.getByRole('checkbox').check();
    await form.getByRole('button',{name:'Save income-tax details'}).click();
    const calculation=page.getByRole('region',{name:'Income-tax calculation',exact:true});
    await calculation.getByLabel('Applicable regime').selectOption(subject==='company'?'th_company_2026':'th_resident_2026');
    await calculation.getByLabel(subject==='company'?'Established net taxable profit':'Established net taxable income',{exact:true}).fill(subject==='company'?'3500000':'150000');
    await calculation.getByLabel('Ordinary annual treatment and exclusions checked').selectOption('true');
    await calculation.getByLabel('Allowed tax credits',{exact:true}).fill('0');
    await calculation.getByLabel('Prepaid tax for this period',{exact:true}).fill('0');
    if(subject==='company') {
      await calculation.getByLabel('Verified exempt income included in saved income').fill('500000');
      await calculation.getByLabel('Company rate scheme').selectOption('sme');
      await calculation.getByLabel('All SME and continuous-period conditions verified').selectOption('true');
    } else await calculation.getByLabel('Section 40 employment and non-employment classification verified').selectOption('true');
    await calculation.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Annual basis reconciled with verified allowable expenses and allowances; ordinary regime and applicable SME qualification checked.');
    await calculation.getByRole('checkbox').check();
    await calculation.getByRole('button',{name:'Calculate and save result'}).click();
    const report=page.getByRole('article',{name:'Saved calculation result'});
    await expect(report).toContainText(subject==='company'?'505000':'20000');
    await expect(report.getByRole('link')).toHaveCount(subject==='company'?3:4);
    if(subject==='company') await expect(report.getByRole('region',{name:'Company basis reconciliation'})).toContainText('500000');
    if(subject==='individual') {
      await expect(report).toContainText('Minimum tax before exemption');
      await page.screenshot({path:'test-results/income-tax-thailand-individual.png',fullPage:true});
    }
    await openIncome(page);
    await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText(subject==='company'?'505000':'20000');
  });
  test(`Malaysia ${subject} calculation is saved with official evidence`, async ({page})=>{
    const form=await openIncome(page);
    await form.getByRole('combobox',{name:'Taxpayer',exact:true}).selectOption(subject);
    await form.getByRole('combobox',{name:'Filing jurisdiction',exact:true}).selectOption('my');
    await form.getByLabel('Period start',{exact:true}).fill('2026-01-01');
    await form.getByLabel('Period end',{exact:true}).fill('2026-12-31');
    await form.getByRole('combobox',{name:'Tax residency',exact:true}).selectOption('resident');
    await form.getByRole('combobox',{name:'Income category',exact:true}).selectOption(subject==='company'?'business':'employment');
    await form.getByLabel('Gross income',{exact:true}).fill(subject==='company'?'1000000':'100000');
    await form.getByLabel('Income description',{exact:true}).fill('Domestic ordinary income in the 2026 basis period');
    await form.getByLabel('Claimed deductions (blank if unknown)',{exact:true}).fill('0');
    await form.getByLabel('Carried losses (blank if unknown)',{exact:true}).fill('0');
    await form.getByRole('checkbox').check();
    await form.getByRole('button',{name:'Save income-tax details'}).click();
    const calculation=page.getByRole('region',{name:'Income-tax calculation',exact:true});
    await calculation.getByLabel('Applicable regime').selectOption(`my_${subject}_2026`);
    await calculation.getByLabel('Established chargeable income',{exact:true}).fill(subject==='company'?'1000000':'100000');
    await calculation.getByLabel('Ordinary treatment and exclusions checked').selectOption('true');
    for (const label of ['Allowed tax rebates','Allowed tax credits','Prepaid tax for this period'])
      await calculation.getByLabel(label,{exact:true}).fill('0');
    if(subject==='company') {
      await calculation.getByLabel('Company rate scheme').selectOption('sme');
      await calculation.getByLabel('All SME rate conditions verified').selectOption('true');
    }
    for(const label of ['Source 1: Verified additions','Source 1: Allowed source deductions','Source 1: Statutory charges','Source 1: Statutory allowances','Schedule 4 additions','Verified total-income deductions',...(subject==='individual'?['Allowed personal reliefs']:[])])
      await calculation.getByLabel(label,{exact:true}).fill('0');
    for(const label of ['Source adjustments and deduction eligibility verified',subject==='company'?'Standalone ordinary company without group relief verified':'Separate assessment verified'])
      await calculation.getByRole('combobox',{name:label,exact:true}).selectOption('true');
    await calculation.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Chargeable income and applicable ordinary or SME eligibility conditions checked against supporting records.');
    await calculation.getByRole('checkbox').check();
    await calculation.getByRole('button',{name:'Calculate and save result'}).click();
    await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText(subject==='company'?'195000':'9400');
    if(subject==='individual') {
      const schedule=page.getByRole('region',{name:'Tax basis reconciliation',exact:true});
      await expect(schedule).toContainText('100000');
      await expect(schedule).toContainText('Prior business losses used');
    }
    await expect(page.getByRole('article',{name:'Saved calculation result'}).getByRole('link').first()).toHaveAttribute('href',/lom.agc.gov.my/);
    if(subject==='company') await page.screenshot({path:'test-results/income-tax-malaysia-company.png',fullPage:true});
    await openIncome(page);
    await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText(subject==='company'?'195000':'9400');
    if(subject==='individual') {
      const schedule=page.getByRole('region',{name:'Tax basis reconciliation',exact:true});
      await expect(schedule).toContainText('100000');
      await expect(schedule).toContainText('Prior business losses used');
    }
  });
}

test('Vietnam employment saves dependent deductions and official source', async ({page})=>{
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','individual'],['Filing jurisdiction','vn'],['Tax residency','resident'],['Income category','employment']])
    await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Gross income','786000000'],['Income description','Domestic annual employment'],['Claimed deductions (blank if unknown)','325800000'],['Carried losses (blank if unknown)','0']])
    await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('checkbox').check();
  await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calc.getByLabel('Applicable regime').selectOption('vn_employment_2026');
  for(const [name,value] of [['Chargeable pay before personal deductions','786000000'],['Eligible months per dependent (comma-separated; enter 0 for none)','12,13'],['Verified deductible insurance','24000000'],['Verified article 11 deductions','4200000'],['Prepaid tax for this period','100000000']])
    await calc.getByLabel(name,{exact:true}).fill(value);
  await calc.getByLabel('Full calendar-year resident assessment verified').selectOption('true');
  await calc.getByLabel('Pay classification, deductions and nonduplicated dependent-month claims verified').selectOption('true');
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Verified chargeable pay, residence, insurance limits, deduction evidence and unique dependent-month entitlements.');
  await calc.getByRole('checkbox').check();
  await calc.getByRole('button',{name:'Calculate and save result'}).click();
  await expect(calc.getByRole('alert')).toContainText('whole months from 0 to 12');
  await calc.getByLabel('Eligible months per dependent (comma-separated; enter 0 for none)',{exact:true}).fill('12,6');
  await calc.getByRole('checkbox').check();
  await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  for(const value of ['50040000','-49960000','111600000']) await expect(report).toContainText(value);
  await expect(report.getByRole('link',{name:'vn.law.pit2026.vi',exact:true})).toHaveAttribute('href',/congbaocdn.chinhphu.vn/);
  await page.screenshot({path:'test-results/income-tax-vietnam-employment.png',fullPage:true});
  await openIncome(page);
  await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText('-49960000');
});

for (const isNew of [false,true]) test(`Vietnam company ${isNew?'new':'existing'} uses conditional revenue facts`, async ({page})=>{
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','company'],['Filing jurisdiction','vn'],['Tax residency','resident'],['Income category','business']])
    await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Gross income','10000000000'],['Income description','All ordinary domestic statutory revenue'],['Claimed deductions (blank if unknown)','9000000000'],['Carried losses (blank if unknown)','0']])
    await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('checkbox').check();
  await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calc.getByLabel('Applicable regime').selectOption('vn_company_2026');
  await calc.getByLabel('Established exempt income included in saved income',{exact:true}).fill('0');
  await calc.getByLabel('Established taxable income',{exact:true}).fill('1000000000');
  await calc.getByRole('combobox',{name:'Enterprise established in Vietnam',exact:true}).selectOption('true');
  const newField=calc.getByRole('combobox',{name:'Enterprise newly established in this period',exact:true});
  await newField.selectOption('false');
  await calc.getByLabel('Complete prior-period statutory revenue',{exact:true}).fill('4000000000');
  await calc.getByRole('combobox',{name:'Prior-period statutory active months',exact:true}).selectOption('12');
  if(isNew) {
    await newField.selectOption('true');
    await expect(calc.getByLabel('Complete prior-period statutory revenue',{exact:true})).toHaveCount(0);
  }
  await calc.getByRole('combobox',{name:'Related enterprise disqualifies small-revenue exemption',exact:true}).selectOption('false');
  await calc.getByRole('combobox',{name:'Related enterprise disqualifies reduced rates',exact:true}).selectOption('false');
  const split=calc.getByRole('combobox',{name:'Enterprise formed by a split after the resolution',exact:true});
  await split.selectOption('true');
  await calc.getByLabel('Combined statutory revenue of all split entities (including this enterprise)',{exact:true}).fill('11000000000');
  if(!isNew) {
    await split.selectOption('false');
    await expect(calc.getByLabel('Combined statutory revenue of all split entities (including this enterprise)',{exact:true})).toHaveCount(0);
  }
  await calc.getByLabel('Verified other incentives before annual relief',{exact:true}).fill('20000000');
  await calc.getByLabel('Prepaid tax for this period',{exact:true}).fill('150000000');
  for(const name of ['Ordinary domestic income and all exclusions verified','Complete statutory revenue scope and periods verified','Other incentive amount and eligibility verified'])
    await calc.getByRole('combobox',{name,exact:true}).selectOption('true');
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Verified ordinary domestic scope, complete revenues, prior period, relationship exclusions and separately established incentives.');
  await calc.getByRole('checkbox').check();
  await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  await expect(report.locator('dl > div').filter({hasText:'Tax for this assessment'}).locator('dd')).toHaveText(isNew ? /^150000000(?:\.0+)?$/ : /^105000000(?:\.0+)?$/);
  if(!isNew) await expect(report).toContainText('-45000000');
  await expect(report.getByRole('link')).toHaveCount(5);
  await expect(report.getByRole('region',{name:'Company basis reconciliation',exact:true})).toContainText('9000000000');
  await expect(report).toContainText('Annual tax reduction');
  await openIncome(page);
  await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText(isNew?'150000000':'105000000');
});

test('Vietnam personal securities saves result',async({page})=>{
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','individual'],['Filing jurisdiction','vn'],['Tax residency','resident'],['Income category','capital_gain'],['Income source jurisdiction','vn']]) await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Gross income','1000000000'],['Income description','Ordinary share sale'],['Claimed deductions (blank if unknown)','0'],['Carried losses (blank if unknown)','0']]) await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('checkbox').check(); await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calc.getByLabel('Applicable regime').selectOption('vn_personal_transfer_2026');
  await calc.getByLabel('1. Statutory recognition date',{exact:true}).fill('2026-07-01');
  await calc.getByRole('combobox',{name:'1. Verified asset and cost classification',exact:true}).selectOption('capital_known');
  await calc.getByLabel('1. Acquisition cost',{exact:true}).fill('600000000');
  await calc.getByLabel('1. Reasonable transfer costs',{exact:true}).fill('10000000');
  await calc.getByRole('combobox',{name:'1. Verified asset and cost classification',exact:true}).selectOption('security');
  await expect(calc.getByLabel('1. Acquisition cost',{exact:true})).toHaveCount(0);
  await calc.getByLabel('1. Tax prepaid for this transaction',{exact:true}).fill('0');
  for(const name of ['1. Ordinary taxable sale; no deferred contribution or property-linked whole-business sale','1. Classification, statutory price, territorial scope and absence of exemption/treaty relief verified']) await calc.getByRole('combobox',{name,exact:true}).selectOption('true');
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('Verified domestic share sale, statutory value and no relief.');
  await calc.getByRole('checkbox').check();await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  await expect(report.locator('dl > div').filter({hasText:'Tax for this assessment'}).locator('dd')).toHaveText(/^1000000(?:\.0+)?$/);
  await expect(report.getByRole('link')).toHaveCount(2);
  await expect(report.getByRole('region',{name:'Transfer 1',exact:true})).toContainText('Securities proceeds');
  await expect(report.getByRole('region',{name:'Transfer 1',exact:true})).toContainText('2026-07-01');
  await openIncome(page);await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText('1000000');
});
