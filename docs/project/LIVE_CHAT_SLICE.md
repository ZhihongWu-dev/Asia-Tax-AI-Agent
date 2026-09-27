# 网页研究链路 · 实现与验证

日期：2026-09-27。范围是用户批准的第一轮接线：提问、追问、事实确认、现有规则分析和案件恢复；并非完整 PRD 或 L1 验收。

## 已实现

- FastAPI 案件、消息、事实修改、确认、分析接口；前端真实调用这些接口。
- 模型适配器使用根目录 `.env` 的 `FSIE_MODEL_BASE_URL`、`FSIE_MODEL_API_KEY`、`FSIE_MODEL_NAME`。每次请求重新加载配置，填好密钥后无需重启。
- 模型只提出候选事实，经过字段、选项、数值范围和日期校验；不能提交专家批准状态或改变工作流。
- 后端根据已知信息选择核心追问；显式未知不重复询问，冲突要求手工修订。后续字段仍可在事实卡补充。当前追问是确定性核心访谈，不是覆盖全部规则依赖的完整动态访谈引擎。
- 用户确认后保存事实快照，再调用已有规则引擎；现有 5 个业务节点、人工门槛和 5 个未实现节点分别显示。允许对不完整但无冲突的事实执行部分研究，保留阻断项。
- 消息、事实修订、确认快照、规则包快照/哈希、来源清单哈希与来源记录、分析历史持久化；修改事实或补充消息使旧分析失效。
- 乐观版本比较阻止旧页面覆盖新事实；操作幂等键使响应丢失后的同次重试不会重复保存消息或结果。模型调用失败不改变已保存案件，输入保留在当前页面。
- 原文检索沿用已实现的规则条文定位方式；知识数据库不可用时返回官方索引链接并明确未取得原文，不生成替代引用。
- 前端中英文、移动布局、加载/失败/重试、确认后展示结果、刷新恢复已连接。

## 运行

本地首次配置：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
cd apps/web
npm ci
npm run build
cd ../..
.venv/Scripts/python.exe scripts/run_chat.py
```

打开 <http://127.0.0.1:8000>。API 同时提供构建好的前端，无需另开 Vite。开发时可额外运行 `apps/web` 下的 `npm run dev`，打开 <http://127.0.0.1:5173>；该页面通过同源 `/api` 代理到 8000。修改前端后需重建才能更新 8000 的静态页面。

根目录 `.env` 填写 `FSIE_MODEL_API_KEY`。密钥不能加 `VITE_` 前缀，也不能粘贴到聊天或提交 Git。模型连接错误只向网页返回安全错误码。首次发送前用户确认仅提交合成研究资料。正常启动路径不包含测试模型或固定答案。

## 存储及部署边界

本机 PostgreSQL 未连接，因此新增会话表默认存入 gitignored 的 `data/chat.sqlite3`，复用 SQLAlchemy；不静默替换 `FSIE_DATABASE_URL` 指向的知识库。`FSIE_WEB_DATABASE_URL` 可指定独立 PostgreSQL 会话存储。切换配置不会自动搬迁既有会话；与原有 CaseFile / Fact / FactVersion 表的统一迁移仍需后续工作。

随机 HttpOnly、SameSite=Strict cookie 将浏览器工作空间隔离；写入需要同源和自定义头，Host 只允许回环域名。仅绑定 `127.0.0.1`；本轮没有账号登录、组织角色或公开部署授权。删除浏览器 cookie 后原案件仍在数据库，但不能从新工作空间访问；完整账号恢复与数据保留策略尚未实现。`/health` 已移除原始数据库连接字符串。

事实确认表示用户核对输入，不是税务专家批准。分析状态只有“待复核”，没有伪造的已批准或已归档状态。当前网页结果保存于会话库，不等于已完成报告审批和归档。

## 验证

- 独立安装本仓库 `.venv`，不再依赖旧 worktree 的解释器；`pip check` 通过。
- 后端离线测试 94 项通过（含新增 20 项）；数据库集成测试 11 项未运行。
- 浏览器 6 项通过：真实 API、临时数据库及实际规则引擎；**仅模型提取边界和知识库检索使用受控测试返回**。测试服务器只存在于 `tests/chat/serve_browser.py`，正常应用不读取测试开关。
- 前端 TypeScript/Vite 构建通过，检查过中英文首页、手机和研究结果截图。
- 本地 8000 页面、健康检查及 5173 同源 API 代理返回 200。
- 本次检查时 `FSIE_MODEL_API_KEY` 未填写，**未完成真实 DeepSeek 请求验证**。知识数据库不可用，亦未验证当前环境的真实原文检索。不能把上述测试写成完整在线模型或法规检索验收。

测试命令：

```powershell
.venv/Scripts/python.exe -m pytest -q -m "not integration"
cd apps/web
$env:PLAYWRIGHT_CHANNEL = 'chrome'
$env:FSIE_TEST_PYTHON = (Resolve-Path '../../.venv/Scripts/python.exe').Path
node node_modules/@playwright/test/cli.js test
```

CI 安装 Python 后，浏览器测试自动启动独立 API 8001 / Vite 5174，不占用正常应用或触及用户会话。

## 后续缺口

真实模型与完整知识库联调；其余 5 个业务节点；问题驱动的混合检索及适用期间过滤；完整动态问题队列；统一业务数据迁移；报告审批/退回/归档；身份认证、组织权限和恢复测试；香港税务专家验证。以上均不能由一个可用 API key 替代。

实现参考 [FastAPI 官方全栈模板](https://github.com/fastapi/full-stack-fastapi-template) 的 API 分层及同源前后端组织（MIT，未复制实现），与现有 React/Vite/FastAPI/SQLAlchemy 技术栈相符。
