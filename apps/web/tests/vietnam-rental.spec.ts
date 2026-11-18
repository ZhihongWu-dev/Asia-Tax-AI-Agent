import {test,expect,type Page} from '@playwright/test';

async function openIncome(page:Page) {
  await page.goto('/');
  await expect(page.getByRole('button',{name:/Switch to English|切换为中文/})).toBeVisible();
  const english=page.getByRole('button',{name:'Switch to English'});
  if(await english.isVisible())await english.click();
  await page.getByRole('button',{name:'Open case details',exact:true}).click();
  const form=page.locator('.income-tax-facts');
  if(!await form.getByRole('combobox',{name:'Taxpayer',exact:true}).isVisible())await form.locator('summary').click();
  return form;
}

test('Vietnam rental preserves contract allocations, tenant filings and separate balances',async({page})=>{
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','individual'],['Filing jurisdiction','vn'],['Tax residency','resident']])await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Claimed deductions (blank if unknown)','1000000000'],['Carried losses (blank if unknown)','0']])await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('button',{name:'Add income',exact:true}).click();
  for(const [n,gross] of ['800000000','1200000000'].entries()) {
    const row=form.locator('.income-tax-item').nth(n);
    await row.getByRole('combobox',{name:'Income category',exact:true}).selectOption('rental');
    await row.getByRole('combobox',{name:'Income source jurisdiction',exact:true}).selectOption('vn');
    await row.getByLabel('Gross income',{exact:true}).fill(gross);
    await row.getByLabel('Income description',{exact:true}).fill(`Annual property lease ${n+1}`);
  }
  await form.getByRole('checkbox').check();
  await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calc.getByLabel('Applicable regime').selectOption('vn_property_rental_2026');
  for(const n of [1,2]) {
    await calc.getByLabel(`${n}. Contract identifier`,{exact:true}).fill(`Lease-${n}`);
    await calc.getByLabel(`${n}. Allocated annual rental deduction`,{exact:true}).fill(n===1?'800000000':'200000000');
    await calc.getByLabel(`${n}. Actual tax paid for this period`,{exact:true}).fill(n===1?'1000000':'2000000');
    await calc.getByRole('combobox',{name:`${n}. Tenant files and pays on behalf`,exact:true}).selectOption(n===1?'true':'false');
    await calc.getByRole('combobox',{name:`${n}. Contract filing, allocation and payment evidence verified`,exact:true}).selectOption('true');
  }
  for(const name of ['Domestic property rental only; no accommodation or other business verified','Annual revenue recognition and all rental contracts verified'])await calc.getByRole('combobox',{name,exact:true}).selectOption('true');
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('All annual domestic property leases, deduction allocations and actual payments verified.');
  await calc.getByRole('checkbox').check();
  await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  await expect(report.getByRole('link')).toHaveCount(6);
  const first=report.getByRole('region',{name:'Rental contract 1',exact:true});
  const second=report.getByRole('region',{name:'Rental contract 2',exact:true});
  await expect(first).toContainText('Tenant files and pays on behalf');
  await expect(second).toContainText('Landlord responsible for filing');
  await expect(first.locator('dl > div').filter({hasText:'Contract balance'}).locator('dd')).toHaveText(/^-1000000(?:\.0+)?$/);
  await expect(second.locator('dl > div').filter({hasText:'Contract balance'}).locator('dd')).toHaveText(/^33000000(?:\.0+)?$/);
  await openIncome(page);
  await expect(page.getByRole('region',{name:'Rental contract 1',exact:true})).toContainText('Lease-1');
  await page.getByRole('button',{name:'Close details',exact:true}).click();
  await page.getByRole('button',{name:'切换为中文'}).click();
  await page.getByRole('button',{name:'打开案例信息',exact:true}).click();
  await expect(page.getByRole('region',{name:'房产出租计算明细'})).toContainText('由承租人申报代缴');
});
