// Error codes from the server, as English text; translations are in the language files.
export const errors: Record<string, string> = {
  "error:auth_unavailable": "The sign-in service is temporarily unavailable. Please retry.",
  "error:atlas_unavailable": "The tax graph is unavailable: the library or the rule layer cannot be read. Please retry.",
  "error:atlas_not_found": "This jurisdiction or provision was not found.",
  "error:network_error": "Connection interrupted or timed out. Retry safely without duplicating the operation.",
  "error:service_unavailable": "Service unavailable. Check the backend and retry.",
  "error:storage_unavailable": "Case storage is unavailable. Please retry later.",
  "error:revision_conflict": "The case changed elsewhere. The latest version is loaded; review it before proceeding.",
  "error:case_limit": "This case reached its capacity limit. Start a new chat.",
  "error:case_not_found": "Case not found. Reload the page.",
  "error:document_not_found": "This document is no longer in the case. The page has been refreshed.",
  "error:run_active": "The system is working on this case. Send your message when it finishes.",
  "error:rate_limited": "The model usage limit was reached. Please retry later.",
  "error:agent_failed": "This turn did not complete. Please retry.",
};
