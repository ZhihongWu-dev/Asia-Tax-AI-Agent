import {test, expect} from '@playwright/test';

test('atlas renders rates, unknowns, country sources and complete clause', async ({page}) => {
  const version = {library:'fixture-v1',source:'reviewed snapshot',rules:1};
  const cell = {floor:10,ceiling:10,status:'resolved',value_kind:'rate',needs:[],rules:['r1'],cite_ids:['cn.law#1']};
  const unknown = {...cell,floor:null,ceiling:null,status:'unknown',cite_ids:[]};
  const jur = {code:'cn',iso:'156',name:'China',name_zh:'中国',currency:'CNY',wht_company:cell,wht_individual:unknown};
  const passage = 'Full original provision. '.repeat(300);
  await page.route('**/api/atlas/**', route => {
    const url = new URL(route.request().url());
    const body = url.pathname.endsWith('/map') ? {date:'2026-11-18',version,facts:{},metrics:[],jurisdictions:[jur]} :
      url.pathname.includes('/country/') ? {...jur,date:'2026-11-18',version,headline:{wht_company:cell,wht_individual:unknown},cit:null,partners:[],slots:[],params:[],absent:[],docs:[],terms:[]} :
      url.pathname.endsWith('/clause') ? {cite_id:'cn.law#1',doc_id:'cn.law',label:'Article 1',text:passage,total:passage.length,title:'Fixture law',url:'',lang:'en',jur:'cn'} :
      {version,slots:[],terms:[],jurisdictions:[jur]};
    return route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  });
  await page.goto('/');
  await page.getByRole('button',{name:'税务地图',exact:true}).click();
  await expect(page.locator('.atlas-ranking')).toContainText('10%');
  await page.locator('.atlas-ranking button').click();
  await expect(page.locator('.atlas-country-head')).toContainText('中国');
  await expect(page.locator('.atlas-stats')).toContainText('—');
  await page.locator('.atlas-country .atlas-cite').first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.locator('.atlas-clause-text')).toHaveText(passage);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('tab',{name:'税务词典',exact:true}).click();
  await expect(page.getByRole('textbox',{name:'搜索术语'})).toBeVisible();
});

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
