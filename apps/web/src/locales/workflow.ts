export const workflow: Record<string, [string, string]> = {
  "正在思考…": ["正在思考…", "Thinking…"],
  "发送未完成，可重试": ["发送未完成，可重试", "Not completed. You can retry."],
  部分条文未检索到: [
    "部分条文未检索到",
    "Some legal references could not be retrieved",
  ],
  "error:knowledge_unavailable": [
    "暂时无法读取云端资料，请稍后重试。",
    "Cloud sources are temporarily unavailable. Please retry.",
  ],
  "来源内容已变化，待核对。": [
    "来源内容已变化，待核对。",
    "Source content has changed and needs review.",
  ],
  原文抓取时间: ["原文抓取时间", "Source retrieved at"],
  片段编号: ["片段编号", "Passage ID"],
  片段哈希: ["片段哈希", "Passage hash"],
  检索法条与案例: ["检索法条与案例", "Search laws and rulings"],
  "关键词、条文编号或案例编号": [
    "关键词、条文编号或案例编号",
    "Keyword, section or ruling number",
  ],
  检索: ["检索", "Search"],
  "以下为官方原文片段，适用性待核对。": [
    "以下为官方原文片段，适用性待核对。",
    "Official source excerpts. Check their applicability.",
  ],
  "未找到匹配资料，请换用具体条文、案例编号或税务关键词。": [
    "未找到匹配资料，请换用具体条文、案例编号或税务关键词。",
    "No matching sources. Try a section, ruling number or specific tax keyword.",
  ],
  进一步复核清单: ["进一步复核清单", "Further review checklist"],
  "以下事项尚未自动判断，请结合事实和证据逐项复核。": [
    "以下事项尚未自动判断，请结合事实和证据逐项复核。",
    "These items require review against facts and evidence; no automatic decision has been made.",
  ],
  待补充: ["待补充", "Missing"],
  "已记录，待核实": ["已记录，待核实", "Recorded; verify evidence"],
  相关官方案例: ["相关官方案例", "Related official rulings"],
  "按关键词匹配的参考案例，不能直接套用其裁定结论。请同时核对背景、适用期间及假设。":
    [
      "按关键词匹配的参考案例，不能直接套用其裁定结论。请同时核对背景、适用期间及假设。",
      "Keyword-matched references, not decisions for this case. Check background, applicable periods and assumptions.",
    ],
  "value:yes": ["是", "Yes"],
  "value:no": ["否", "No"],
  "value:unknown": ["未知", "Unknown"],
  "value:conflict": ["信息冲突", "Conflicting information"],
  "value:dividend": ["股息", "Dividend"],
  "value:interest": ["利息", "Interest"],
  "value:ip_income": ["知识产权收入", "IP income"],
  "value:disposal_gain": ["处置收益", "Disposal gain"],
  "value:other": ["其他", "Other"],
  "value:regulated_financial_entity": [
    "受规管金融实体",
    "Regulated financial entity",
  ],
  "value:non_financial_entity": ["非金融实体", "Non-financial entity"],
  "value:pure_equity_holding": ["纯股权持有实体", "Pure equity holding entity"],
  "value:general_entity": ["一般实体", "General entity"],
  "value:candidate_foreign_dividend": [
    "候选境外股息",
    "Candidate foreign dividend",
  ],
  "value:not_foreign_dividend": ["非境外股息", "Not a foreign dividend"],
  "value:foreign_sourced": ["境外来源", "Foreign sourced"],
  "value:hk_sourced": ["香港来源", "Hong Kong sourced"],
  "value:mixed": ["混合", "Mixed"],
  "value:received_in_hk": ["在香港收取", "Received in Hong Kong"],
  "value:received_outside_hk": ["在香港境外收取", "Received outside Hong Kong"],
  "value:deemed_received_in_hk": [
    "视为在香港收取",
    "Deemed received in Hong Kong",
  ],
  "value:not_applicable": ["不适用", "Not applicable"],
  "value:direct": ["直接持有", "Direct"],
  "value:indirect": ["间接持有", "Indirect"],
  "value:both": ["兼有", "Both"],
  "value:taxed": ["已征税", "Taxed"],
  "value:untaxed": ["未征税", "Untaxed"],
  "value:partially_taxed": ["部分征税", "Partially taxed"],
  "value:deductible": ["可扣除", "Deductible"],
  "value:non_deductible": ["不可扣除", "Non-deductible"],
  "value:adequate": ["充足（待复核）", "Adequate (subject to review)"],
  "value:inadequate": ["不足", "Inadequate"],
  "value:in_hk": ["在香港", "In Hong Kong"],
  "value:outside_hk": ["在香港境外", "Outside Hong Kong"],
  "value:outsourced_controlled": [
    "外包且有监督",
    "Outsourced with supervision",
  ],
  "value:outsourced_unsupervised": [
    "外包但无监督",
    "Outsourced without supervision",
  ],
  "value:none": ["无", "None"],
  "node:scope": ["适用范围", "Scope"],
  "node:income_characterisation": ["收入定性", "Income characterisation"],
  "node:receipt": ["在港收取", "Receipt in Hong Kong"],
  "node:financial_entity_exclusion": [
    "金融实体排除",
    "Financial entity exclusion",
  ],
  "node:economic_substance": ["经济实质", "Economic substance"],
  "node:participation_basic": [
    "参股基础条件",
    "Basic participation conditions",
  ],
  "node:foreign_tax_switchover": ["境外税转换", "Foreign tax switchover"],
  "node:anti_hybrid": ["反混合错配", "Anti-hybrid"],
  "node:main_purpose": ["主要目的", "Main purpose"],
  "node:compliance_filing": ["合规申报", "Compliance and filing"],
  "output:satisfied": ["条件确立（待复核）", "Established (subject to review)"],
  "output:not_satisfied": ["条件不确立", "Not established"],
  "output:unknown": ["信息不足", "Insufficient information"],
  "output:condition_not_demonstrated": [
    "条件未能证明",
    "Condition not demonstrated",
  ],
  "output:conflict": ["信息冲突", "Conflicting information"],
  "output:human_review_required": ["需要人工判断", "Human judgment required"],
  "error:model_not_configured": [
    "模型尚未配置，请在后端填写模型连接信息。",
    "Model configuration is incomplete. Configure the backend connection.",
  ],
  "error:model_failed": [
    "模型调用或返回校验失败。输入已保留，可以重试。",
    "The model request or response validation failed. Your input is preserved; you can retry.",
  ],
  "error:network_error": [
    "连接中断或超时。请重试，系统会避免重复提交。",
    "Connection interrupted or timed out. Retry safely without duplicating the operation.",
  ],
  "error:service_unavailable": [
    "服务暂不可用，请检查后端后重试。",
    "Service unavailable. Check the backend and retry.",
  ],
  "error:storage_unavailable": [
    "案件存储暂不可用，请稍后重试。",
    "Case storage is unavailable. Please retry later.",
  ],
  "error:revision_conflict": [
    "案件已在别处更新，已载入最新版本。请重新核对后操作。",
    "The case changed elsewhere. The latest version is loaded; review it before proceeding.",
  ],
  "error:invalid_facts": [
    "事实格式不正确，请检查数字、日期和选项。",
    "Invalid facts. Check numbers, dates and selected options.",
  ],
  "error:no_facts": ["请先补充案例事实。", "Add case facts first."],
  "error:resolve_conflicts": [
    "请先修订冲突事实。",
    "Resolve conflicting facts first.",
  ],
  "error:confirmation_required": [
    "请先确认当前事实版本。",
    "Confirm the current fact version first.",
  ],
  "error:data_confirmation_required": [
    "请先确认资料使用范围。",
    "Confirm the data usage scope first.",
  ],
  "error:case_limit": [
    "此案件已达到容量限制，请新建对话。",
    "This case reached its capacity limit. Start a new chat.",
  ],
  "error:workspace_required": [
    "工作空间凭据已失效，请刷新页面。",
    "Workspace credentials expired. Reload the page.",
  ],
  "error:case_not_found": [
    "未找到当前案件，请刷新页面。",
    "Case not found. Reload the page.",
  ],
};

export const liveEn: Record<string, string> = {
  "正在载入工作空间…": "Loading your workspace…",
  重试: "Retry",
  "本次仅提交合成研究资料，不含真实客户或个人信息。":
    "I am submitting synthetic research data only, with no real client or personal information.",
  "输入将发送至配置的模型服务。确认后请再次发送。":
    "Input will be sent to the configured model provider. Confirm, then send again.",
  "请核对候选事实。未知项可以保留，冲突项需先修订。":
    "Review the candidate facts. Unknowns may remain; conflicts must be resolved.",
  "模型提取，待核对": "Model extracted · Check required",
  手工记录: "Manually entered",
  暂不清楚: "Mark unknown",
  补充事实: "Add a fact",
  选择需要补充的事实: "Choose a fact to add",
  "确认将锁定当前事实版本；后续修改会使旧分析过期。":
    "Confirmation locks this fact version. Later changes invalidate the previous analysis.",
  确认事实并分析: "Confirm facts and analyze",
  "请先保存修改，再确认。": "Save your changes before confirming.",
  "此分析已过期，请重新确认事实。":
    "This analysis is outdated. Reconfirm the facts.",
  "研究结果 · 待专业复核": "Research results · Professional review required",
  "以下为现有规则的研究结果，不是免税或应税结论。":
    "Results from the implemented research rules. These do not determine exemption or tax liability.",
  待补充与复核: "Information and review needed",
  规则与分析版本: "Rules and analysis version",
  事实版本: "Fact version",
  规则版本: "Rule version",
  尚未实现的判断节点: "Judgment steps not yet implemented",
  本次分析的来源: "Sources for this analysis",
  "已取得条文片段，适用期间仍需核对。":
    "Provisions retrieved. Their applicability to the case period still needs review.",
  "未取得法规原文；以下是规则关联的官方资料链接。":
    "No legal passages retrieved. These official links are associated with the rules.",
  "这些事实存在冲突，请在案例信息中修订。":
    "These facts conflict. Resolve them in case details.",
  "为了继续梳理，请补充以下信息；不清楚的可以说明。":
    "Please provide the following details to continue. You can say when something is unknown.",
  "已整理本次信息。请核对事实后开始分析。":
    "The information has been organized. Review the facts before starting analysis.",
  核对案例事实: "Review case facts",
  开始分析: "Start analysis",
  "正在处理，请稍候…": "Working on your request…",
  "确认事实后运行研究规则。模型连接失败时可重试，不生成替代答案。":
    "Research rules run after you confirm the facts. Model failures can be retried; no substitute answers are generated.",
  "对话和事实保存在后端，可刷新恢复。当前仅用于内部研究，请勿输入真实客户或个人资料。":
    "Chats and facts are saved on the backend and restored on reload. For internal research only; do not enter real client or personal data.",
};
