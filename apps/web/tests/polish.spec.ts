import { test, expect, type Page } from "@playwright/test";

async function start(page: Page) {
  await page.addInitScript(() => localStorage.setItem("asiatax.language", "en"));
  await page.goto("/");
  await expect(page.locator(".app-shell")).toBeVisible();
}
async function send(page: Page, text: string) {
  const input = page.getByRole("textbox", { name: "Enter your tax question" });
  await input.fill(text); await input.press("Enter");
  if (await page.locator(".data-consent").isVisible()) {
    await page.locator(".data-consent input").check(); await input.press("Enter");
  }
}

test("markdown and copy are safe and history can be renamed archived and restored", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await start(page); await send(page, "MARKDOWN_TEST");
  await expect(page.getByRole("heading", { name: "Summary", exact: true })).toBeVisible();
  await expect(page.locator(".answer-table td")).toHaveCount(2);
  await expect(page.locator('.markdown-answer script, .markdown-answer a[href^="javascript:"]')).toHaveCount(0);
  await page.getByRole("button", { name: "Copy answer", exact: true }).hover();
  await expect(page.getByRole("tooltip")).toHaveText("Copy answer");
  await expect(page.getByRole("button", { name: "Copy answer", exact: true })).toHaveText("");
  await page.getByRole("button", { name: "Copy answer", exact: true }).click();
  await expect(page.getByRole("button", { name: "Copied", exact: true })).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain("## Summary");
  await page.getByRole("button", { name: "More options MARKDOWN_TEST", exact: true }).click();
  await expect(page.getByRole("menuitem", { name: "Rename", exact: true })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("menuitem", { name: "Archive", exact: true })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("menu")).toHaveCount(0);
  await page.getByRole("button", { name: "More options MARKDOWN_TEST", exact: true }).click();
  await page.getByRole("menuitem", { name: "Rename", exact: true }).click();
  await page.getByRole("textbox", { name: "Chat title" }).fill("My research");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.locator(".case-item")).toContainText("My research");
  await page.getByRole("button", { name: "More options My research", exact: true }).click();
  await page.getByRole("menuitem", { name: "Archive", exact: true }).click();
  await expect(page.locator(".case-item")).toHaveCount(0);
  await page.getByRole("button", { name: "Archived", exact: true }).click();
  await expect(page.locator(".case-item")).toContainText("My research");
  await page.reload();
  await page.getByRole("button", { name: "Archived", exact: true }).click();
  await page.getByRole("button", { name: "More options My research", exact: true }).click();
  await page.getByRole("menuitem", { name: "Restore", exact: true }).click();
  await page.getByRole("button", { name: "Recent chats", exact: true }).click();
  await expect(page.locator(".case-item")).toContainText("My research");
  await page.screenshot({ path: "test-results/polished-answer.png", fullPage: true });
});

test("unvalidated response stays hidden and stop cancels without committing a partial turn", async ({ page }) => {
  await start(page); await send(page, "STREAM_TEST");
  await expect(page.locator(".assistant-pending")).toBeVisible();
  await expect(page.locator(".streaming-answer")).toHaveCount(0);
  await expect(page.locator(".message.assistant:not(.streaming-answer)")).toHaveCount(0);
  await page.getByRole("button", { name: "Stop generating" }).click();
  await expect(page.locator(".assistant-pending")).toHaveCount(0);
  await expect(page.getByRole("textbox", { name: "Enter your tax question" })).toHaveValue("STREAM_TEST");
  await page.reload();
  await expect(page.locator(".message.assistant")).toHaveCount(0);
  await send(page, "STREAM_TEST");
  await expect(page.locator(".assistant-pending")).toBeVisible();
  await expect(page.locator(".streaming-answer")).toHaveCount(0);
  await expect(page.locator(".message.assistant:not(.streaming-answer)")).toContainText("First live chunk and final chunk");
  await page.reload();
  await expect(page.locator(".message.assistant")).toHaveCount(1);
});

test("reading older messages is not interrupted by a new reply", async ({ page }) => {
  await start(page);
  for (let n = 0; n < 4; n++) {
    await send(page, "MARKDOWN_TEST");
    await expect(page.locator(".message.assistant")).toHaveCount(n + 1);
  }
  await send(page, "STREAM_TEST");
  await expect(page.locator(".assistant-pending")).toBeVisible();
  await page.locator(".workspace-scroll").evaluate(el => { el.scrollTop = 0; el.dispatchEvent(new Event("scroll")); });
  await expect(page.getByRole("button", { name: "Back to bottom" })).toBeVisible();
  await expect(page.locator(".message.assistant:not(.streaming-answer)")).toHaveCount(5);
  expect(await page.locator(".workspace-scroll").evaluate(el => el.scrollTop)).toBe(0);
  await page.getByRole("button", { name: "Back to bottom" }).click();
  await expect(page.getByRole("button", { name: "Back to bottom" })).toHaveCount(0);
});
