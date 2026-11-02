export const errors: Record<string, [string, string]> = {
  "error:auth_unavailable": ["认证服务暂不可用，请稍后重试。","The sign-in service is temporarily unavailable. Please retry."],
  "error:network_error": ["连接中断或超时。请重试，系统会避免重复提交。","Connection interrupted or timed out. Retry safely without duplicating the operation."],
  "error:service_unavailable": ["服务暂不可用，请检查后端后重试。","Service unavailable. Check the backend and retry."],
  "error:storage_unavailable": ["案件存储暂不可用，请稍后重试。","Case storage is unavailable. Please retry later."],
  "error:revision_conflict": ["案件已在别处更新，已载入最新版本。请重新核对后操作。","The case changed elsewhere. The latest version is loaded; review it before proceeding."],
  "error:case_limit": ["此案件已达到容量限制，请新建对话。","This case reached its capacity limit. Start a new chat."],
  "error:case_not_found": ["未找到当前案件，请刷新页面。","Case not found. Reload the page."],
  "error:run_active": ["系统正在处理此案件，完成后再发送。","The system is working on this case. Send your message when it finishes."],
  "error:rate_limited": ["模型额度已用尽，请稍后重试。","The model usage limit was reached. Please retry later."],
  "error:agent_failed": ["这一轮未能完成，请重试。","This turn did not complete. Please retry."],
};
