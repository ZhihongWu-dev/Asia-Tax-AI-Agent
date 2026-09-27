import { test, expect } from "@playwright/test";

test("minimal home has no region selector or demonstration copy", async ({
  page,
}) => {
  const external: string[] = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://127.0.0.1:5173"))
      external.push(request.url());
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "让税务问题，更清晰。" }),
  ).toBeVisible();
  await expect(page.getByRole("combobox")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText(
    /选择地区|演示|预览|虚构|示例/,
  );
  await expect(page.getByLabel("快捷问题").getByRole("button")).toHaveCount(3);
  await expect(page.getByRole("button", { name: "发送消息" })).toBeDisabled();
  await page.screenshot({
    path: "test-results/minimal-desktop.png",
    fullPage: true,
  });
  expect(external).toEqual([]);
});

test("suggestion is editable and disconnected service never fabricates an answer", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "境外股息", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "输入你的税务问题" }),
  ).toHaveValue(/FSIE/);
  await expect(page.getByRole("status")).toHaveCount(0);
  await page.getByRole("button", { name: "发送消息" }).click();
  await expect(page.getByRole("status")).toContainText(
    "消息尚未发送，也未生成分析",
  );
  await expect(page.locator(".message")).toHaveCount(1);
  await page.getByRole("button", { name: "整理案例信息" }).click();
  await expect(page.getByLabel("纳税主体")).toHaveValue("");
  await expect(page.getByLabel("金额", { exact: true })).toHaveValue("");
  await expect(page.getByText("地区", { exact: true })).toHaveCount(0);
});

test("case facts, messages and drafts remain isolated across chats", async ({
  page,
}) => {
  await page.goto("/");
  const input = page.getByRole("textbox", { name: "输入你的税务问题" });
  await input.fill("案例 Alpha");
  await input.press("Enter");
  await page.getByRole("button", { name: "打开案例信息" }).click();
  await page.getByLabel("纳税主体").fill("Alpha Ltd");
  await page.getByLabel("收取情况").selectOption("尚未汇入香港");
  await page.getByRole("button", { name: "保存事实" }).click();
  await input.fill("Alpha 草稿");
  await page.locator(".new-case").click();
  await expect(input).toHaveValue("");
  await page.getByRole("button", { name: "打开案例信息" }).click();
  await expect(page.getByLabel("纳税主体")).toHaveValue("");
  await page.getByRole("button", { name: "关闭详情" }).click();
  await page.getByRole("button", { name: "案例 Alpha", exact: true }).click();
  await expect(input).toHaveValue("Alpha 草稿");
  await page.getByRole("button", { name: "打开案例信息" }).click();
  await expect(page.getByLabel("纳税主体")).toHaveValue("Alpha Ltd");
  await expect(page.getByLabel("收取情况")).toHaveValue("尚未汇入香港");
  await page.getByRole("textbox", { name: "搜索对话" }).fill("absent");
  await expect(page.getByText("没有找到匹配的案例")).toBeVisible();
});

test("source metadata is available on demand with correct official links", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "法规资料", exact: true }).click();
  const link = page.getByRole("link", { name: "在官方网站阅读" });
  await expect(link).toHaveAttribute("href", /ird.gov.hk/);
  await expect(page.getByText("尚未验证", { exact: true })).not.toBeVisible();
  await page.getByText("来源与版本", { exact: true }).click();
  await expect(page.getByText("尚未验证", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /《税务条例》第 112 章/ }).click();
  await expect(link).toHaveAttribute("href", /elegislation.gov.hk/);
  await page.screenshot({
    path: "test-results/minimal-sources.png",
    fullPage: true,
  });
});

test("language changes UI, preserves entered text and persists only preference", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "输入你的税务问题" })
    .fill("原始草稿");
  await page.getByRole("button", { name: "Switch to English" }).click();
  await expect(
    page.getByRole("textbox", { name: "Enter your tax question" }),
  ).toHaveValue("原始草稿");
  await expect(
    page.getByRole("heading", { name: "Clarity for your tax questions." }),
  ).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator("body")).not.toContainText(
    /demo|preview|fictional|jurisdiction/i,
  );
  await page.screenshot({
    path: "test-results/minimal-english.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByRole("status")).toContainText("has not been sent");
  await page.reload();
  await expect(
    page.getByRole("textbox", { name: "Enter your tax question" }),
  ).toHaveValue("");
  await expect(page.locator(".message")).toHaveCount(0);
  expect(await page.evaluate(() => ({ ...localStorage }))).toEqual({
    "asiatax.language": "en",
  });
});

test("Chinese composition and Shift Enter do not submit prematurely", async ({
  page,
}) => {
  await page.goto("/");
  const input = page.getByRole("textbox", { name: "输入你的税务问题" });
  await input.fill("税务问题");
  await input.dispatchEvent("compositionstart");
  await input.press("Enter");
  await expect(page.locator(".message")).toHaveCount(0);
  await input.dispatchEvent("compositionend");
  await input.press("Shift+Enter");
  await expect(page.locator(".message")).toHaveCount(0);
  await input.press("Enter");
  await expect(page.locator(".message")).toHaveCount(1);
});

test("mobile dialogs trap focus and restore it on dismissal", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.screenshot({
    path: "test-results/minimal-mobile.png",
    fullPage: true,
  });
  const menu = page.getByRole("button", { name: "打开案例导航" });
  await menu.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(menu).toBeFocused();
  const sources = page.getByRole("button", { name: "法规资料", exact: true });
  await sources.click();
  await expect(page.getByRole("button", { name: "关闭详情" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(page.locator(".source-metadata summary")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "关闭详情" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(sources).toBeFocused();
});

test("English mobile home and forms fit without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Switch to English" }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Open case details" }).click();
  await expect(page.getByLabel("Taxpayer", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save facts" })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.getByRole("dialog")).not.toContainText(/[\u4e00-\u9fff]/);
});
