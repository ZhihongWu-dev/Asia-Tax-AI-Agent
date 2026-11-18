# Taxrora 云端部署

网站：https://taxrora.onrender.com

## 团队更新流程

### 当前 Li 与所得税集成交付

本次工作先交付到 `Zhihong-Wu` 并进行线上验收，验收通过后再合入
`main`。下方常规流程描述现有生产部署，不表示本次集成已经发布。
仓库 `render.yaml` 的 web 和 worker 仍指向 `main`；仅推送
`Zhihong-Wu` 不会将该版本部署到生产网站。

验收环境必须明确选择 `Zhihong-Wu` 的同一个已测试提交作为 web 和
worker 的版本，使用同一案例队列数据库和独立的法规只读账号。
按照 [worker 部署说明](PLANNING_WORKER_DEPLOYMENT.md) 先检查数据库迁移、
法规版本和 `--check`，再执行真实规划、双账号隔离及重启恢复验收。
记录实际部署的提交号及测试结果后，才能将已验收版本推广到 `main`。
本说明没有创建服务、改变现有部署分支或执行数据库迁移。

独立验收配置现位于仓库根目录 `render.acceptance.yaml`。创建 Blueprint 时
明确选择此路径和 `Zhihong-Wu` 分支；它定义独立的
`taxrora-acceptance` 与 `taxrora-acceptance-worker`，两者均关闭自动部署。
后台任务使用 `1c-2g` 付费规格，配置文件本身不会创建或收费；容量仍需实测。
网页和 worker 必须手动部署同一个已审核提交，不能仅凭分支名认定版本一致。

首次设置 `FSIE_AUTH_SITE_URL` 为实际验收站点的 HTTPS 地址，并在认证项目
配置对应回调地址。模型的 `FSIE_MODEL_BASE_URL`、`FSIE_MODEL_API_KEY`、
`FSIE_MODEL_NAME` 通过托管环境填写。案例数据库使用隔离的验收数据库，
worker 从验收 web 引用相同连接；法规库使用专用只读角色。不要给任一服务
单独设置不同的 `FSIE_WEB_DATABASE_URL`，否则会绕过共享案例数据库设置。
应用配置前先完成数据库迁移和法规接纳检查，再按上述顺序执行真实验收。

配置已用 [Render 官方 Schema](https://render.com/schema/render.yaml.json)
进行结构校验，并检查目标分支、关闭自动部署、独立服务名和队列连接引用。
字段和自定义路径依据 [Blueprint 文档](https://render.com/docs/blueprint-spec)
及 [Render 官方配置参考](https://github.com/render-oss/skills/blob/main/skills/render-blueprints/references/field-reference.md)；
未引入第三方代码或依赖。此校验不证明已部署或业务验收通过。

### 常规生产更新

1. 拉取最新 main，在自己的功能分支开发和测试。
2. 推送功能分支，通过 PR 合并到 main。
3. Render 监听 main 的提交，自动构建并部署；在服务 Deploys 页面检查结果。
4. 部署成功后检查网站。构建失败时查看日志并修复，不代表新版本已上线。

Render 服务名为 taxrora，使用 Free 方案，自动部署设置为 On Commit。
GitHub 来源使用 Render App 授权的 `ZhihongWu-dev/Asia-Tax-AI-Agent`，而非仅填写公开仓库 URL；App 授权中必须包含此仓库，才能接收推送事件。
构建命令：`bash scripts/render_build.sh`。
启动命令：`uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT --workers 1`。
健康检查：`/health`。

## 配置与边界

密钥和数据库连接在 Render Environment 中维护；不要提交 .env。
启动入口已统一：本地 `python scripts/run_chat.py`、兼容入口 `python -m scripts.run_combined`、Render 的 uvicorn 命令均进入同一 API 生命周期。默认配置在 `config/runtime.json`：hybrid + dynamic tools + combined。Render 构建时安装固定版本 tax engine 依赖；本地首次运行先执行 `python scripts/install_tax_engine_release.py`。

配置优先级：进程环境变量 > 本地 .env > config/runtime.json。认证地址、HTTPS cookie、端口因环境而异，业务开关默认一致。combined 模式自动启动仅监听本机的只读资料服务、生成临时令牌，并在退出时回收；资料缺失或校验失败会阻止启动，不会悄悄切回旧模式。

`/health` 返回提交号和实际业务开关，不返回密钥或资料服务令牌。资料子进程退出时健康检查返回 503。内部知识 API 使用随机本机端口，不需要公开 8010。

接通组件不代表全部场景已完成业务验收。现有 CNY 限制、未解决的引用和专业复核要求继续有效。
macOS 如需系统证书，可用 `python scripts/install_tax_engine_release.py --system-trust`；项目的 macOS 依赖已包含 truststore。

历史 deploy/taxrora-current-ui 和 deploy/taxrora-free-demo 分支不再是线上发布来源。

## 回滚

在 Render 的部署历史选择已验证版本回滚。回滚后检查自动部署开关；必要时先暂停自动部署，再在 main 上通过 revert 修复，验证后恢复 On Commit。
