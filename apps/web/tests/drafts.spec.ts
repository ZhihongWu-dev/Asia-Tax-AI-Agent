import {test, expect} from '@playwright/test';

test('opening and repeatedly selecting a new chat creates no server case', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button', {name:'Switch to English'}).click();
  const input = page.getByRole('textbox', {name:'Enter your tax question'});
  await input.fill('Keep this unsent question');
  await page.locator('.new-case').click();
  await page.locator('.new-case').click();
  await expect(input).toHaveValue('Keep this unsent question');
  expect(await (await page.request.get('/api/cases')).json()).toEqual([]);
  expect(new URL(page.url()).hash).toBe('');
});

test('first-send failure preserves attachments and retry reuses the created case', async ({page}) => {
  let creates = 0;
  page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/api/cases')) creates++; });
  await page.route('**/api/attachments?*', route => route.fulfill({json:{name:'draft.pdf', page_count:1, pages:[{page:1,text:'Draft document'}], empty_pages:[]}}));
  await page.route('**/messages', route => route.fulfill({status:503, json:{detail:'model_failed'}}));
  await page.goto('/');
  await page.getByRole('button', {name:'Switch to English'}).click();
  await page.locator('input[type=file]').setInputFiles({name:'draft.pdf', mimeType:'application/pdf', buffer:Buffer.from('pdf')});
  await page.getByRole('textbox', {name:'Enter your tax question'}).fill('Please read this document');
  await page.getByRole('button', {name:'Send message'}).click();
  await page.getByRole('checkbox').check();
  await page.getByRole('button', {name:'Send message'}).click();
  await expect(page.locator('.request-error')).toBeVisible();
  await expect(page.locator('.composer .attachment-chip')).toContainText('draft.pdf');
  expect(creates).toBe(1);
  await page.unroute('**/messages');
  await page.locator('.request-error button').click();
  await expect(page.locator('.composer .attachment-chip')).toHaveCount(0, {timeout:15000});
  expect(creates).toBe(1);
  await page.reload();
  await expect(page.locator('.message.user .sent-attachment')).toContainText('draft.pdf');
});

test('opening income facts materializes one case and preserves the unsent text', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button', {name:'Switch to English'}).click();
  await page.getByRole('textbox', {name:'Enter your tax question'}).fill('Unsent income question');
  await page.getByRole('button', {name:'Open case details', exact:true}).click();
  await expect(page.locator('.income-tax-facts')).toBeVisible();
  const cases = await (await page.request.get('/api/cases')).json();
  expect(cases).toHaveLength(1);
  expect(new URL(page.url()).hash).toBe('#'+cases[0].id);
  await page.locator('.panel-header button').last().click();
  await expect(page.getByRole('textbox', {name:'Enter your tax question'})).toHaveValue('Unsent income question');
  await page.getByRole('button', {name:'Open case details', exact:true}).click();
  await expect(page.locator('.income-tax-facts')).toBeVisible();
  expect(await (await page.request.get('/api/cases')).json()).toHaveLength(1);
});
