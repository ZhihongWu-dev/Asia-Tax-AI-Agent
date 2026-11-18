import { test, expect } from "@playwright/test";

function expectSameRow(left: { x: number; y: number; width: number; height: number }, right: { x: number; y: number; width: number; height: number }) {
  const overlap = Math.min(left.y + left.height, right.y + right.height) - Math.max(left.y, right.y);
  expect(overlap).toBeGreaterThan(Math.min(left.height, right.height) / 2);
  expect(left.x + left.width).toBeLessThan(right.x);
}

test("structure guide explains each goal and keeps amount beside currency", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "结构分析", exact: true }).click();

  const goal = page.getByRole("combobox", { name: "分析目的" });
  const help = page.locator(".structure-mode-help");
  await expect(help).toContainText("现有付款及持股安排");
  await goal.selectOption("plan_structure");
  await expect(help).toContainText("尚未付款");
  await goal.selectOption("review_paid");
  await expect(help).toContainText("已经付款并缴税");

  await page.getByText("如何使用结构分析").click();
  await expect(page.getByText("保存后运行分析。", { exact: false })).toBeVisible();
  const amount = await page.getByRole("spinbutton", { name: "结构股息金额" }).boundingBox();
  const currency = await page.getByRole("combobox", { name: "结构币种" }).boundingBox();
  expect(amount).not.toBeNull();
  expect(currency).not.toBeNull();
  expectSameRow(amount!, currency!);

  await page.setViewportSize({ width: 390, height: 844 });
  const mobileAmount = await page.getByRole("spinbutton", { name: "结构股息金额" }).boundingBox();
  const mobileCurrency = await page.getByRole("combobox", { name: "结构币种" }).boundingBox();
  expect(mobileAmount).not.toBeNull();
  expect(mobileCurrency).not.toBeNull();
  expectSameRow(mobileAmount!, mobileCurrency!);
});

test("structure dates use day/month/year and help icon explains the panel", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "结构分析", exact: true }).click();
  await page.getByRole("button", { name: "结构分析有什么用途" }).hover();
  await expect(page.getByRole("tooltip")).toContainText("根据已确认的付款、持股和日期事实");

  await page.getByRole("button", { name: "载入合成示例" }).click();
  const paymentDate = page.getByRole("textbox", { name: "结构支付日期" });
  const acquisitionDate = page.getByRole("textbox", { name: "结构取得日期" });
  await expect(paymentDate).toHaveValue("11/10/2026");
  await expect(acquisitionDate).toHaveValue("01/01/2020");

  await paymentDate.fill("31/02/2026");
  await page.getByRole("button", { name: "保存结构案情" }).click();
  await expect(page.getByRole("alert")).toContainText("dd/mm/yyyy");

  await paymentDate.fill("13/10/2026");
  const requestPromise = page.waitForRequest(request => request.url().endsWith("/domain-case") && request.method() === "PUT");
  await page.getByRole("button", { name: "保存结构案情" }).click();
  const request = await requestPromise;
  const body = request.postDataJSON();
  expect(body.case_input.event.on).toBe("2026-10-13");
  expect(body.case_input.event.as_at).toBe("2026-10-13");
  expect(body.case_input.holds[0].since).toBe("2020-01-01");
});

test("structure panel saves a tax engine case, runs it, and restores the result", async ({ page }) => {
  test.skip(!process.env.FSIE_TAX_ENGINE_RELEASE_DIR, "Pinned tax engine release is required");
  await page.goto("/");
  await page.getByRole("button", { name: "结构分析", exact: true }).click();
  await page.getByRole("button", { name: "载入合成示例" }).click();
  await page.getByRole("checkbox", { name: /本次仅提交合成研究资料/ }).check();
  await page.getByRole("button", { name: "保存结构案情" }).click();
  await expect(page.getByRole("button", { name: "运行结构规划" })).toBeEnabled();
  await page.getByRole("button", { name: "运行结构规划" }).click();
  await expect(page.getByRole("region", { name: "结构分析结果" })).toContainText("候选结构", { timeout: 30000 });
  const id = page.url().split("#")[1];
  const saved = await (await page.request.get(`/api/cases/${id}`)).json();
  expect(saved.domain_case.roles.OP.loc).toBe("CN");
  expect(saved.domain_outcome.release).toMatch(/^771e452/);
  await page.reload();
  await page.getByRole("button", { name: "结构分析", exact: true }).click();
  await expect(page.getByRole("region", { name: "结构分析结果" })).toContainText("候选结构");
});

test("current structure supports unknown answer, partial frozen report and export", async ({ page }) => {
  test.skip(!process.env.FSIE_TAX_ENGINE_RELEASE_DIR, "Pinned tax engine release is required");
  await page.goto("/");
  await page.getByRole("button", { name: "结构分析", exact: true }).click();
  await page.getByRole("button", { name: "载入合成示例" }).click();
  await page.getByRole("checkbox", { name: /本次仅提交合成研究资料/ }).check();
  await page.getByRole("button", { name: "保存结构案情" }).click();
  await expect(page.getByRole("button", { name: "运行结构规划" })).toBeEnabled();
  await page.getByRole("button", { name: "运行结构规划" }).click();
  await page.getByText("单独回答或暂缓当前问题", { exact: true }).click();
  await expect(page.getByRole("button", { name: "事实未知", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "事实未知", exact: true }).click();
  await expect(page.getByRole("button", { name: "确认当前结构事实" })).toBeEnabled({ timeout: 30000 });
  await page.getByRole("button", { name: "确认当前结构事实" }).click();
  await page.getByRole("checkbox", { name: /同意按当前信息生成部分研究稿/ }).check();
  await expect(page.getByRole("button", { name: "生成合并研究稿" })).toBeEnabled();
  await page.getByRole("button", { name: "生成合并研究稿" }).click();
  const id = page.url().split("#")[1];
  await expect.poll(async () => (await (await page.request.get(`/api/cases/${id}`)).json()).analyses.length).toBe(1);
  const saved = await (await page.request.get(`/api/cases/${id}`)).json();
  const report = saved.analyses[0];
  expect(report.report_kind).toBe("current_structure");
  expect(report.report_hash).toMatch(/^[a-f0-9]{64}$/);
  expect(report.partial_output_authorized).toBe(true);
  expect(report.evidence_gate).toBe("insufficient");
  expect(Object.values(saved.canonical_fact_records).some((r: any) => r.status === "unknown")).toBe(true);
  const exported = await page.request.get(`/api/cases/${id}/analyses/${report.id}/markdown`);
  expect(exported.status()).toBe(200);
  expect(await exported.text()).toContain("合并编排研究稿");
  await page.reload();
  await expect(page.getByText("合并编排研究稿", { exact: false }).first()).toBeVisible();
});

test("engine results follow the selected language and buttons use the green palette", async ({ page }) => {
  test.skip(!process.env.FSIE_TAX_ENGINE_RELEASE_DIR, "Pinned tax engine release is required");
  await page.goto("/");
  await page.getByRole("button", { name: "结构分析", exact: true }).click();
  await page.getByRole("button", { name: "载入合成示例" }).click();
  await page.getByRole("checkbox", { name: /本次仅提交合成研究资料/ }).check();
  await page.getByRole("button", { name: "保存结构案情" }).click();
  const run = page.getByRole("button", { name: "运行结构规划" });
  await expect(run).toBeEnabled();
  await run.click();
  const result = page.locator(".structure-result");
  await expect(result).toContainText("候选结构", { timeout: 30000 });
  await page.getByRole("button", { name: "关闭详情" }).click();
  await page.getByRole("button", { name: "Switch to English" }).click();
  await page.getByRole("button", { name: "Structure analysis", exact: true }).click();
  await expect(result).toContainText("Only the stated existing structure is assessed");
  await expect(result).toContainText("Operating company");
  await expect(result).toContainText("Dividend");
  await expect(result).not.toContainText(/[\u3400-\u9fff]/);
  await expect(page.locator(".structure-question")).not.toContainText(/flow:|reinvested_in_cn/);
  await page.getByText("Answer or defer one question", { exact: true }).click();
  const primary = page.getByRole("button", { name: "Submit and recalculate" });
  await expect(primary).toHaveCSS("background-color", "rgb(36, 84, 66)");
  await expect(primary).toHaveCSS("color", "rgb(255, 255, 255)");
  const secondary = page.getByRole("button", { name: "Defer question" });
  await expect(secondary).toHaveCSS("background-color", "rgb(226, 236, 223)");
  await expect(secondary).toHaveCSS("color", "rgb(33, 75, 60)");
  await secondary.hover();
  await expect(secondary).toHaveCSS("background-color", "rgb(207, 223, 202)");
  await page.mouse.move(0, 0);
  await page.screenshot({ path: "test-results/structure-english-theme.png", fullPage: true });
  await page.reload();
  await page.getByRole("button", { name: "Structure analysis", exact: true }).click();
  await expect(page.locator(".structure-result")).not.toContainText(/[\u3400-\u9fff]/);
  await page.getByRole("button", { name: "Close details" }).click();
  await page.getByRole("button", { name: "切换为中文" }).click();
  await page.getByRole("button", { name: "结构分析", exact: true }).click();
  await expect(result).toContainText("经营公司");
  await expect(result).toContainText("股息");
  await expect(result).not.toContainText("DIVIDEND");
});
