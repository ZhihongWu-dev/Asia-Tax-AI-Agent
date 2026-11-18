import {test, expect} from '@playwright/test';

test('cancel preserves a chat; confirm deletes it and reload does not restore it', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button', {name:'Switch to English'}).click();
  await expect(page.locator('.case-item')).toHaveCount(1);
  const oldId = new URL(page.url()).hash.slice(1);
  await page.getByRole('button', {name:/More options/}).click();
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByRole('menuitem', {name:'Delete', exact:true}).click();
  expect((await page.request.get(`/api/cases/${oldId}`)).status()).toBe(200);
  await page.getByRole('button', {name:/More options/}).click();
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('menuitem', {name:'Delete', exact:true}).click();
  await expect.poll(() => new URL(page.url()).hash.slice(1)).not.toBe(oldId);
  expect((await page.request.get(`/api/cases/${oldId}`)).status()).toBe(404);
  await page.reload();
  await expect(page.locator('.case-item')).toHaveCount(1);
  expect(new URL(page.url()).hash.slice(1)).not.toBe(oldId);
});

test('a revision conflict retains the chat and reports failure', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button', {name:'Switch to English'}).click();
  await expect(page.locator('.case-item')).toHaveCount(1);
  const oldId = new URL(page.url()).hash.slice(1);
  await page.route(`**/api/cases/${oldId}`, route => route.request().method() === 'DELETE'
    ? route.fulfill({status:409, json:{detail:'revision_conflict'}}) : route.continue());
  await page.getByRole('button', {name:/More options/}).click();
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('menuitem', {name:'Delete', exact:true}).click();
  await expect(page.getByText('Could not update. Refresh and retry.')).toBeVisible();
  await expect(page.locator('.case-item')).toHaveCount(1);
  expect(new URL(page.url()).hash.slice(1)).toBe(oldId);
});
