import { test, expect } from "@playwright/test";

for (const failedCallback of [false, true]) {
  test(`expired link restores login and email resend (${failedCallback ? "callback" : "fragment"})`, async ({ page }) => {
    await page.route("**/api/auth/session", route => route.fulfill({ json: { configured: true, user: null } }));
    await page.route("**/api/auth/callback", route => route.fulfill({ status: 401, json: { detail: "auth_invalid" } }));
    await page.goto(failedCallback ? "/?reset=1#access_token=expired-token&refresh_token=expired-refresh&type=recovery" : "/?reset=1#error=access_denied&error_code=otp_expired");
    await expect(page.getByRole("alert")).toContainText("验证链接已失效");
    await expect(page.getByRole("button", { name: "登录", exact: true })).toBeEnabled();
    expect(page.url()).not.toMatch(/reset=|access_token=|error=/);
    await page.getByRole("button", { name: "重新发送验证邮件", exact: true }).click();
    await expect(page.getByLabel("密码", { exact: true })).toHaveCount(0);
    await page.getByLabel("邮箱", { exact: true }).fill("person@example.test");
    let requests = 0;
    await page.route("**/api/auth/resend", async route => {
      requests++;
      expect(route.request().postDataJSON()).toEqual({ email: "person@example.test" });
      await route.fulfill({ json: { status: "check_email" } });
    });
    await page.clock.install();
    await page.getByRole("button", { name: "重新发送验证邮件", exact: true }).click();
    await expect(page.getByRole("heading", { name: "请查看邮箱" })).toBeVisible();
    await expect(page.getByRole("button", { name: /秒后可重发/ })).toBeDisabled();
    expect(requests).toBe(1);
    await page.clock.fastForward(61000);
    await expect(page.getByRole("button", { name: "重新发送验证邮件", exact: true })).toBeEnabled();
    await page.route("**/api/auth/resend", route => route.fulfill({ status: 429, json: { detail: "auth_rate_limited" } }));
    await page.getByRole("button", { name: "重新发送验证邮件", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText("请求较频繁");
    await expect(page.getByRole("button", { name: /秒后可重发/ })).toBeDisabled();
    await page.getByRole("button", { name: "返回登录" }).click();
    await expect(page.getByRole("button", { name: "登录", exact: true })).toBeEnabled();
  });
}

test("unverified login offers resend and provider failure remains retryable", async ({ page }) => {
  await page.route("**/api/auth/session", route => route.fulfill({ json: { configured: true, user: null } }));
  await page.route("**/api/auth/login", route => route.fulfill({ status: 401, json: { detail: "email_not_confirmed" } }));
  await page.route("**/api/auth/resend", route => route.fulfill({ status: 503, json: { detail: "auth_unavailable" } }));
  await page.goto("/");
  await page.getByLabel("邮箱", { exact: true }).fill("person@example.test");
  await page.getByLabel("密码", { exact: true }).fill("password123");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.getByRole("button", { name: "重新发送验证邮件", exact: true }).click();
  await expect(page.getByLabel("邮箱", { exact: true })).toHaveValue("person@example.test");
  await page.getByRole("button", { name: "Switch to English" }).click();
  await page.getByRole("button", { name: "Resend verification email", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Unable to complete");
  await expect(page.getByRole("button", { name: "Resend verification email", exact: true })).toBeEnabled();
});

test("email screens validate input, show safe errors and confirmation", async ({ page }) => {
  await page.route("**/api/auth/session", route => route.fulfill({ json: { configured: true, user: null } }));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "欢迎回来" })).toBeVisible();
  await expect(page.locator(".auth-page")).toContainText("TAXORA");
  await page.screenshot({ path: "test-results/taxora-login.png", fullPage: true, animations: "disabled" });
  await page.getByRole("button", { name: "创建账号", exact: true }).click();
  await page.getByLabel("邮箱", { exact: true }).fill("person@example.test");
  await page.getByLabel("密码", { exact: true }).fill("password123");
  await page.getByLabel("确认密码", { exact: true }).fill("different123");
  await page.getByRole("button", { name: "创建账号", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("不一致");
  await page.getByLabel("确认密码", { exact: true }).fill("password123");
  await page.route("**/api/auth/signup", route => route.fulfill({ json: { status: "check_email" } }));
  await page.getByRole("button", { name: "创建账号", exact: true }).click();
  await expect(page.getByRole("heading", { name: "请查看邮箱" })).toBeVisible();
  await page.getByRole("button", { name: "返回登录" }).click();
  await page.route("**/api/auth/login", route => route.fulfill({ status: 401, json: { detail: "auth_invalid" } }));
  await page.getByLabel("密码", { exact: true }).fill("wrongpass");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("邮箱或密码不正确");
  await page.getByRole("button", { name: "忘记密码？" }).click();
  await page.route("**/api/auth/recover", route => route.fulfill({ json: { status: "check_email" } }));
  await page.getByRole("button", { name: "发送重置邮件" }).click();
  await expect(page.getByRole("heading", { name: "请查看邮箱" })).toBeVisible();
});

test("mobile auth and English fit without overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/auth/session", route => route.fulfill({ json: { configured: true, user: null } }));
  await page.goto("/");
  await page.getByRole("button", { name: "Switch to English" }).click();
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByLabel("Confirm password")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/taxora-signup-mobile.png", fullPage: true, animations: "disabled" });
});

test("verification callback scrubs tokens and recovery opens password form", async ({ page }) => {
  const user = { id: "test-user", email: "person@example.test" };
  await page.route("**/api/auth/session", route => route.fulfill({ json: { configured: true, user } }));
  await page.route("**/api/auth/callback", route => route.fulfill({ json: { user } }));
  await page.route("**/api/auth/password", route => route.fulfill({ json: { status: "updated" } }));
  await page.goto("/?reset=1#access_token=fixture-token&refresh_token=fixture-refresh&type=recovery");
  await expect(page.getByRole("heading", { name: "设置新密码" })).toBeVisible();
  expect(page.url()).not.toContain("access_token");
  await page.getByLabel("密码", { exact: true }).fill("newpassword123");
  await page.getByLabel("确认密码", { exact: true }).fill("newpassword123");
  await page.getByRole("button", { name: "保存新密码" }).click();
  await expect(page.locator(".app-shell")).toBeVisible();
});
