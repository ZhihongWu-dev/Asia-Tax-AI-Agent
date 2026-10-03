# Taxora 税衡 邮箱账号与云端数据

产品名称更新为 Taxora，使用已确认的 T 形 Logo。登录注册、找回密码、设置新密码、中英文和手机布局已接入。内部包名及兼容请求头暂时沿用旧名称。

## 本机配置

在项目 `.env` 填写（不要提交）：

```dotenv
FSIE_AUTH_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
FSIE_AUTH_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_OR_ANON_KEY
FSIE_AUTH_SITE_URL=http://127.0.0.1:8000
FSIE_AUTH_SECURE_COOKIE=false
```

项目控制台的 Connect 或 Settings / API Keys 可获取 Project URL 和 Publishable key（旧项目可用 anon key）。不要使用 service_role 或 secret key。密码由 Supabase Auth 管理，应用数据库不存密码。

Supabase Authentication 配置：

1. 启用 Email 登录及邮箱确认。
2. URL Configuration 中 Site URL 设为 `http://127.0.0.1:8000`。
3. Redirect URLs 加入 `http://127.0.0.1:8000/` 和 `http://127.0.0.1:8000/?reset=1`。
4. 保留标准邮箱模板的 ConfirmationURL；本版回调接收默认邮件流程的令牌片段，立即从地址栏清除后交后端验证。不支持任意自定义 OTP/PKCE 模板。
5. 正式给团队发注册或重置邮件前配置 Custom SMTP。默认发送服务限制收件人及频率；请用实际邮箱验证收信，不以页面提示成功代替邮件验收。

开发端口 5173 也需作为实际使用地址统一配置，避免认证回调落到另一来源。HTTPS 部署设 `FSIE_AUTH_SECURE_COOKIE=true`，同时配置部署域名、回调白名单和 API TrustedHost；当前启动脚本仅绑定本机。

## 用户数据如何保存

- 浏览器通过同源后端调用 Supabase Auth。access/refresh token 放在 HttpOnly、SameSite=Lax Cookie，不通过 localStorage 保存；登录响应不返回令牌。
- 后端向配置的 Supabase 项目验证身份，只有邮箱已确认的用户可访问案件、检索与分析接口。每次读取或修改都使用服务端确定的 `user:<UUID>` 作为 owner，不接受客户端提交 owner。
- 现有 `chat_cases` 表无需变更结构，新案件保存到已有云库。相同账号登录其他浏览器可获取同一案件集。
- 旧浏览器 cookie owner 的案件保留原状，不自动认领到任何账号；后续如需迁移，单独确认归属再迁移。
- 前端退出后卸载工作空间，清除内存中的案件与草稿，并通知其他同源标签页重新加载。密码重置及登录不会自动授予专业复核权限。
- 服务端数据库账号仍是受信任账号；本次账号隔离在后端执行，不等同于已完成数据库最小权限、组织协作或 L1 数据审批。

## 验证

2026-09-29 更新：失效邮件回调清理令牌片段及 reset 参数后，仍检查认证配置，允许返回登录。注册后的收信页、未验证邮箱登录提示及失效链接提示均可进入重发验证邮件流程。`POST /api/auth/resend` 仅接受邮箱，固定使用 signup 类型和服务端配置的回跳地址；账号不存在或已验证时返回相同提示。前端提供 60 秒等待倒计时，服务端限流由 Supabase 执行，429 和发送服务故障保留可操作提示。倒计时是界面节流，不代表 SMTP 一定已投递或服务端限流一定已解除。

离线测试覆盖身份校验、未登录拒绝访问、跨账号读写隔离、同账号会话持久化、密码校验、刷新和退出。浏览器测试使用隔离数据及认证替身，覆盖页面、邮箱提示、恢复回调、移动端与既有聊天流程；不代表已完成真实邮件投递验收。

真实云端脚本 `scripts/verify_cloud_chat.py` 现在要求进程环境变量 `TAXORA_SMOKE_EMAIL` 和 `TAXORA_SMOKE_PASSWORD`，使用已验证的专用测试账号。仅创建合成案件，并仅清理脚本自己创建的案件；禁止把凭据写入测试文件。

当前配置是否可用以本机 `/api/auth/session` 为准。凭据缺失时显示配置提示，不回退匿名登录。

## 官方参考

- [Supabase 邮箱密码认证](https://supabase.com/docs/guides/auth/passwords)
- [身份验证](https://supabase.com/docs/reference/javascript/auth-getuser)
- [邮件配置](https://supabase.com/docs/guides/auth/auth-smtp)

认证采用 Supabase HTTP API，保留现有 FastAPI 同源接口，不引入浏览器认证 SDK；参考官方实现和近期会话刷新修复记录，未复制第三方 UI 或代码。
