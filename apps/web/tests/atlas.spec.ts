import {test, expect} from '@playwright/test';

test('atlas navigation reports unavailable data and returns to saved workspace', async ({page}) => {
  await page.route('**/api/atlas/map', route => route.fulfill({status:503,
    contentType:'application/json', body:JSON.stringify({detail:'atlas_unavailable'})}));
  await page.goto('/');
  await page.getByRole('button', {name:'税务地图', exact:true}).click();
  await expect(page.getByRole('heading', {name:'税务地图', exact:true})).toBeVisible();
  await expect(page.getByRole('alert')).toBeVisible();
  await page.getByRole('button', {name:'返回工作空间', exact:true}).click();
  await expect(page.getByRole('button', {name:'打开案例信息', exact:true})).toBeVisible();
});
