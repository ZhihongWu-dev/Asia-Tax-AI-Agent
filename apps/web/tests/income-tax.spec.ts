import { test, expect } from '@playwright/test';

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
