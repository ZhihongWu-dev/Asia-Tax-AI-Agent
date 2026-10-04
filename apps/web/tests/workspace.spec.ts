import { test, expect, type Page } from "@playwright/test";

test("a failed pending send preserves the next draft and retries without duplication", async ({
  page,
}) => {
  await english(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let first = true;
  await page.route("**/api/cases/*/messages", async (route) => {
    if (!first) return route.continue();
    first = false;
    await gate;
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "model_failed" }),
    });
  });
  try {
    await send(page, "Original submitted question");
    const input = page.getByRole("textbox", {
      name: "Enter your tax question",
    });
    await expect(input).toHaveValue("");
    await input.fill("A different next draft");
    release();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.locator(".delivery-failed")).toBeVisible();
    await expect(page.locator(".message.user")).toContainText(
      "Original submitted question",
    );
    await expect(page.locator(".assistant-pending")).toHaveCount(0);
    await expect(input).toHaveValue("A different next draft");
    await page.getByRole("button", { name: "Retry", exact: true }).click();
    await expect(page.locator(".message.assistant")).toHaveCount(1);
    await expect(page.locator(".message.user")).toHaveCount(1);
    await expect(page.locator(".delivery-failed")).toHaveCount(0);
    await expect(input).toHaveValue("A different next draft");
  } finally {
    release();
  }
});

test("send immediately shows the question and animated brand, preserving a new draft", async ({
  page,
}) => {
  await english(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/cases/*/messages", async (route) => {
    await gate;
    await route.continue();
  });
  try {
    await send(page, "Waiting for a synthetic reply");
    await expect(page.locator(".message.user")).toHaveText(
      "Waiting for a synthetic reply",
    );
    const input = page.getByRole("textbox", {
      name: "Enter your tax question",
    });
    await expect(input).toHaveValue("");
    await expect(page.getByRole("status", { name: "Thinking…" })).toBeVisible();
    await expect(page.locator(".assistant-pending .brand-loader-emblem rect")).toHaveCount(4);
    await expect(page.locator(".assistant-pending .brand-loader-emblem rect").first()).toHaveCSS(
      "animation-name",
      "taxora-assemble",
    );
    await page.screenshot({
      path: "test-results/pending-reply.png",
      fullPage: true, animations: "disabled",
    });
    await input.fill("My next draft");
    release();
    await expect(page.locator(".assistant-pending")).toHaveCount(0);
    await expect(page.locator(".message.assistant")).toHaveCount(1);
    await expect(page.locator(".message.user")).toHaveCount(1);
    await expect(input).toHaveValue("My next draft");
    await page.reload();
    await expect(page.locator(".message.user")).toHaveCount(1);
  } finally {
    release();
  }
});

test("natural conversation is rendered and restored without a research error", async ({
  page,
}) => {
  await english(page);
  await send(page, "你好");
  await expect(page.locator(".chat-reply")).toHaveText(
    "你好！今天想聊些什么？",
  );
  await expect(page.locator(".research-response")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Review case facts" }),
  ).toHaveCount(0);
  await send(page, "用英文再说一遍");
  await expect(page.locator(".chat-reply").last()).toHaveText(
    "Hello! What would you like to talk about today?",
  );
  await page.reload();
  await expect(page.locator(".chat-reply")).toHaveCount(2);
  await page.screenshot({
    path: "test-results/natural-chat.png",
    fullPage: true, animations: "disabled",
  });
});

test("source search, provenance and persisted research replies", async ({
  page,
}) => {
  await english(page);
  await send(page, "Case 68");
  await expect(page.locator(".research-response")).toContainText(
    "Reference excerpts are displayed with permission",
  );
  await page.locator(".research-response .knowledge-passage > summary").click();
  await expect(page.locator(".research-response")).toContainText(
    "Synthetic browser fixture: date retained.",
  );
  await expect(page.locator(".research-response")).toContainText(
    "Source content has changed",
  );
  await page.reload();
  await expect(page.locator(".research-response")).toContainText(
    "Date of ruling issued",
  );
  await page.getByRole("button", { name: "切换为中文" }).click();
  await expect(page.locator(".research-response")).toContainText(
    "仅展示已获许可的参考原文",
  );
  await page.getByRole("button", { name: "法规资料", exact: true }).click();
  await page.getByRole("textbox", { name: "检索法条与案例" }).fill("案例 68");
  await page.getByRole("button", { name: "检索", exact: true }).click();
  await expect(
    page.locator(".knowledge-search .knowledge-passage"),
  ).toHaveCount(1);
  await page.screenshot({
    path: "test-results/knowledge-search.png",
    fullPage: true, animations: "disabled",
  });
  await page.getByRole("textbox", { name: "检索法条与案例" }).fill("case 999");
  await page.getByRole("button", { name: "检索", exact: true }).click();
  await expect(page.locator(".knowledge-search")).toContainText(
    "未找到匹配资料",
  );
  await expect(
    page.locator(".knowledge-search .knowledge-passage"),
  ).toHaveCount(0);
});

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
    if (!request.url().startsWith(`http://127.0.0.1:${process.env.FSIE_TEST_WEB_PORT || "5174"}/`))
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
    fullPage: true, animations: "disabled",
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
    page.getByText("这笔收入由个人还是公司收取？", { exact: false }),
  ).toBeVisible();
  await expect(page.locator(".analysis-result")).toHaveCount(0);
  await send(page, "FOLLOW_UP");
  await expect(page.locator(".message.user")).toHaveCount(2);
  await send(page, "partial summary");
  await expect(page.locator(".message.assistant").last()).toContainText("不是完整分析");
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
    fullPage: true, animations: "disabled",
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
  await expect(page.locator(".message.assistant")).toHaveCount(1);
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
    page.getByText("本次应采用哪个值？", { exact: false }),
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
  await expect(page.locator(".message.assistant")).toHaveCount(1);
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
    fullPage: true, animations: "disabled",
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

test("guided interview asks once, records unknown, and resumes after refresh", async ({ page }) => {
  await english(page);
  await send(page, "Synthetic foreign dividend case");
  const last = page.locator(".message.assistant").last();
  await expect(last).toContainText("这笔收入由个人还是公司收取？");
  await expect(last.locator("ul")).toHaveCount(0);
  await send(page, "公司");
  await expect(last).toContainText("分析哪个地区");
  await send(page, "不知道");
  await expect(last).toContainText("继续补充其他信息、先看部分整理，还是暂停");
  const id = new URL(page.url()).hash.slice(1);
  let doc = await (await page.request.get(`/api/cases/${id}`)).json();
  expect(doc.facts.recipient_type.value).toBe("company");
  expect(doc.facts.analysis_jurisdiction.value).toBe("unknown");
  expect(doc.dialogue.partial_consent).toBeUndefined();
  await send(page, "暂停");
  await page.reload();
  await expect(last).toContainText("已暂停并保存");
  await send(page, "继续补充");
  await expect(last).toContainText("最想解决股息的哪个问题");
  doc = await (await page.request.get(`/api/cases/${id}`)).json();
  expect(doc.messages.at(-1).question.field).toBe("consultation_goal");
});
