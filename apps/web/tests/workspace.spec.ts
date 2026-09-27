import { test, expect, type Page } from "@playwright/test";

async function english(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Switch to English" }).click();
}
async function send(page: Page, text: string) {
  await page
    .getByRole("textbox", { name: "Enter your tax question" })
    .fill(text);
  await page.getByRole("button", { name: "Send message" }).click();
  const consent = page.getByRole("checkbox");
  if (await consent.isVisible()) {
    await consent.check();
    await page.getByRole("button", { name: "Send message" }).click();
  }
}

test("minimal bilingual home preserves design with a real backend", async ({
  page,
}) => {
  const external: string[] = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://127.0.0.1:5174"))
      external.push(request.url());
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "让税务问题，更清晰。" }),
  ).toBeVisible();
  await expect(page.locator("body")).not.toContainText(
    /选择地区|演示|预览|虚构|示例/,
  );
  await expect(page.getByRole("combobox")).toHaveCount(0);
  await page.screenshot({
    path: "test-results/live-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Switch to English" }).click();
  await expect(
    page.getByRole("heading", { name: "Clarity for your tax questions." }),
  ).toBeVisible();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  expect(external).toEqual([]);
});

test("intake, follow-up, explicit confirmation, real rules and refresh recovery", async ({
  page,
}) => {
  await english(page);
  await send(page, "Synthetic foreign dividend case");
  await expect(
    page.getByText("Please provide the following details to continue.", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(page.locator(".analysis-result")).toHaveCount(0);
  await send(page, "FOLLOW_UP");
  await expect(page.locator(".message.user")).toHaveCount(2);
  await page.getByRole("button", { name: "Review case facts" }).click();
  await expect(
    page.getByLabel(
      "Is the recipient part of a multinational enterprise group?",
      { exact: true },
    ),
  ).toHaveValue("yes");
  await expect(page.getByLabel("Dividend amount", { exact: true })).toHaveValue(
    "100000",
  );
  await page.getByRole("button", { name: "Confirm facts and analyze" }).click();
  await expect(page.getByRole("button", { name: "Close details" })).toHaveCount(
    0,
  );
  await expect(page.locator(".analysis-result")).toContainText(
    "Professional review required",
  );
  await page.getByText("Sources for this analysis", { exact: true }).click();
  await expect(page.locator(".analysis-result")).toContainText(
    "No legal passages retrieved",
  );
  await expect(page.locator(".analysis-result a").first()).toHaveAttribute(
    "href",
    /^https:\/\//,
  );
  await page.screenshot({
    path: "test-results/live-analysis.png",
    fullPage: true,
  });
  const url = page.url();
  await page.reload();
  await expect(page.locator(".analysis-result")).toHaveCount(1);
  expect(page.url()).toBe(url);
  await page.getByRole("button", { name: "Review case facts" }).click();
  await page.getByLabel("Dividend amount", { exact: true }).fill("");
  await page
    .getByLabel("Dividend amount", { exact: true })
    .pressSequentially("200000.50");
  await expect(page.getByLabel("Dividend amount", { exact: true })).toHaveValue(
    "200000.50",
  );
  await expect(
    page.getByRole("button", { name: "Confirm facts and analyze" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Save facts", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Save facts", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Close details" }).click();
  await expect(page.locator(".analysis-result")).toContainText("outdated");
});

test("failed model keeps input and retry creates one exchange", async ({
  page,
}) => {
  await english(page);
  await send(page, "RETRY_TEST");
  await expect(page.getByRole("alert")).toContainText("model request");
  await expect(
    page.getByRole("textbox", { name: "Enter your tax question" }),
  ).toHaveValue("RETRY_TEST");
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.locator(".message.user")).toHaveCount(1);
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(
    page.getByRole("textbox", { name: "Enter your tax question" }),
  ).toHaveValue("");
});

test("conflicts require explicit editing before confirmation", async ({
  page,
}) => {
  await english(page);
  await send(page, "CONFLICT_TEST");
  await expect(
    page.getByText("These facts conflict.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Review case facts" }).click();
  await expect(
    page.getByRole("button", { name: "Confirm facts and analyze" }),
  ).toBeDisabled();
  await page
    .getByLabel("Does the recipient carry on business in Hong Kong?", {
      exact: true,
    })
    .selectOption("yes");
  await page.getByRole("button", { name: "Save facts", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Confirm facts and analyze" }),
  ).toBeEnabled();
});

test("case and draft isolation, language changes preserve original text", async ({
  page,
}) => {
  await english(page);
  await send(page, "Alpha");
  await expect(page.locator(".message.user")).toHaveCount(1);
  await page
    .getByRole("textbox", { name: "Enter your tax question" })
    .fill("原始草稿");
  await page.locator(".new-case").click();
  await expect(
    page.getByRole("textbox", { name: "Enter your tax question" }),
  ).toHaveValue("");
  await page.getByRole("button", { name: "Alpha", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Enter your tax question" }),
  ).toHaveValue("原始草稿");
  await page.getByRole("button", { name: "切换为中文" }).click();
  await expect(
    page.getByRole("textbox", { name: "输入你的税务问题" }),
  ).toHaveValue("原始草稿");
  expect(await page.evaluate(() => ({ ...localStorage }))).toEqual({
    "asiatax.language": "zh",
  });
});

test("IME does not submit and phone dialogs trap focus without overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const input = page.getByRole("textbox", { name: "输入你的税务问题" });
  await input.fill("税务问题");
  await input.dispatchEvent("compositionstart");
  await input.press("Enter");
  await expect(page.getByRole("checkbox")).toHaveCount(0);
  await input.dispatchEvent("compositionend");
  await input.press("Shift+Enter");
  await expect(page.getByRole("checkbox")).toHaveCount(0);
  await input.fill("");
  await page.screenshot({
    path: "test-results/live-mobile.png",
    fullPage: true,
  });
  const sources = page.getByRole("button", { name: "法规资料", exact: true });
  await sources.click();
  await expect(page.getByRole("button", { name: "关闭详情" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(page.locator(".source-metadata summary")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(sources).toBeFocused();
  await page.getByRole("button", { name: "Switch to English" }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
