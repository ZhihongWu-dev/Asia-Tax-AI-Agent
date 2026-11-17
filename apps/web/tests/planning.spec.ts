import { test, expect } from '@playwright/test';

async function open(page:import('@playwright/test').Page){
  await page.goto('/');
  await expect(page.getByRole('button',{name:/Switch to English|切换为中文/})).toBeVisible();
  const language=page.getByRole('button',{name:'Switch to English'});
  if(await language.isVisible())await language.click();
  await page.getByRole('button',{name:'Structure analysis',exact:true}).click();
  const panel=page.locator('.planning-panel');
  await panel.locator('summary').click();
  await expect(panel.getByRole('combobox',{name:'Payer jurisdiction',exact:true})).toBeEnabled();
  return panel;
}

test('saved planning input submits once and history survives reload',async({page})=>{
  let panel=await open(page);
  await expect(panel.getByRole('button',{name:'Submit planning task',exact:true})).toBeDisabled();
  await panel.getByRole('combobox',{name:'Payer jurisdiction',exact:true}).selectOption('jp');
  await panel.getByRole('combobox',{name:'Recipient jurisdiction',exact:true}).selectOption('sg');
  await panel.getByRole('combobox',{name:'Recipient type',exact:true}).selectOption('individual');
  await panel.getByLabel('Payment date',{exact:true}).fill('2026-11-17');
  await panel.getByLabel('Dividend amount',{exact:true}).fill('0');
  await panel.getByLabel('Payment currency',{exact:true}).fill('JPY');
  await panel.getByRole('button',{name:'Save planning details',exact:true}).click();
  await expect(panel.getByRole('status')).toHaveText('Planning details saved.');
  const response=page.waitForResponse(r=>r.url().endsWith('/planning-runs')&&r.request().method()==='POST');
  await panel.getByRole('button',{name:'Submit planning task',exact:true}).click();
  expect((await response).status()).toBe(202);
  await expect(panel.getByRole('list')).toContainText('Queued');
  panel=await open(page);
  await expect(panel.getByLabel('Dividend amount',{exact:true})).toHaveValue('0');
  await expect(panel.getByRole('list')).toContainText('Queued');
  await panel.getByRole('button',{name:'Submit planning task',exact:true}).click();
  await expect(panel.getByRole('list').getByRole('listitem')).toHaveCount(2);
  await panel.getByLabel('Dividend amount',{exact:true}).fill('15');
  await expect(panel.getByRole('button',{name:'Submit planning task',exact:true})).toBeDisabled();
  await page.screenshot({path:'test-results/planning-panel.png',fullPage:true});
});
