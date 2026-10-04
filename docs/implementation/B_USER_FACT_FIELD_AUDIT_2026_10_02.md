# 用户侧字段核查表（GitHub 基线 + B 扩展）

核查日期：2026-10-02。原仓库 43 字段，B 聊天目录开放原有 42 个候选字段（排除 expert_decision_status），另有 11 个 B 字段，共 53 项；这不是要求用户逐项填完的表单。

原始字段来自 `Zhihong-Wu@7054c45`，与 `main@8974ee7` 的字段词典及规则一致。具体来源见 [追问设计](B_GUIDED_INTAKE_DESIGN_2026_10_02.md)。

## 原有字段逐项对应

“用户侧”包含用户描述与其授权材料，不能由 C 的公开法规或参考案例补造。“判断陈述”只能保存为候选，用户确认事实不等于专业批准。“非入口必需”仍可能在具体节点阻断。

| 字段 | 含义 | 从谁获取/如何使用 | 原规则 required_facts | 候选场景识别是否必需 |
|---|---|---|---|---|
| `entity_hk_business_status` | 收款实体是否在香港经营某行业、专业或业务 | 用户侧事实/材料；没有则保持缺项 | scope | 否 |
| `mne_group_status` | 是否属于 FSIE 覆盖的跨国企业集团（MNE）实体 | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | scope | 否 |
| `regulated_financial_entity_status` | 是否属受规管金融实体的排除情形（判断链第4步） | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | 未列入当前 6 条规则的必需字段 | 否 |
| `pure_equity_holding_entity_status` | 是否纯股权持有实体，决定适用简化经济实质标准 | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | economic_substance | 否 |
| `entity_tax_residency` | 实体税务居民地 | 用户侧事实/材料；没有则保持缺项 | 未列入当前 6 条规则的必需字段 | 否 |
| `income_type` | 收入类型；L0 纵切仅处理 dividend | 用户侧事实/材料；没有则保持缺项 | scope, income_characterisation | 是 |
| `income_legal_character` | 是否构成本方案意义上的境外来源股息 | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | income_characterisation | 否 |
| `payer_entity` | 派息的被投资实体 | 用户侧事实/材料；没有则保持缺项 | income_characterisation | 否 |
| `dividend_amount` | 股息金额（数值，币种见配对字段） | 用户侧事实/材料；没有则保持缺项 | 未列入当前 6 条规则的必需字段 | 否 |
| `dividend_currency` | 股息币种 ISO 4217 | 用户侧事实/材料；没有则保持缺项 | 未列入当前 6 条规则的必需字段 | 否 |
| `accrual_date` | 收入累算日期，用于选择生效规则版本 | 用户侧事实/材料；没有则保持缺项 | scope, income_characterisation | 否 |
| `underlying_profit_period` | 股息对应的底层利润期间 | 用户侧事实/材料；没有则保持缺项 | income_characterisation | 否 |
| `source_analysis` | 收入来源地分析 | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | income_characterisation | 否 |
| `receipt_location` | 股息是否在香港收取或视为在港收取 | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | receipt | 否 |
| `receipt_date` | 实际或视为收取日期 | 用户侧事实/材料；没有则保持缺项 | receipt | 否 |
| `bank_or_account_path` | 收款账户、现金池与资金流转路径（统一替代旧名 receipt_account） | 用户侧事实/材料；没有则保持缺项 | receipt | 否 |
| `set_off_or_clearing_arrangement` | 是否存在抵销、结算等视为收取安排 | 用户侧事实/材料；没有则保持缺项 | receipt | 否 |
| `cash_pool_arrangement` | 是否涉及集团现金池 | 用户侧事实/材料；没有则保持缺项 | 未列入当前 6 条规则的必需字段 | 否 |
| `payment_on_behalf_arrangement` | 是否存在代付安排 | 用户侧事实/材料；没有则保持缺项 | 未列入当前 6 条规则的必需字段 | 否 |
| `direct_or_indirect_holding` | 直接或间接持股关系 | 用户侧事实/材料；没有则保持缺项 | participation_basic | 否 |
| `investee_entity` | 被投资实体（与 payer_entity 相互核对） | 用户侧事实/材料；没有则保持缺项 | participation_basic | 否 |
| `holding_percentage_pct` | 持股百分比（0-100），统一替代旧名 holding_percentage | 用户侧事实/材料；没有则保持缺项 | participation_basic | 否 |
| `continuous_holding_period_months` | 收入累算前连续持股月数 | 用户侧事实/材料；没有则保持缺项 | participation_basic | 否 |
| `acquisition_date` | 取得股权日期，用于核算连续持有期 | 用户侧事实/材料；没有则保持缺项 | 未列入当前 6 条规则的必需字段 | 否 |
| `beneficial_owner_status` | 是否为受益所有人 | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | 未列入当前 6 条规则的必需字段 | 否 |
| `foreign_tax_on_dividend_or_underlying_profit` | 股息或其底层利润在境外是否被征合资格类似税项 | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | participation_basic | 否 |
| `foreign_nominal_tax_rate_pct` | 境外名义税率，与 15% 参考税率比较 | 用户陈述 + C 对应税种/期间的依据；不能与股息预提税率混用 | 未列入当前 6 条规则的必需字段 | 否 |
| `foreign_tax_jurisdiction` | 境外征税地 | 用户侧事实/材料；没有则保持缺项 | 未列入当前 6 条规则的必需字段 | 否 |
| `underlying_tax_deductible_status` | 底层利润税款在被投方所在地是否可税前扣除（反混合错配） | 用户侧事实/材料；没有则保持缺项 | 未列入当前 6 条规则的必需字段 | 否 |
| `foreign_tax_credit_available` | 参股豁免不适用时是否可转境外税收抵免（switch-over） | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | 未列入当前 6 条规则的必需字段 | 否 |
| `entity_activity_profile` | 在港进行的核心创收活动描述 | 用户侧事实/材料；没有则保持缺项 | economic_substance | 否 |
| `hk_adequate_employees` | 在港是否有足够合资格雇员（充分性属人工判断） | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | economic_substance | 否 |
| `hk_adequate_premises` | 在港是否有足够经营场所 | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | economic_substance | 否 |
| `hk_operating_expenditure_amount` | 在港发生的经营支出金额 | 用户侧事实/材料；没有则保持缺项 | economic_substance | 否 |
| `hk_operating_expenditure_currency` | 经营支出币种 | 用户侧事实/材料；没有则保持缺项 | 未列入当前 6 条规则的必需字段 | 否 |
| `strategic_decision_making_location` | 战略性决策作出地 | 用户侧事实/材料；没有则保持缺项 | economic_substance | 否 |
| `outsourcing_and_supervision` | 活动外包及在港监督情况 | 用户侧事实/材料；没有则保持缺项 | economic_substance | 否 |
| `hybrid_mismatch_arrangement` | 是否存在混合错配安排 | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | 未列入当前 6 条规则的必需字段 | 否 |
| `main_purpose_tax_benefit_flag` | 安排主要目的是否为获取税务利益（强制人工判断） | 用户可提供陈述和材料；法律资格/充分性留最终判断，不直接向用户索取结论 | participation_basic | 否 |
| `restructuring_near_income_date` | 收入累算前后是否存在临近重组 | 用户侧事实/材料；没有则保持缺项 | 未列入当前 6 条规则的必需字段 | 否 |
| `commercial_rationale` | 商业合理性说明 | 用户侧事实/材料；没有则保持缺项 | 未列入当前 6 条规则的必需字段 | 否 |
| `evidence_inventory` | 案件证据清单及其状态（provided/missing/conflict/not_applicable） | 用户材料目录 + 系统实收记录；自述已提供不等于附件已验证 | human_gate | 否 |
| `expert_decision_status` | 人工/专家复核状态，供强制人工门控使用 | 最终顾问/系统；聊天与事实编辑禁止写入 | human_gate | 否 |

## B 的补充输入与作用

| 字段 | 含义 | 何时收集 |
|---|---|---|
| `recipient_type` | 收款主体 | 候选场景识别必需 |
| `analysis_jurisdiction` | 本次分析的地区 | 候选场景识别必需 |
| `consultation_goal` | 本次咨询目标 | 候选场景识别必需 |
| `payer_jurisdiction` | 派息方所在地区 | 后续跨境背景核对，不阻断候选场景识别 |
| `income_event_status` | 收入已发生还是计划发生 | 按当前任务的必要事实收集 |
| `group_structure_description` | 集团成员与经营地区描述 | 按当前任务的必要事实收集 |
| `hk_staff_description` | 在港员工人数与职责描述 | 按当前任务的必要事实收集 |
| `hk_premises_description` | 在港场所及用途描述 | 按当前任务的必要事实收集 |
| `foreign_tax_description` | 境外缴税实际情况 | 按当前任务的必要事实收集 |
| `dividend_form` | 股息支付形式 | 收取分支区分现金/实物；不作为所有场景的入口门槛 |
| `transaction_flow_description` | 非现金资产及流转描述 | 收取分支区分现金/实物；不作为所有场景的入口门槛 |

## 本轮保留的边界

- 原规则 required_facts 与求值器读取项有差异；追问策略另有明确的任务依赖，不能依据代码未报错宣称事实完整。
- 4 张裁定研究卡中的非现金分配、现金池/再投资、企业税与预提税、未披露员工数量等，用于核查建模缺口，不能把裁定申请人的事实移植到用户案件。
- 非现金路径、税项描述目前采用结构化字段内的文字描述；尚无多实体交易图、双税种明细表或自动适用裁定的能力。
- 文件上传/材料解析不在 A 当前聊天入口的本轮实现内。本轮支持用户描述、候选事实与材料清单，不宣称已经读到客户凭证。
- C 的法规、规则、来源版本、适用期间、展示/入模许可与检索覆盖属于检索接口输出；不向用户追问“应该使用哪个法条版本/哈希”。
- 列表/未知值保持原类型；不自动生成真实公司名称、账户号、税率或交易日。
