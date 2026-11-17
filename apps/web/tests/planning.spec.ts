import { test, expect } from '@playwright/test';

async function resultsFixture(page:import('@playwright/test').Page, mismatch=false){
  await page.route('**/planning-runs',route=>route.fulfill({json:{items:[{id:'saved-run',case_revision:3,status:'succeeded',created_at:1,error:null}],next_before:null}}));
  await page.route('**/planning-runs/saved-run/artifacts/*',route=>{
    const name=route.request().url().split('/').pop()!;
    const contents:Record<string,object>={
      'tax.json':{amount:0,currency:'JPY',taxes:[
        {branch_id:'b1',cand_id:'c1',complete:true,amount:{floor:0,ceiling:0},per_100:{floor:5,ceiling:10},answers_assumed:{beneficial_owner:'yes'},needs:[],needs_under_assumption:[]},
        {branch_id:'b2',cand_id:'c2',complete:false,amount:{floor:null,ceiling:null},per_100:{floor:null,ceiling:null},answers_assumed:{},needs:[['FACT','holding_months']],needs_under_assumption:[]}]},
      'ranking.json':{ranking:[{branch_id:'b1',cand_id:'c1',rank:1},{branch_id:'b2',cand_id:'c2',rank:null,why:'incomplete'}]},
      'paths.json':{candidates:[{cand_id:'c1',path:['jp:company','sg:individual']},{cand_id:'c2',path:['jp:company','hk:company','sg:individual']}]},
      'open_items.json':{open_items:[{question:'Confirm beneficial ownership',key:'beneficial_owner',changes_rank:true}]},
    };
    return route.fulfill({json:{run_id:'saved-run',case_revision:3,content:{version:mismatch&&name==='paths.json'?'wrong':'saved-version',...contents[name]}}});
  });
}

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

test('saved results preserve zero, unknown amounts and conditional ranking',async({page})=>{
  await resultsFixture(page);
  const panel=await open(page);
  await panel.getByRole('button',{name:'View results',exact:true}).click();
  const result=panel.getByRole('region',{name:'Planning results'});
  await expect(result).toContainText('Case revision 3');
  await expect(result).toContainText('Submitted dividend amount: 0 JPY');
  const options=result.locator('.planning-option');
  await options.nth(0).locator('summary').click();
  await expect(options.nth(0)).toContainText('Tax amount range: 0 JPY');
  await expect(options.nth(0)).toContainText('beneficial_owner');
  await options.nth(1).locator('summary').click();
  await expect(options.nth(1)).toContainText('Not ranked');
  await expect(options.nth(1)).toContainText('Tax amount range: Unknown JPY');
  await expect(result).toContainText('Confirm beneficial ownership');
  await panel.getByLabel('Dividend amount',{exact:true}).fill('999');
  await expect(result).toContainText('Submitted dividend amount: 0 JPY');
  await result.screenshot({path:'test-results/planning-result.png'});
});

test('inconsistent saved artifacts fail closed and can be retried',async({page})=>{
  await resultsFixture(page,true);
  const panel=await open(page);
  await panel.getByRole('button',{name:'View results',exact:true}).click();
  const result=panel.getByRole('region',{name:'Planning results'});
  await expect(result.getByRole('alert')).toContainText('could not be loaded or verified');
  await expect(result.locator('.planning-option')).toHaveCount(0);
  await resultsFixture(page);
  await result.getByRole('button',{name:'Reload results',exact:true}).click();
  await expect(result.locator('.planning-option')).toHaveCount(2);
});
