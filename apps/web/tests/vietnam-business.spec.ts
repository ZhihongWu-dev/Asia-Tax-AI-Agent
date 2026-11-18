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

for(const method of ['revenue','profit'])test(`Vietnam business ${method} saves reconciled activities and restores sources`,async({page})=>{
  const form=await openIncome(page);
  for(const [name,value] of [['Taxpayer','individual'],['Filing jurisdiction','vn'],['Tax residency','resident']])await form.getByRole('combobox',{name,exact:true}).selectOption(value);
  for(const [name,value] of [['Period start','2026-01-01'],['Period end','2026-12-31'],['Claimed deductions (blank if unknown)','1000000000'],['Carried losses (blank if unknown)','0']])await form.getByLabel(name,{exact:true}).fill(value);
  await form.getByRole('button',{name:'Add income',exact:true}).click();
  for(const [n,gross] of ['800000000','1200000000'].entries()) {
    const row=form.locator('.income-tax-item').nth(n);
    await row.getByRole('combobox',{name:'Income category',exact:true}).selectOption('business');
    await row.getByRole('combobox',{name:'Income source jurisdiction',exact:true}).selectOption('vn');
    await row.getByLabel('Gross income',{exact:true}).fill(gross);
    await row.getByLabel('Income description',{exact:true}).fill(n?'Ordinary goods receipts':'Digital content receipts');
  }
  await form.getByRole('checkbox').check();
  await form.getByRole('button',{name:'Save income-tax details'}).click();
  const calc=page.getByRole('region',{name:'Income-tax calculation',exact:true});
  await calc.getByLabel('Applicable regime').selectOption('vn_business_2026');
  await calc.getByRole('combobox',{name:'Valid calculation method',exact:true}).selectOption('revenue');
  await calc.getByRole('combobox',{name:'1. Business income classification',exact:true}).selectOption('digital_content');
  await calc.getByRole('combobox',{name:'2. Business income classification',exact:true}).selectOption('goods');
  await calc.getByLabel('1. Allocated annual revenue deduction',{exact:true}).fill('800000000');
  await calc.getByLabel('2. Allocated annual revenue deduction',{exact:true}).fill('200000000');
  await calc.getByRole('combobox',{name:'Revenue-method entry within the VND 3bn limit verified',exact:true}).selectOption('true');
  if(method==='profit') {
    await calc.getByRole('checkbox').check();
    await calc.getByRole('combobox',{name:'Valid calculation method',exact:true}).selectOption('profit');
    await expect(calc.getByRole('checkbox')).not.toBeChecked();
    await expect(calc.getByLabel('1. Allocated annual revenue deduction',{exact:true})).toHaveCount(0);
    await calc.getByLabel('Verified deductible business expenses',{exact:true}).fill('1000000000');
  }
  await calc.getByLabel('Actual prepaid and withheld tax for this period',{exact:true}).fill('1000000');
  for(const name of [
    'Domestic ordinary business only; no property rent, special relief or foreign business verified',
    'All business receipts, classifications and expense evidence verified, including platform-withheld receipts',
    'Method election and two-year continuity verified; no switch solely for lower tax'])await calc.getByRole('combobox',{name,exact:true}).selectOption('true');
  await calc.getByLabel('Tax-basis adjustments and eligibility explanation').fill('All annual business receipts, allocation, costs and valid method election verified.');
  await calc.getByRole('checkbox').check();
  await calc.getByRole('button',{name:'Calculate and save result'}).click();
  const report=page.getByRole('article',{name:'Saved calculation result'});
  const expected=method==='profit'?'105000000':'3500000';
  await expect(report.locator('dl > div').filter({hasText:'Tax for this assessment'}).locator('dd')).toHaveText(new RegExp(`^${expected}(?:\\.0+)?$`));
  await expect(report.getByRole('link')).toHaveCount(5);
  await expect(report.getByRole('region',{name:'Business activity 1',exact:true})).toContainText('Digital content business');
  await expect(report.getByRole('region',{name:'Business activity 2',exact:true})).toContainText('Goods distribution/supply');
  if(method==='profit')await expect(report).toContainText('two-year profit-method continuity');
  await openIncome(page);
  await expect(page.getByRole('article',{name:'Saved calculation result'})).toContainText(expected);
  await page.getByRole('button',{name:'Close details',exact:true}).click();
  await page.getByRole('button',{name:'切换为中文'}).click();
  await page.getByRole('button',{name:'打开案例信息',exact:true}).click();
  await expect(page.getByRole('region',{name:'经营所得计算明细'})).toContainText('数字内容业务');
});
