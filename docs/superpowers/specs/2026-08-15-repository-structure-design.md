# Asia Tax AI Agent 仓库结构设计

| 项目 | 内容 |
|---|---|
| 文档状态 | 用户已确认，按设计实施 |
| 日期 | 2026-08-15 |
| 目标分支 | `main` |

## 1. 目标

本次只建立文档优先、可继续扩展的仓库框架。仓库需要让新参与者快速理解项目目标、当前阶段、核心文档位置和未来代码边界，但不创建没有实际功能的 Python、前端、数据库或部署工程。

## 2. 设计原则

- 香港 FSIE 是当前深度 MVP；中国内地、日本和韩国是后续东亚扩展范围；
- 产品、技术、项目管理和审查记录分开存放；
- 未来代码目录只用说明文件定义职责，不预先锁定尚未实施的工程结构；
- 不提交客户资料、密钥、环境变量、临时渲染文件或本地审查产物；
- 本次只移动用户指定的四份文档，其他已有文件和未提交改动保持原状；
- 不在未获得用户选择的情况下添加开源许可证。

## 3. 目标结构

```text
Asia-Tax-AI-Agent/
├── README.md
├── .gitignore
├── docs/
│   ├── README.md
│   ├── product/
│   │   └── PRD.md
│   ├── architecture/
│   │   └── TECHNICAL_ROADMAP.md
│   ├── project/
│   │   └── PROJECT_PLAN_2026.md
│   ├── reviews/
│   │   └── 2026-08-15-prd-roadmap-project-plan-plain-language-review.md
│   └── superpowers/specs/
│       └── existing design records
├── apps/
│   └── README.md
├── packages/
│   └── README.md
├── knowledge/
│   └── README.md
├── tests/
│   └── README.md
├── scripts/
│   └── README.md
└── infrastructure/
    └── README.md
```

Git 不追踪空目录，因此每个未来代码目录使用 `README.md` 说明职责，而不是使用缺乏语义的 `.gitkeep`。

## 4. 文件职责

### 根目录 README

根目录 README 说明项目愿景、当前交付等级、地区范围、核心文档入口、仓库结构、开发状态和资料安全边界。它不宣称系统已经实现，也不把研究原型描述为客户可用产品。

### 文档目录

- `docs/product/`：产品范围、用户、需求和验收标准；
- `docs/architecture/`：技术架构、数据边界、安全基线和技术路线；
- `docs/project/`：时间、资源、负责人、依赖和里程碑；
- `docs/reviews/`：审查报告、批准记录和回归检查结果；
- `docs/superpowers/specs/`：已有设计过程记录，暂不迁移或重写。

### 未来代码目录

- `apps/`：未来可部署应用，例如 Web 工作台和 API；
- `packages/`：未来可复用模块，例如规则、检索、评测和共享类型；
- `knowledge/`：可公开并允许版本管理的资料清单、标注定义和规则元数据；
- `tests/`：自动化测试、评测入口和测试数据使用规则；
- `scripts/`：可重复执行的数据处理、检查和开发脚本；
- `infrastructure/`：未来部署、数据库和环境配置；当前不创建实际基础设施文件。

## 5. 四份文件的移动规则

| 当前路径 | 目标路径 |
|---|---|
| `docs/PRD.md` | `docs/product/PRD.md` |
| `docs/TECHNICAL_ROADMAP.md` | `docs/architecture/TECHNICAL_ROADMAP.md` |
| `docs/PROJECT_PLAN_2026.md` | `docs/project/PROJECT_PLAN_2026.md` |
| `docs/reviews/2026-08-15-prd-roadmap-project-plan-plain-language-review.md` | 保持原路径 |

移动后需要修复三份核心文档和根目录 README 中的相对链接。审查报告继续使用稳定文件名，以保留日期和审查对象。

## 6. `.gitignore` 边界

基础忽略规则覆盖：

- `.env`、密钥和本地环境文件，但允许提交 `.env.example`；
- Python、Node.js、测试、构建和编辑器产生的缓存；
- 本地虚拟环境、日志、临时文件和操作系统文件；
- `.codex-doc-review/` 等本地文档渲染与审查产物；
- `knowledge/**/raw/` 和 `data/` 等可能包含受限原始资料的目录。

`.gitignore` 只是误提交保护，不能代替客户数据和秘密信息的访问控制。

## 7. Git 整合方式

远端默认分支为 `main`，当前只有初始 README；本地文档历史位于 `master`，两者没有共同提交祖先。实施时保留双方历史，通过非强制方式整合远端初始提交，解决 README 内容后将整理结果推送到 `main`。禁止使用强制推送覆盖远端。

本次提交范围包括：仓库框架说明文件、基础 `.gitignore`、更新后的根目录 README、四份指定文档及其路径调整和链接修复。现有本地审查缓存和与本次无关的未跟踪设计文件不进入提交。

## 8. 验收标准

- Git 能追踪目标结构中的每个目录，且每个说明文件表达明确职责；
- 根目录 README 能直接导航到四份指定文档；
- 四份文档移动后内部链接有效，版本按正式 Git 发布规则更新；
- 文档确定性扫描、相对链接检查和 `git diff --check` 全部通过；
- 提交中不存在 `.env`、密钥、客户数据、原始受限资料或 `.codex-doc-review/`；
- 远端 `main` 通过普通快进推送更新，不进行强制推送。
