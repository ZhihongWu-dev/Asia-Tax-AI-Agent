import { test, expect, type Page } from "@playwright/test";

async function submit(page: Page) {
  await page.getByRole("button", { name: "发送消息" }).click();
  const consent = page.getByRole("checkbox");
  if (await consent.isVisible()) {
    await consent.check();
    await page.getByRole("button", { name: "发送消息" }).click();
  }
}

for (const [button, hint, task] of [
  ["境外股息", "dividend_consultation", "股息咨询"],
  ["梳理事实", "fact_intake", "梳理事实"],
  ["查阅依据", "reference_lookup", "查阅依据"],
]) {
  test(`shortcut ${hint} transmits its task and avoids a case interview for generic preparation`, async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: button, exact: true }).click();
    const sent = page.waitForRequest(req => req.method() === "POST" && req.url().endsWith("/messages"));
    await submit(page);
    expect((await sent).postDataJSON().entry_hint).toBe(hint);
    await expect(page.locator(".message.assistant")).toHaveCount(1);
    await expect(page.locator(".composer-area [role=status]")).toContainText(task);
    await expect(page.locator(".message.assistant")).not.toContainText("收款方是个人还是公司");
    await page.reload();
    await expect(page.locator(".composer-area [role=status]")).toContainText(task);
  });
}

test("editing a shortcut clears the task hint and keeps normal conversation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "梳理事实", exact: true }).click();
  await page.getByRole("textbox", { name: "输入你的税务问题" }).fill("你好");
  const sent = page.waitForRequest(req => req.method() === "POST" && req.url().endsWith("/messages"));
  await submit(page);
  expect((await sent).postDataJSON().entry_hint).toBe("auto");
  await expect(page.locator(".message.assistant")).toContainText("你好！今天想聊些什么？");
});

test("shortcut retry retains request ID and original entry after another draft is typed", async ({ page }) => {
  await page.goto("/");
  const payloads: Record<string, unknown>[] = [];
  await page.route("**/api/cases/*/messages", async route => {
    payloads.push(route.request().postDataJSON());
    if (payloads.length === 1) await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "model_failed" }) });
    else await route.continue();
  });
  await page.getByRole("button", { name: "查阅依据", exact: true }).click();
  await submit(page);
  await expect(page.getByRole("alert")).toBeVisible();
  await page.getByRole("textbox", { name: "输入你的税务问题" }).fill("下一条草稿");
  await page.getByRole("button", { name: "重试", exact: true }).click();
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  expect(payloads[1]).toEqual(payloads[0]);
  await expect(page.getByRole("textbox", { name: "输入你的税务问题" })).toHaveValue("下一条草稿");
});

test("requested fact summary renders known values without confirming or authorizing analysis", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("textbox", { name: "输入你的税务问题" })).toBeVisible();
  const created = await page.request.post("/api/cases", { headers: { "x-asiatax-request": "1" } });
  expect(created.status()).toBe(201);
  const original = await created.json();
  const path = `/api/cases/${original.id}`;
  const edited = await page.request.patch(path + "/facts", {
    headers: { "x-asiatax-request": "1" },
    data: { revision: original.revision, request_id: crypto.randomUUID(), facts: {
      recipient_type: "company", income_type: "dividend", analysis_jurisdiction: "HK",
      consultation_goal: "scope", dividend_amount: 1000000, holding_percentage_pct: 3,
    } },
  });
  expect(edited.status()).toBe(200);
  await page.goto(`/#${original.id}`);
  // Hash-only navigation does not remount the workspace; reload to fetch the seeded case.
  const loaded = page.waitForResponse(response => response.url().endsWith("/api/cases") && response.request().method() === "GET");
  await page.reload();
  const list = await loaded;
  expect(list.status()).toBe(200);
  expect((await list.json()).find((item: { id: string }) => item.id === original.id).facts.dividend_amount.value).toBe(1000000);
  await expect(page).toHaveURL(new RegExp(original.id));
  await page.getByRole("textbox", { name: "输入你的税务问题" }).fill("先不要下结论，把我已经提供的信息列出来，并说还缺哪些关键资料");
  await submit(page);
  await expect(page.locator(".message.assistant")).toContainText("1000000");
  await expect(page.locator(".message.assistant")).toContainText("待补与待核对");
  const doc = await (await page.request.get(path)).json();
  expect(doc.confirmed_facts).toBeNull();
  expect(doc.dialogue.partial_consent).toBeUndefined();
  expect(doc.analyses).toEqual([]);
});
