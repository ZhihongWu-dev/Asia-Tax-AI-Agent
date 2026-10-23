import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const text = '合成研究：分红公司在中国内地。金额1000000 CNY，计划2026-12-01分红。香港公司直接持有100%股份，自2020-01-01取得。最终给张先生，税务居民地中国内地。没有中间控股公司，目标长期留在公司投资。';

test('existing chat design, consultation confirmation, PDF download and deletion', async ({page}) => {
  await page.goto('/');
  await expect(page.locator('.welcome')).toBeVisible();
  await expect(page.locator('.sidebar')).toBeVisible();
  await expect(page.locator('.suggested-questions')).toBeVisible();
  await expect(page.locator('.brief-intro')).toHaveCount(0);
  await page.getByRole('textbox',{name:'输入你的税务问题'}).fill(text);
  await page.getByRole('button',{name:'发送消息',exact:true}).click();
  await page.locator('.data-consent input').check();
  await page.getByRole('button',{name:'发送消息',exact:true}).click();
  await expect(page.locator('.message.user')).toContainText('1000000');
  const modal = page.getByRole('dialog');
  await expect(modal).toBeVisible();
  await expect(modal.getByRole('button',{name:'生成 PDF',exact:true})).toBeDisabled();
  await modal.getByRole('checkbox').check();
  await modal.getByRole('button',{name:'生成 PDF',exact:true}).click();
  await expect(modal).toHaveCount(0);
  await expect(page.getByRole('button',{name:'下载到本地',exact:true})).toBeVisible();
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button',{name:'下载到本地',exact:true}).click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  await page.reload();
  await expect(page.getByRole('button',{name:'下载到本地',exact:true})).toBeVisible();
  await page.screenshot({path:fileURLToPath(new URL('../../../tmp/pdfs/consultation-chat-preview.png', import.meta.url)),fullPage:true});
  const deletion = page.waitForResponse(r => r.request().method()==='DELETE');
  await page.getByRole('button',{name:'取消下载并删除文件',exact:true}).click();
  const deleted = await deletion;
  expect(deleted.status()).toBe(200);
  expect((await deleted.json()).status).toBe('cancelled');
  expect((await page.request.get(deleted.url()+'/download')).status()).toBe(409);
  await expect(page.getByRole('button',{name:'下载到本地',exact:true})).toHaveCount(0);
  await page.reload();
  await expect(page.getByText('已取消下载并删除服务器上的 PDF。')).toBeVisible();
});

test('missing basics stay in the existing chat without a report dialog', async ({page}) => {
  await page.goto('/');
  await page.getByRole('textbox',{name:'输入你的税务问题'}).fill('我想做股息方案');
  await page.getByRole('button',{name:'发送消息',exact:true}).click();
  await page.locator('.data-consent input').check();
  await page.getByRole('button',{name:'发送消息',exact:true}).click();
  await expect(page.locator('.message.assistant').last()).toContainText('分红公司在哪个国家');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});
