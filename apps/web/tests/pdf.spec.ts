import { test, expect } from '@playwright/test';

test('multiple dropped files can be removed, sent and reopened without losing attachments', async ({page}) => {
  let uploads = 0;
  await page.route('**/api/attachments?*', route => {
    uploads++;
    const name = new URL(route.request().url()).searchParams.get('filename');
    return route.fulfill({json:{name,page_count:1,pages:[{page:1,text:'Dropped document '+name}],empty_pages:[]}});
  });
  await page.goto('/');
  await page.getByRole('button', {name:'Switch to English'}).click();
  const transfer = await page.evaluateHandle(() => {
    const data = new DataTransfer();
    data.items.add(new File(['%PDF-fixture'], 'drop.pdf', {type:'application/pdf'}));
    return data;
  });
  await page.locator('.chat-body').dispatchEvent('dragenter', {dataTransfer:transfer});
  await expect(page.getByText('Drop files to attach', {exact:true})).toBeVisible();
  await page.locator('.chat-body').dispatchEvent('drop', {dataTransfer:transfer});
  await expect(page.locator('.composer .attachment-chip')).toContainText('drop.pdf');
  await expect(page.getByText('Drop files to attach', {exact:true})).toHaveCount(0);
  const multiple = await page.evaluateHandle(() => {
    const data = new DataTransfer();
    for (const name of ['a.pdf','b.pdf']) data.items.add(new File(['pdf'], name, {type:'application/pdf'}));
    return data;
  });
  await page.locator('.chat-body').dispatchEvent('drop', {dataTransfer:multiple});
  await expect(page.locator('.composer .attachment-chip')).toHaveCount(3);
  expect(uploads).toBe(3);
  await page.locator('.composer .attachment-chip').filter({hasText:'a.pdf'}).getByRole('button', {name:'Remove attachment'}).click();
  await expect(page.locator('.composer .attachment-chip')).toHaveCount(2);
  await page.getByRole('textbox', {name:'Enter your tax question'}).fill('Compare the documents.');
  await page.getByRole('button', {name:'Send message'}).click();
  await page.getByRole('checkbox').check();
  const sent = page.waitForRequest(r => r.url().endsWith('/messages') && r.method()==='POST');
  await page.getByRole('button', {name:'Send message'}).click();
  const message = (await sent).postDataJSON().text;
  expect(message).toContain('drop.pdf'); expect(message).toContain('b.pdf'); expect(message).not.toContain('a.pdf');
  // The user bubble is optimistic; clearing waits for the committed SSE case.
  await expect(page.locator('.composer .attachment-chip')).toHaveCount(0, {timeout: 15000});
  await page.reload();
  await expect(page.locator('.message.user .sent-attachment')).toHaveCount(2);
  await expect(page.locator('.message.user')).toContainText('drop.pdf');
  await expect(page.locator('.message.user')).toContainText('b.pdf');
  await transfer.dispose(); await multiple.dispose();
});

test('PDF chip, consent, message and reload retain the attachment', async ({ page }) => {
  await page.route('**/api/attachments?*', route => route.fulfill({ json: {name:'case.pdf', page_count:2, pages:[{page:1,text:'Hong Kong company receives CNY 2000000.'}], empty_pages:[2]} }));
  await page.goto('/');
  await page.getByRole('button', {name:'Switch to English'}).click();
  await page.locator('input[type=file]').setInputFiles({name:'case.pdf', mimeType:'application/pdf', buffer:Buffer.from('%PDF-fixture')});
  await expect(page.locator('.composer .attachment-chip')).toContainText('case.pdf');
  await expect(page.locator('.composer details')).toHaveCount(0);
  await page.getByRole('textbox', {name:'Enter your tax question'}).fill('Please summarize my PDF.');
  await page.getByRole('button', {name:'Send message'}).click();
  await page.getByRole('checkbox').check();
  const message = page.waitForRequest(r => r.url().endsWith('/messages') && r.method()==='POST');
  await page.getByRole('button', {name:'Send message'}).click();
  expect((await message).postDataJSON().text).toContain('2000000');
  await expect(page.locator('.message.user')).toContainText('case.pdf');
  // The user bubble is optimistic; clearing waits for the committed SSE case.
  await expect(page.locator('.composer .attachment-chip')).toHaveCount(0, {timeout: 15000});
  await page.reload();
  await expect(page.locator('.message.user')).toContainText('case.pdf');
  await expect(page.locator('.message.user details, .message.user pre')).toHaveCount(0);
  await expect(page.locator('.message.user .sent-attachment')).toContainText('case.pdf');
});

test('unreadable PDF reports an error and does not attach an empty file', async ({page}) => {
  await page.route('**/api/attachments?*', route => route.fulfill({status:422,json:{detail:'pdf_no_text'}}));
  await page.goto('/');
  await page.getByRole('button', {name:'Switch to English'}).click();
  await page.locator('input[type=file]').setInputFiles({name:'scan.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-fixture')});
  await expect(page.getByRole('alert')).toContainText('Apply OCR first');
  await expect(page.locator('.composer .attachment-chip')).toHaveCount(0);
  await expect(page.getByRole('button', {name:'Send message'})).toBeDisabled();
});

for (const [name, kind, label] of [['case.docx', 'word', 'Document body / tables'], ['case.xlsx', 'excel', 'Worksheet: Dividends']]) {
  test(`paperclip uploads and shows ${name}`, async ({ page }) => {
    await page.route('**/api/attachments?*', route => route.fulfill({json:{name, kind, page_count:1, pages:[{page:1,label,text:'Amount: 2000000'}], empty_pages:[],warnings:[]}}));
    await page.goto('/');
    await page.getByRole('button', {name:'Switch to English'}).click();
    const clip = page.getByRole('button', {name:'Attach file',exact:true});
    await expect(clip).toHaveText('');
    await expect(clip.locator('svg')).toHaveCount(1);
    await page.locator('input[type=file]').setInputFiles({name,mimeType:'application/octet-stream',buffer:Buffer.from('fixture')});
    await expect(page.locator('.composer .attachment-chip')).toContainText(name);
    await expect(page.locator('.composer details, .composer pre')).toHaveCount(0);
    await expect(page.locator('.composer .attachment-chip')).toHaveText(name);
    if (kind === 'word') await page.screenshot({path:'/tmp/taxrora-attachment-preview.png',fullPage:true});
    await page.getByRole('button',{name:'Remove attachment'}).click();
    await expect(page.locator('.composer .attachment-chip')).toHaveCount(0);
  });
}

test('image upload displays thumbnail above sent text and survives reload', async ({page}) => {
  const {readFileSync} = await import('node:fs');
  const bytes = readFileSync('../../tests/chat/fixtures/attachment.jpg');
  const thumb = 'data:image/jpeg;base64,' + bytes.toString('base64');
  await page.route('**/api/attachments?*', route => route.fulfill({json:{name:'receipt.jpg',kind:'image',thumbnail:thumb,page_count:1,pages:[{page:1,text:'Dividend 2000000'}],empty_pages:[],warnings:['image_ocr_only']}}));
  await page.goto('/');
  await page.getByRole('button',{name:'Switch to English'}).click();
  await page.locator('input[type=file]').setInputFiles({name:'receipt.jpg',mimeType:'image/jpeg',buffer:bytes});
  await expect(page.locator('.composer img')).toBeVisible();
  await page.getByRole('textbox',{name:'Enter your tax question'}).fill('Read this image.');
  await page.getByRole('button',{name:'Send message'}).click();
  await page.getByRole('checkbox').check();
  await page.getByRole('button',{name:'Send message'}).click();
  await expect(page.locator('.message.user .sent-image-thumbnail')).toBeVisible();
  await expect(page.locator('.composer img')).toHaveCount(0);
  await page.reload();
  const img = page.locator('.message.user .sent-image-thumbnail');
  await expect(img).toBeVisible();
  await expect(page.getByText('[Taxrora attachment]', {exact:false})).toHaveCount(0);
  expect(await img.evaluate((e:HTMLImageElement) => e.naturalWidth)).toBeGreaterThan(0);
  const card = await page.locator('.message.user .sent-attachment').boundingBox();
  const text = await page.locator('.message.user .user-message-content > p').boundingBox();
  expect(card!.y + card!.height).toBeLessThanOrEqual(text!.y);
  await expect(page.locator('.message.user details, .message.user pre')).toHaveCount(0);
  await page.screenshot({path:'/tmp/taxrora-image-message.png',fullPage:true});
});
