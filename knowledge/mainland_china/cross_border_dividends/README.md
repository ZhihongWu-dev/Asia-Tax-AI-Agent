# 中国内地：跨境股息官方来源目录

当前等级为 `source-catalog baseline`，核对日期 2026-10-03。五个已声明主题及七个官方来源见 `source_manifest.json`。目录记录来源、地区、语言、主题、适用日期、版本说明、覆盖缺口和专业核验状态；日期未知时明确留空并在版本说明中解释。所有记录均为 `unverified`。

先执行 `python -m alembic upgrade head`，再执行 `python -m packages.knowledge_pipeline.catalog` 写入云端 PostgreSQL。重复运行会按 `source_id` 更新，不会新增重复行。可用 `python -m packages.knowledge_pipeline.catalog --search dividend_withholding` 查找目录项；其他主题 ID 见清单。本包不抓取全文、不生成法条片段，也不接入香港 FSIE 聊天检索。内地记录的 `l0_in_scope=false`，避免把目录误当成可引用的香港原文。

官方页面已在 2026-10-03 通过网页检索逐一核对；税务总局站点对本机自动 HTTP 请求返回 403，因此数据库中的 `http_status` 留空，未声称机器抓取或 hash 校验通过。后续发布前应在浏览器检查目录链接、复核修订与各议定书，并由内地税务专家确认材料的现行适用性。特别是基础安排与第五议定书并不构成一份完整整合文本，第一至第四议定书尚待整理。

此目录只能帮助定位官方依据，不能凭目录直接计算税率、判断受益所有人资格或给出个案申报方案。
