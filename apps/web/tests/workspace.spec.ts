import { test, expect, type Page } from "@playwright/test";

async function startCase(page: Page) {
  await page
    .getByRole("button", { name: "境外股息 从收入性质开始梳理" })
    .click();
  await page.getByRole("button", { name: "发送消息" }).click();
}
async function completeCase(page: Page) {
  await startCase(page);
  await page.getByRole("button", { name: "确认并继续" }).click();
  await page.getByRole("button", { name: "已汇入香港", exact: true }).click();
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
});

test("desktop welcome and no unsolicited network calls", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const external: string[] = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://127.0.0.1:5173"))
      external.push(request.url());
  });
  await page.reload();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "复杂税务",
  );
  await expect(page.getByRole("button", { name: "发送消息" })).toBeDisabled();
  await expect(page.getByText("交互预览", { exact: true })).toBeVisible();
  await page.screenshot({
    path: "test-results/welcome-desktop.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
});

test("fact confirmation, receipt selection and matching official source", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await completeCase(page);
  await expect(
    page.getByRole("heading", { name: "研究起点已整理好" }),
  ).toBeVisible();
  await expect(page.getByText("1,000,000", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "2 《税务条例》第 112 章" }).click();
  await expect(
    page.getByRole("link", { name: "在官方网站阅读" }),
  ).toHaveAttribute("href", /elegislation|resource.data.one.gov/);
  await expect(
    page.getByRole("button", { name: /02.*第 112 章/ }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.screenshot({
    path: "test-results/conversation-desktop.png",
    fullPage: true,
  });
});

test("editing facts invalidates old research and reconfirms", async ({
  page,
}) => {
  await completeCase(page);
  await page.getByRole("button", { name: "编辑事实", exact: true }).click();
  await page.getByLabel("金额", { exact: true }).fill("2,000,000");
  await page.getByRole("button", { name: "保存事实" }).click();
  await expect(
    page.getByRole("heading", { name: "研究起点已整理好" }),
  ).toHaveCount(0);
  await expect(page.getByText("2,000,000", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "确认并继续" })).toBeVisible();
  await page.getByRole("button", { name: "确认并继续" }).click();
  await page.getByRole("button", { name: "不确定", exact: true }).click();
  await expect(
    page.getByText("你选择了「不确定」。", { exact: false }),
  ).toBeVisible();
});

test("case isolation, search and reload clears case data", async ({ page }) => {
  await startCase(page);
  await page.getByRole("button", { name: "新建研究案例" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page
    .getByRole("button", { name: "境外利息 整理资金与收取情况" })
    .click();
  await page.getByRole("button", { name: "发送消息" }).click();
  await expect(page.getByText("50,000", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "境外股息 · 香港 待补充事实" })
    .click();
  await expect(page.getByText("1,000,000", { exact: true })).toBeVisible();
  await expect(page.getByText("50,000", { exact: true })).toHaveCount(0);
  await page.getByRole("textbox", { name: "搜索案例" }).fill("不存在的案例");
  await expect(page.getByText("没有找到匹配的案例")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
});

test("free text is not silently inferred and must have core facts", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "描述你的虚构税务案例" })
    .fill("日本公司的税务问题，虚构案例");
  await page.getByRole("button", { name: "发送消息" }).click();
  await expect(
    page.getByText("当前是交互预览，不会自动解析自由文本", { exact: false }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "确认并继续" })).toBeDisabled();
});

test("Chinese IME Enter does not send; Shift Enter adds a line", async ({
  page,
}) => {
  const composer = page.getByRole("textbox", { name: "描述你的虚构税务案例" });
  await composer.fill("虚构案例");
  await composer.dispatchEvent("compositionstart");
  await composer.press("Enter");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await composer.dispatchEvent("compositionend");
  await composer.fill("虚构案例");
  await composer.press("End");
  await composer.press("Shift+Enter");
  await expect(composer).toHaveValue("虚构案例\n");
  await composer.press("Enter");
  await expect(page.getByRole("heading", { level: 1 })).toHaveCount(0);
});

test("mobile navigation and source dialog trap focus without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.screenshot({
    path: "test-results/welcome-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "打开案例导航" }).click();
  await expect(page.getByRole("dialog", { name: "案例导航" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "打开案例导航" }),
  ).toBeFocused();
  await page.getByRole("button", { name: "法规资料", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "研究详情" });
  await expect(dialog).toBeVisible();
  await expect(page.getByRole("button", { name: "关闭详情" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(
    dialog.getByRole("link", { name: "在官方网站阅读" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await completeCase(page);
  await expect(
    page.getByRole("heading", { name: "研究起点已整理好" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/conversation-mobile.png",
    fullPage: true,
  });
});

test("English flow includes facts, source panels and saved language preference", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Switch to English" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Start with a conversation.",
  );
  await page
    .getByRole("button", {
      name: "Foreign dividends Clarify the nature of the income",
    })
    .click();
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(
    page.getByText("Hong Kong company (fictional)", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Confirm and continue" }).click();
  await page.getByRole("button", { name: "Not sure", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Your research starting point" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "2 Inland Revenue Ordinance, Cap. 112" })
    .click();
  await expect(
    page.getByRole("link", { name: "Read on the official website" }),
  ).toBeVisible();
  // The language switch intentionally keeps the destination label “中文”.
  expect((await page.locator("body").innerText()).replace('中文', '')).not.toMatch(/[\u3400-\u9fff]/);
  await page.screenshot({
    path: "test-results/conversation-english.png",
    fullPage: true,
  });
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([
    "asiatax.language",
  ]);
});

test("switching language preserves user messages, drafts, case state and edited facts", async ({
  page,
}) => {
  const original = "虚构公司的自由描述 original text";
  await page
    .getByRole("textbox", { name: "描述你的虚构税务案例" })
    .fill(original);
  await page.getByRole("button", { name: "Switch to English" }).click();
  await expect(
    page.getByRole("textbox", { name: "Describe your fictional tax case" }),
  ).toHaveValue(original);
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(page.locator(".message.user")).toHaveText(original);
  await page.getByRole("button", { name: "Edit facts", exact: true }).click();
  await page.getByLabel("Taxpayer").fill("虚构公司 Custom Ltd");
  await page.getByLabel("Income type").fill("Custom income");
  await page.getByRole("button", { name: "切换为中文" }).click();
  await expect(page.getByLabel("纳税主体")).toHaveValue("虚构公司 Custom Ltd");
  await page.getByRole("button", { name: "保存事实" }).click();
  await page.getByRole("button", { name: "确认并继续" }).click();
  await page.getByRole("button", { name: "已汇入香港", exact: true }).click();
  await page.getByRole("button", { name: "Switch to English" }).click();
  await expect(
    page.getByRole("heading", { name: "Your research starting point" }),
  ).toBeVisible();
  await expect(
    page.getByText("虚构公司 Custom Ltd", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("You selected “Remitted to Hong Kong”.", { exact: false }),
  ).toBeVisible();
});

test("English mobile layout and source navigation fit the viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Switch to English" }).click();
  await expect(page.getByRole("button", { name: "切换为中文" })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/welcome-english-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "Research details" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Close details", exact: true })
    .click();
  await page.getByRole("button", { name: "Open case navigation" }).click();
  await page.getByRole("button", { name: "How to use" }).click();
  await expect(
    page.getByRole("heading", { name: "About this workspace" }),
  ).toBeVisible();
});
