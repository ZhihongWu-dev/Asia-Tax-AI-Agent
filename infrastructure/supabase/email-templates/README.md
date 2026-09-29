# Taxora 认证邮件

状态：用户已手动配置 Gmail SMTP 和英文模板，并报告实际邮件流程正常；代理未直接读取云端模板核对。后续修改这些文件不会自动更新 Supabase 邮件。

在项目 Supabase Dashboard 的 Authentication 邮件模板设置中，分别复制整个 HTML 文件到对应模板，并保存标题：

| 模板 | 文件 | Subject |
| --- | --- | --- |
| Confirm sign up | confirm-signup.html | Taxora — Confirm your email |
| Reset password | reset-password.html | Taxora — Reset your password |

保留 `{{ .ConfirmationURL }}`，不要替换为本地网址或固定链接。现有前端依赖标准验证回调，未改为 OTP 或 PKCE。

采用内联样式、表格布局和文字品牌，不依赖外部图片、域名、脚本或网络字体。邮件统一使用英文，不会自动跟随前端语言切换。模板只调整正文与标题；发件人名称在 SMTP Settings 中设为 Taxora。控制台要求先配置自定义 SMTP 才能编辑模板。

保存前备份现有模板；保存后用自己的测试账号分别验证注册、找回密码、链接失效提示，以及手机邮箱显示。不要在仓库保存真实验证链接。

参考 Supabase 官方仓库及文档的变量约定，自行编写 HTML，未复制第三方设计或引入依赖：
- https://github.com/supabase/auth/blob/master/internal/mailer/templatemailer/templatemailer.go
- https://supabase.com/docs/guides/auth/auth-email-templates
- https://supabase.com/docs/guides/local-development/customizing-email-templates
